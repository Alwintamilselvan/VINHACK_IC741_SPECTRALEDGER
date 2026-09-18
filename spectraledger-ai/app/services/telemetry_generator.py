"""
Synthetic telemetry generator.

This is the test-data source for the forecasting model AND the fallback
live-data feed used by the WebSocket broadcaster when no real telemetry
feed (Kafka, real 5G core, etc.) is wired up yet.

Design:
- Each slice has a `SliceProfile` (slice_type, capacity, baseline diurnal
  shape, noise level).
- A smooth daily cycle (two overlaid sine waves: a business-hours hump +
  a smaller evening hump) sets the "expected" load for time-of-day.
- Randomized named demand spikes are layered on top:
    * "ai_training_burst"    - large, moderately long throughput spike
    * "emergency_backup_job" - sharp, short throughput+latency spike
    * "maintenance_dip"      - rare short capacity/throughput dip
- Latency is modeled as a function of utilization (queueing gets worse as
  the slice approaches capacity) plus a slice-type base latency and noise.

Run as a script to materialize a CSV used for model training:
    python -m app.services.telemetry_generator
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from app.config import (
    DATA_DIR,
    DEFAULT_SIM_DAYS,
    TELEMETRY_CSV,
    TELEMETRY_SAMPLE_INTERVAL_MINUTES,
)

import os


@dataclass
class SliceProfile:
    slice_id: str
    slice_type: str  # one of eMBB, URLLC, mMTC, AI_TRAINING
    capacity_mbps: float
    base_utilization: float      # 0-1, average fraction of capacity used at "typical" load
    diurnal_amplitude: float     # 0-1, how much time-of-day swings utilization
    base_latency_ms: float       # latency floor at low utilization
    latency_congestion_gain: float  # how sharply latency rises as utilization -> 1
    noise_std_frac: float        # relative noise on throughput (fraction of capacity)
    spike_rate_per_day: float    # expected number of spike events per day


DEFAULT_PROFILES: List[SliceProfile] = [
    SliceProfile("slice-embb-01", "eMBB", 1000.0, 0.45, 0.35, 6.0, 40.0, 0.04, 1.2),
    SliceProfile("slice-embb-02", "eMBB", 800.0, 0.35, 0.30, 7.0, 35.0, 0.05, 1.0),
    SliceProfile("slice-urllc-01", "URLLC", 200.0, 0.25, 0.10, 1.5, 25.0, 0.03, 0.8),
    SliceProfile("slice-mmtc-01", "mMTC", 100.0, 0.20, 0.15, 15.0, 10.0, 0.06, 1.5),
    SliceProfile("slice-aitrain-01", "AI_TRAINING", 1000.0, 0.30, 0.15, 5.0, 45.0, 0.06, 2.5),
    SliceProfile("slice-aitrain-02", "AI_TRAINING", 1200.0, 0.25, 0.10, 5.0, 45.0, 0.07, 2.2),
]

SPIKE_TYPES = {
    "ai_training_burst": dict(
        magnitude_range=(1.6, 3.0), duration_range_min=(20, 90),
        latency_gain=1.4, weight_by_type={"AI_TRAINING": 3.0, "eMBB": 1.0, "URLLC": 0.3, "mMTC": 0.4},
    ),
    "emergency_backup_job": dict(
        magnitude_range=(1.3, 2.2), duration_range_min=(10, 40),
        latency_gain=1.8, weight_by_type={"AI_TRAINING": 0.8, "eMBB": 1.2, "URLLC": 1.5, "mMTC": 0.6},
    ),
    "maintenance_dip": dict(
        magnitude_range=(0.3, 0.6), duration_range_min=(10, 30),
        latency_gain=1.1, weight_by_type={"AI_TRAINING": 0.5, "eMBB": 0.5, "URLLC": 0.4, "mMTC": 0.5},
    ),
}


def _diurnal_factor(t: datetime, amplitude: float) -> float:
    """Smooth 0..1-ish multiplier on baseline utilization based on time-of-day.
    Business-hours hump (peak ~14:00 UTC) + smaller evening hump (~21:00 UTC)."""
    hour = t.hour + t.minute / 60.0
    business_hump = math.exp(-((hour - 14.0) ** 2) / (2 * 4.0 ** 2))
    evening_hump = 0.5 * math.exp(-((hour - 21.0) ** 2) / (2 * 2.5 ** 2))
    shape = business_hump + evening_hump  # roughly 0..1.5
    return 1.0 + amplitude * (shape - 0.5)


def compute_sample(
    profile: SliceProfile,
    t: datetime,
    spike_multiplier: float,
    spike_latency_gain: float,
    rng: np.random.Generator,
) -> tuple:
    """Turn (time-of-day, active spike state) into one (throughput, latency,
    utilization) sample for a slice. Shared by the batch generator (used for
    training data) and the live simulator (used for the WebSocket demo feed)
    so both produce data from the same underlying model."""
    diurnal = _diurnal_factor(t, profile.diurnal_amplitude)
    utilization = profile.base_utilization * diurnal * spike_multiplier
    utilization = float(np.clip(utilization, 0.02, 1.15))  # allow brief overshoot above 1.0

    noise = rng.normal(0, profile.noise_std_frac * profile.capacity_mbps)
    throughput = max(0.0, utilization * profile.capacity_mbps + noise)

    congestion = min(utilization, 1.0)
    latency = (
        profile.base_latency_ms
        + profile.latency_congestion_gain * (congestion ** 3) * spike_latency_gain
        + rng.normal(0, profile.base_latency_ms * 0.08)
    )
    latency = max(0.5, latency)
    return throughput, latency, utilization


@dataclass
class LiveSpikeState:
    """Tracks an in-progress spike for one slice in the live simulator."""
    remaining_ticks: int = 0
    magnitude: float = 1.0
    latency_gain: float = 1.0
    label: str = ""


def next_live_sample(
    profile: SliceProfile,
    t: datetime,
    state: LiveSpikeState,
    rng: np.random.Generator,
    tick_minutes: float,
) -> Tuple[float, float, str]:
    """Advance the live simulator by one tick for a single slice. Mutates
    `state` in place (spike countdown) and returns (throughput, latency,
    active_spike_label). Used by the WebSocket demo feed as the fallback
    live-data source when no real telemetry pipeline is connected."""
    if state.remaining_ticks <= 0:
        # Chance of starting a new spike this tick, calibrated from the
        # profile's expected spikes/day.
        ticks_per_day = (24 * 60) / max(tick_minutes, 1e-6)
        p_new_spike = profile.spike_rate_per_day / max(ticks_per_day, 1.0)
        if rng.random() < p_new_spike:
            spike_names = list(SPIKE_TYPES.keys())
            weights = np.array([
                SPIKE_TYPES[name]["weight_by_type"].get(profile.slice_type, 0.5) for name in spike_names
            ], dtype=float)
            weights = weights / weights.sum()
            name = rng.choice(spike_names, p=weights)
            spec = SPIKE_TYPES[name]
            duration = rng.uniform(*spec["duration_range_min"])
            state.remaining_ticks = max(1, int(duration / tick_minutes))
            state.magnitude = float(rng.uniform(*spec["magnitude_range"]))
            state.latency_gain = spec["latency_gain"]
            state.label = name
        else:
            state.magnitude, state.latency_gain, state.label = 1.0, 1.0, ""

    throughput, latency, _ = compute_sample(profile, t, state.magnitude, state.latency_gain, rng)

    if state.remaining_ticks > 0:
        state.remaining_ticks -= 1
        if state.remaining_ticks == 0:
            state.magnitude, state.latency_gain, state.label = 1.0, 1.0, ""

    return throughput, latency, state.label


def _sample_spike_events(profile: SliceProfile, start: datetime, days: int, rng: np.random.Generator):
    """Pre-generate a list of (start, end, magnitude, latency_gain, label) spike windows."""
    events = []
    n_expected = profile.spike_rate_per_day * days
    n_events = rng.poisson(max(n_expected, 0.01))
    for _ in range(n_events):
        spike_names = list(SPIKE_TYPES.keys())
        weights = np.array([
            SPIKE_TYPES[name]["weight_by_type"].get(profile.slice_type, 0.5) for name in spike_names
        ], dtype=float)
        weights = weights / weights.sum()
        name = rng.choice(spike_names, p=weights)
        spec = SPIKE_TYPES[name]

        offset_minutes = rng.uniform(0, days * 24 * 60)
        spike_start = start + timedelta(minutes=float(offset_minutes))
        duration = rng.uniform(*spec["duration_range_min"])
        spike_end = spike_start + timedelta(minutes=float(duration))
        magnitude = rng.uniform(*spec["magnitude_range"])
        events.append((spike_start, spike_end, magnitude, spec["latency_gain"], name))
    return events


def generate_slice_timeseries(
    profile: SliceProfile,
    start: datetime,
    days: int = DEFAULT_SIM_DAYS,
    interval_minutes: int = TELEMETRY_SAMPLE_INTERVAL_MINUTES,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """Generate one slice's full throughput/latency time series."""
    rng = np.random.default_rng(seed)
    n_points = int(days * 24 * 60 / interval_minutes)
    timestamps = [start + timedelta(minutes=i * interval_minutes) for i in range(n_points)]

    spikes = _sample_spike_events(profile, start, days, rng)

    rows = []
    for t in timestamps:
        active_spike_label = None
        spike_multiplier = 1.0
        spike_latency_gain = 1.0
        for (s_start, s_end, magnitude, latency_gain, name) in spikes:
            if s_start <= t <= s_end:
                spike_multiplier = max(spike_multiplier, magnitude)
                spike_latency_gain = max(spike_latency_gain, latency_gain)
                active_spike_label = name

        throughput, latency, utilization = compute_sample(
            profile, t, spike_multiplier, spike_latency_gain, rng
        )

        rows.append(
            {
                "slice_id": profile.slice_id,
                "slice_type": profile.slice_type,
                "timestamp": t,
                "throughput_mbps": round(throughput, 2),
                "latency_ms": round(latency, 2),
                "capacity_mbps": profile.capacity_mbps,
                "utilization": round(utilization, 4),
                "spike_label": active_spike_label or "",
            }
        )

    return pd.DataFrame(rows)


def generate_dataset(
    profiles: Optional[List[SliceProfile]] = None,
    start: Optional[datetime] = None,
    days: int = DEFAULT_SIM_DAYS,
    interval_minutes: int = TELEMETRY_SAMPLE_INTERVAL_MINUTES,
    seed: Optional[int] = 42,
) -> pd.DataFrame:
    """Generate the full multi-slice dataset used for training + demo fallback."""
    profiles = profiles or DEFAULT_PROFILES
    start = start or (datetime.now(timezone.utc) - timedelta(days=days))
    rng = np.random.default_rng(seed)

    frames = []
    for i, profile in enumerate(profiles):
        # derive a distinct-but-reproducible seed per slice
        slice_seed = None if seed is None else int(rng.integers(0, 1_000_000)) + i
        frames.append(
            generate_slice_timeseries(profile, start, days=days, interval_minutes=interval_minutes, seed=slice_seed)
        )
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(["slice_id", "timestamp"]).reset_index(drop=True)
    return df


def latest_window_for_slice(
    df: pd.DataFrame, slice_id: str, n_points: int = 12
) -> pd.DataFrame:
    """Convenience helper: pull the most recent N samples for one slice (e.g. for demo requests)."""
    sub = df[df["slice_id"] == slice_id].sort_values("timestamp")
    return sub.tail(n_points)


def save_dataset(df: pd.DataFrame, path: str = TELEMETRY_CSV) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    dataset = generate_dataset()
    out_path = save_dataset(dataset)
    print(f"Generated {len(dataset):,} rows across {dataset['slice_id'].nunique()} slices -> {out_path}")
    print(dataset.groupby(["slice_id", "slice_type"]).agg(
        avg_throughput=("throughput_mbps", "mean"),
        max_throughput=("throughput_mbps", "max"),
        avg_latency=("latency_ms", "mean"),
        spikes=("spike_label", lambda s: (s != "").sum()),
    ))
