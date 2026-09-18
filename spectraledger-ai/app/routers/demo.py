"""
Convenience endpoints for the demo/hackathon judges and downstream teams
who don't want to hand-build telemetry payloads to try /forecast,
/price, and /agent/evaluate. Not part of the core contract -- purely
sugar on top of the synthetic dataset.
"""
import os

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.config import TELEMETRY_CSV
from app.services.telemetry_generator import DEFAULT_PROFILES, generate_dataset, save_dataset

router = APIRouter(prefix="/demo", tags=["demo"])


def _load_dataset() -> pd.DataFrame:
    if not os.path.exists(TELEMETRY_CSV):
        df = generate_dataset()
        save_dataset(df)
        return df
    return pd.read_csv(TELEMETRY_CSV, parse_dates=["timestamp"])


@router.get("/slices")
async def list_slices():
    """List the demo slice profiles available in the synthetic dataset."""
    return [
        {
            "slice_id": p.slice_id,
            "slice_type": p.slice_type,
            "capacity_mbps": p.capacity_mbps,
            "base_utilization": p.base_utilization,
        }
        for p in DEFAULT_PROFILES
    ]


@router.get("/telemetry/{slice_id}")
async def latest_telemetry(slice_id: str, n: int = Query(default=8, ge=2, le=50)):
    """Return the most recent `n` synthetic telemetry samples for a slice,
    shaped exactly like the `telemetry` field /forecast and /agent/evaluate
    expect -- copy-paste this straight into either request body."""
    df = _load_dataset()
    sub = df[df["slice_id"] == slice_id].sort_values("timestamp")
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"Unknown slice_id '{slice_id}'. See GET /demo/slices.")
    tail = sub.tail(n)
    return {
        "slice_id": slice_id,
        "slice_type": tail["slice_type"].iloc[0],
        "capacity_mbps": float(tail["capacity_mbps"].iloc[0]),
        "current_utilization": float(tail["utilization"].iloc[-1]),
        "telemetry": [
            {
                "timestamp": row.timestamp.isoformat(),
                "throughput_mbps": row.throughput_mbps,
                "latency_ms": row.latency_ms,
            }
            for row in tail.itertuples()
        ],
    }
