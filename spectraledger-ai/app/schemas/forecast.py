"""
/forecast contract.

POST /forecast
    in:  ForecastRequest  (slice_id + recent telemetry window)
    out: ForecastResponse (predicted bandwidth demand for next 15-60 min + CI)
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ConfidenceInterval, SliceType, TelemetryPoint


class ForecastRequest(BaseModel):
    slice_id: str = Field(..., description="Unique identifier of the network slice")
    slice_type: SliceType = Field(
        default=SliceType.EMBB, description="Workload category, used as a model feature"
    )
    telemetry: List[TelemetryPoint] = Field(
        ..., min_length=6,
        description="Recent telemetry window, ordered oldest->newest. "
                    "At least 6 samples recommended (e.g. last 30-60 min at 5 min resolution).",
    )
    horizon_minutes: int = Field(
        default=30, ge=15, le=60,
        description="How far ahead to forecast demand, in minutes (15-60).",
    )

    @field_validator("telemetry")
    @classmethod
    def _sorted_and_nonempty(cls, v: List[TelemetryPoint]) -> List[TelemetryPoint]:
        if len(v) < 2:
            raise ValueError("telemetry must contain at least 2 points")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "slice_id": "slice-aitrain-07",
                "slice_type": "AI_TRAINING",
                "horizon_minutes": 30,
                "telemetry": [
                    {"timestamp": "2026-09-18T09:30:00Z", "throughput_mbps": 340.2, "latency_ms": 9.1},
                    {"timestamp": "2026-09-18T09:35:00Z", "throughput_mbps": 355.8, "latency_ms": 9.4},
                    {"timestamp": "2026-09-18T09:40:00Z", "throughput_mbps": 402.1, "latency_ms": 10.2},
                    {"timestamp": "2026-09-18T09:45:00Z", "throughput_mbps": 460.7, "latency_ms": 11.0},
                    {"timestamp": "2026-09-18T09:50:00Z", "throughput_mbps": 511.3, "latency_ms": 12.4},
                    {"timestamp": "2026-09-18T09:55:00Z", "throughput_mbps": 548.9, "latency_ms": 13.1},
                ],
            }
        }
    }


class ForecastResponse(BaseModel):
    slice_id: str
    slice_type: SliceType
    generated_at: datetime
    horizon_minutes: int
    predicted_demand_mbps: float = Field(..., description="Point forecast of demand")
    confidence_interval: ConfidenceInterval
    confidence_score: float = Field(
        ..., ge=0, le=1,
        description="0-1 score derived from interval width relative to the point forecast; "
                    "1.0 = very tight/confident interval, 0.0 = very wide/uncertain.",
    )
    trend: str = Field(..., description="Human-readable trend label: rising | falling | stable")
    model_version: str = Field(..., description="Identifier of the model that produced this forecast")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "slice_id": "slice-aitrain-07",
                "slice_type": "AI_TRAINING",
                "generated_at": "2026-09-18T10:00:00Z",
                "horizon_minutes": 30,
                "predicted_demand_mbps": 612.4,
                "confidence_interval": {"lower": 560.1, "upper": 664.7},
                "confidence_score": 0.78,
                "trend": "rising",
                "model_version": "lightgbm-v1",
            }
        }
    }
