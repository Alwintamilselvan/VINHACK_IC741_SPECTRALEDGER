"""
Bandwidth forecasting model.

Approach: LightGBM gradient-boosted trees (no deep learning -- fast to
train, easy to explain). One point-forecast model (regression objective)
plus two quantile models (alpha=0.1 / alpha=0.9) give a prediction
interval, which is how ForecastResponse.confidence_interval and
confidence_score are derived.

Features (computed identically at train time and inference time, so the
model never sees a distribution shift between the two):
    hour_sin, hour_cos          - time-of-day, cyclic encoded
    dow_sin, dow_cos            - day-of-week, cyclic encoded
    last_throughput, last_latency
    rolling_mean, rolling_std   - over the whole supplied telemetry window
    rolling_mean_recent         - mean of the last <=3 points (short-term)
    trend_slope                 - Mbps/step linear trend across the window
    slice_type_code             - categorical code for the slice workload type
    horizon_minutes             - how far ahead we're predicting (15-60)

If no trained model exists on disk, `ensure_model()` trains one on the fly
from the synthetic telemetry CSV (generating it first if needed), so the
service is runnable with zero manual setup steps.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from app.config import FORECAST_MODEL_PATH, MODEL_VERSION, TELEMETRY_CSV
from app.schemas.common import ConfidenceInterval, SliceType, TelemetryPoint
from app.schemas.forecast import ForecastResponse

SLICE_TYPE_CODES = {t.value: i for i, t in enumerate(SliceType)}
HISTORY_POINTS = 12          # up to 60 min of 5-min samples used for rolling features
TRAIN_HORIZONS_MIN = [15, 30, 45, 60]
TRAIN_INTERVAL_MIN = 5

FEATURE_COLUMNS = [
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "last_throughput", "last_latency",
    "rolling_mean", "rolling_std", "rolling_mean_recent",
    "trend_slope", "slice_type_code", "horizon_minutes",
]


def _cyclic(value: float, period: float) -> Tuple[float, float]:
    angle = 2 * np.pi * (value / period)
    return float(np.sin(angle)), float(np.cos(angle))


def _slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values))
    # simple least-squares slope, robust to short windows
    x_mean, y_mean = x.mean(), values.mean()
    denom = ((x - x_mean) ** 2).sum()
    if denom == 0:
        return 0.0
    return float(((x - x_mean) * (values - y_mean)).sum() / denom)


def build_features(
    timestamps: List[datetime],
    throughputs: List[float],
    latencies: List[float],
    slice_type: str,
    horizon_minutes: int,
) -> dict:
    """Build one feature row from a telemetry window. Used identically for
    training (windows sliced from historical data) and inference (the
    window supplied in the request body)."""
    now = timestamps[-1]
    hour_sin, hour_cos = _cyclic(now.hour + now.minute / 60.0, 24.0)
    dow_sin, dow_cos = _cyclic(now.weekday(), 7.0)

    tp = np.asarray(throughputs, dtype=float)
    recent = tp[-3:] if len(tp) >= 3 else tp

    return {
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "dow_sin": dow_sin,
        "dow_cos": dow_cos,
        "last_throughput": float(tp[-1]),
        "last_latency": float(latencies[-1]),
        "rolling_mean": float(tp.mean()),
        "rolling_std": float(tp.std()) if len(tp) > 1 else 0.0,
        "rolling_mean_recent": float(recent.mean()),
        "trend_slope": _slope(tp),
        "slice_type_code": SLICE_TYPE_CODES.get(slice_type, SLICE_TYPE_CODES[SliceType.EMBB.value]),
        "horizon_minutes": float(horizon_minutes),
    }


def _build_training_frame(
    df: pd.DataFrame,
    history_points: int = HISTORY_POINTS,
    horizons_minutes: List[int] = TRAIN_HORIZONS_MIN,
    interval_minutes: int = TRAIN_INTERVAL_MIN,
) -> pd.DataFrame:
    rows = []
    for slice_id, sub in df.groupby("slice_id"):
        sub = sub.sort_values("timestamp").reset_index(drop=True)
        ts = pd.to_datetime(sub["timestamp"]).tolist()  # list of pandas.Timestamp (datetime-compatible)
        throughput = sub["throughput_mbps"].to_numpy()
        latency = sub["latency_ms"].to_numpy()
        slice_type = sub["slice_type"].iloc[0]
        max_horizon_steps = max(h // interval_minutes for h in horizons_minutes)
        n = len(sub)

        for i in range(history_points - 1, n - max_horizon_steps):
            window_slice = slice(i - history_points + 1, i + 1)
            window_ts = list(ts[window_slice])
            window_tp = list(throughput[window_slice])
            window_lat = list(latency[window_slice])

            for horizon in horizons_minutes:
                steps = horizon // interval_minutes
                target_idx = i + steps
                if target_idx >= n:
                    continue
                feat = build_features(window_ts, window_tp, window_lat, slice_type, horizon)
                feat["target"] = float(throughput[target_idx])
                rows.append(feat)

    return pd.DataFrame(rows)


@dataclass
class ForecastModelBundle:
    point_model: LGBMRegressor
    lower_model: LGBMRegressor
    upper_model: LGBMRegressor
    feature_columns: List[str]
    model_version: str
    trained_at: str
    train_mae: float


def train_model(df: Optional[pd.DataFrame] = None, save_path: str = FORECAST_MODEL_PATH) -> ForecastModelBundle:
    if df is None:
        if not os.path.exists(TELEMETRY_CSV):
            from app.services.telemetry_generator import generate_dataset, save_dataset
            df = generate_dataset()
            save_dataset(df)
        else:
            df = pd.read_csv(TELEMETRY_CSV, parse_dates=["timestamp"])

    train_df = _build_training_frame(df)
    X = train_df[FEATURE_COLUMNS]
    y = train_df["target"]

    common_kwargs = dict(
        n_estimators=200,
        num_leaves=31,
        learning_rate=0.05,
        min_child_samples=20,
        verbose=-1,
    )

    point_model = LGBMRegressor(objective="regression", **common_kwargs)
    point_model.fit(X, y)

    lower_model = LGBMRegressor(objective="quantile", alpha=0.1, **common_kwargs)
    lower_model.fit(X, y)

    upper_model = LGBMRegressor(objective="quantile", alpha=0.9, **common_kwargs)
    upper_model.fit(X, y)

    preds = point_model.predict(X)
    mae = float(np.mean(np.abs(preds - y.to_numpy())))

    bundle = ForecastModelBundle(
        point_model=point_model,
        lower_model=lower_model,
        upper_model=upper_model,
        feature_columns=FEATURE_COLUMNS,
        model_version=MODEL_VERSION,
        trained_at=datetime.now(timezone.utc).isoformat(),
        train_mae=mae,
    )

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump(bundle, save_path)
    return bundle


_BUNDLE: Optional[ForecastModelBundle] = None


def ensure_model() -> ForecastModelBundle:
    """Load the trained model from disk, training one first if it doesn't exist yet."""
    global _BUNDLE
    if _BUNDLE is not None:
        return _BUNDLE
    if os.path.exists(FORECAST_MODEL_PATH):
        _BUNDLE = joblib.load(FORECAST_MODEL_PATH)
    else:
        _BUNDLE = train_model()
    return _BUNDLE


def predict(
    telemetry: List[TelemetryPoint],
    slice_id: str,
    slice_type: str,
    horizon_minutes: int,
) -> ForecastResponse:
    bundle = ensure_model()

    timestamps = [p.timestamp for p in telemetry]
    throughputs = [p.throughput_mbps for p in telemetry]
    latencies = [p.latency_ms for p in telemetry]

    feat = build_features(timestamps, throughputs, latencies, slice_type, horizon_minutes)
    X = pd.DataFrame([feat])[bundle.feature_columns]

    point = float(bundle.point_model.predict(X)[0])
    lower = float(bundle.lower_model.predict(X)[0])
    upper = float(bundle.upper_model.predict(X)[0])

    # Guard against quantile crossing / negative values.
    lower, upper = min(lower, upper), max(lower, upper)
    point = float(np.clip(point, 0, None))
    lower = float(np.clip(min(lower, point), 0, None))
    upper = float(max(upper, point))

    width = max(upper - lower, 0.0)
    relative_width = width / max(point, 1.0)
    confidence_score = float(np.clip(np.exp(-relative_width), 0.0, 1.0))

    last_throughput = throughputs[-1]
    if point > last_throughput * 1.05:
        trend = "rising"
    elif point < last_throughput * 0.95:
        trend = "falling"
    else:
        trend = "stable"

    return ForecastResponse(
        slice_id=slice_id,
        slice_type=slice_type,
        generated_at=datetime.now(timezone.utc),
        horizon_minutes=horizon_minutes,
        predicted_demand_mbps=round(point, 2),
        confidence_interval=ConfidenceInterval(lower=round(lower, 2), upper=round(upper, 2)),
        confidence_score=round(confidence_score, 4),
        trend=trend,
        model_version=bundle.model_version,
    )
