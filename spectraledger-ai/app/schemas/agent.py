"""
/agent/evaluate contract.

POST /agent/evaluate
    in:  AgentEvaluateRequest (order book snapshot + slice state, role = seller|buyer)
    out: AgentEvaluateResponse (decision + natural-language reasoning)

The agent internally calls the forecasting and pricing services (not just
stubs) using the telemetry/slice_state supplied here, so the response also
echoes the forecast and price it derived its decision from -- useful for
demoing the full pipeline in one call.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import (
    AgentDecisionType,
    AgentRole,
    Order,
    QosPriority,
    SliceType,
    TelemetryPoint,
)
from app.schemas.forecast import ForecastResponse
from app.schemas.pricing import PriceResponse


class SliceState(BaseModel):
    slice_id: str
    slice_type: SliceType = SliceType.EMBB
    capacity_mbps: float = Field(..., gt=0)
    current_utilization: float = Field(
        ..., ge=0, le=1.2,
        description="Fraction of capacity_mbps currently in use. Allowed slightly above 1.0 "
                    "on purpose -- a slice can be genuinely oversubscribed (e.g. the demo's "
                    "slice-factory-09), and that's exactly the signal that should drive a BUY "
                    "decision, not something to clamp away before it reaches the agent.",
    )
    qos_priority: QosPriority = QosPriority.SILVER
    sla_min_confidence: float = Field(
        default=0.5, ge=0, le=1,
        description="Minimum forecast confidence_score required to list bandwidth for sale "
                    "(SLA risk gate threshold). Below this, the Seller Agent refuses to list.",
    )


class AgentEvaluateRequest(BaseModel):
    role: AgentRole = Field(..., description="Which agent persona should evaluate: seller or buyer")
    slice_state: SliceState
    telemetry: List[TelemetryPoint] = Field(
        ..., min_length=6, description="Recent telemetry window used to derive the forecast"
    )
    order_book: List[Order] = Field(
        default_factory=list, description="Resting bid/ask orders visible to the agent"
    )
    horizon_minutes: int = Field(default=30, ge=15, le=60)

    model_config = {
        "json_schema_extra": {
            "example": {
                "role": "seller",
                "slice_state": {
                    "slice_id": "slice-embb-12",
                    "slice_type": "eMBB",
                    "capacity_mbps": 1000.0,
                    "current_utilization": 0.3,
                    "qos_priority": "silver",
                    "sla_min_confidence": 0.5,
                },
                "telemetry": [
                    {"timestamp": "2026-09-18T09:30:00Z", "throughput_mbps": 280.0, "latency_ms": 7.5},
                    {"timestamp": "2026-09-18T09:35:00Z", "throughput_mbps": 275.0, "latency_ms": 7.4},
                    {"timestamp": "2026-09-18T09:40:00Z", "throughput_mbps": 290.0, "latency_ms": 7.6},
                    {"timestamp": "2026-09-18T09:45:00Z", "throughput_mbps": 265.0, "latency_ms": 7.3},
                    {"timestamp": "2026-09-18T09:50:00Z", "throughput_mbps": 270.0, "latency_ms": 7.5},
                    {"timestamp": "2026-09-18T09:55:00Z", "throughput_mbps": 260.0, "latency_ms": 7.2},
                ],
                "order_book": [
                    {
                        "order_id": "ord-1",
                        "slice_id": "slice-aitrain-07",
                        "side": "bid",
                        "price": 0.09,
                        "quantity_mbps": 200.0,
                        "qos_priority": "gold",
                    }
                ],
                "horizon_minutes": 30,
            }
        }
    }


class AgentEvaluateResponse(BaseModel):
    slice_id: str
    role: AgentRole
    decision: AgentDecisionType
    quantity_mbps: Optional[float] = Field(
        default=None, description="Bandwidth to list/buy/sell in Mbps, if applicable"
    )
    price: Optional[float] = Field(default=None, description="Price attached to the decision, if applicable")
    matched_order_id: Optional[str] = Field(
        default=None, description="Order book entry this decision matched against, if a trade cleared"
    )
    reasoning: str = Field(..., description="Short natural-language explanation of the decision")
    sla_gate_passed: bool = Field(..., description="Whether the SLA risk evaluator allowed listing")
    forecast: ForecastResponse
    pricing: PriceResponse
    decided_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "slice_id": "slice-embb-12",
                "role": "seller",
                "decision": "list",
                "quantity_mbps": 300.0,
                "price": 0.061,
                "matched_order_id": None,
                "reasoning": "Forecast confidence (0.86) clears the SLA safety threshold (0.5). "
                             "Predicted demand (301 Mbps) leaves a projected surplus of ~699 Mbps "
                             "against 1000 Mbps capacity, so listing 300 Mbps keeps a safety buffer. "
                             "No matching bid at this ask price yet -> listing, not selling.",
                "sla_gate_passed": True,
                "forecast": "...",
                "pricing": "...",
                "decided_at": "2026-09-18T10:00:02Z",
            }
        }
    }