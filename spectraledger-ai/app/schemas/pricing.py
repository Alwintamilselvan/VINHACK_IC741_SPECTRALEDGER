"""
/price contract.

POST /price
    in:  PriceRequest  (slice_id, current utilization, forecast output)
    out: PriceResponse (bid/ask price + confidence score + explainable breakdown)
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import QosPriority
from app.schemas.forecast import ForecastResponse


class PriceRequest(BaseModel):
    slice_id: str
    capacity_mbps: float = Field(..., gt=0, description="Total provisioned capacity of the slice")
    current_utilization: float = Field(
        ..., ge=0, le=1, description="Fraction of capacity_mbps currently in use (0-1)"
    )
    qos_priority: QosPriority = Field(default=QosPriority.SILVER)
    forecast: ForecastResponse = Field(..., description="Output of a prior call to /forecast")
    base_rate: Optional[float] = Field(
        default=None, gt=0,
        description="Override the default base rate ($ per Mbps-hour). Omit to use service default.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "slice_id": "slice-aitrain-07",
                "capacity_mbps": 1000.0,
                "current_utilization": 0.55,
                "qos_priority": "gold",
                "forecast": {
                    "slice_id": "slice-aitrain-07",
                    "slice_type": "AI_TRAINING",
                    "generated_at": "2026-09-18T10:00:00Z",
                    "horizon_minutes": 30,
                    "predicted_demand_mbps": 612.4,
                    "confidence_interval": {"lower": 560.1, "upper": 664.7},
                    "confidence_score": 0.78,
                    "trend": "rising",
                    "model_version": "lightgbm-v1",
                },
            }
        }
    }


class PriceComponents(BaseModel):
    """Explainable breakdown of the pricing formula. No black box: every factor is visible."""
    base_rate: float
    congestion_multiplier: float
    qos_priority_weight: float
    urgency_factor: float

    def as_formula_string(self) -> str:
        return (
            f"price = {self.base_rate:.4f} (base_rate) "
            f"* {self.congestion_multiplier:.4f} (congestion_multiplier) "
            f"* {self.qos_priority_weight:.4f} (qos_priority_weight) "
            f"* {self.urgency_factor:.4f} (urgency_factor)"
        )


class PriceResponse(BaseModel):
    slice_id: str
    generated_at: datetime
    unit: str = Field(default="USD per Mbps-hour")
    bid_price: float = Field(..., description="Price a buyer would pay (slightly below mid)")
    ask_price: float = Field(..., description="Price a seller would ask (slightly above mid)")
    mid_price: float = Field(..., description="Undiscounted formula output")
    confidence_score: float = Field(..., ge=0, le=1, description="Carried over from the forecast")
    components: PriceComponents
    explanation: str = Field(..., description="Human-readable explanation of the price derivation")

    model_config = {
        "json_schema_extra": {
            "example": {
                "slice_id": "slice-aitrain-07",
                "generated_at": "2026-09-18T10:00:01Z",
                "unit": "USD per Mbps-hour",
                "bid_price": 0.0871,
                "ask_price": 0.0963,
                "mid_price": 0.0917,
                "confidence_score": 0.78,
                "components": {
                    "base_rate": 0.05,
                    "congestion_multiplier": 1.375,
                    "qos_priority_weight": 1.2,
                    "urgency_factor": 1.111,
                },
                "explanation": "Demand forecast (612 Mbps) exceeds current utilization "
                               "(55% of 1000 Mbps), pushing congestion_multiplier to 1.38x. "
                               "Gold QoS adds 1.2x. Surplus window closes soon, adding a 1.11x "
                               "urgency premium.",
            }
        }
    }
