"""
Shared enums and primitive types used across the SpectraLedger AI Engine
API contract. Keep this module stable once the contract is shared with the
backend/frontend teams — downstream services depend on these shapes.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SliceType(str, Enum):
    """Coarse category of the 5G network slice workload."""
    EMBB = "eMBB"              # enhanced mobile broadband (general traffic)
    URLLC = "URLLC"            # ultra-reliable low-latency (safety-critical)
    MMTC = "mMTC"              # massive machine-type comms (IoT/sensors)
    AI_TRAINING = "AI_TRAINING"  # bursty, throughput-hungry batch workloads


class QosPriority(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"


class AgentRole(str, Enum):
    SELLER = "seller"
    BUYER = "buyer"


class AgentDecisionType(str, Enum):
    LIST = "list"
    HOLD = "hold"
    BUY = "buy"
    SELL = "sell"
    NO_ACTION = "no_action"


class OrderSide(str, Enum):
    BID = "bid"   # buyer wants to buy bandwidth
    ASK = "ask"   # seller wants to sell bandwidth


class TelemetryPoint(BaseModel):
    """A single sample of a slice's throughput/latency time series."""
    timestamp: datetime = Field(..., description="UTC timestamp of the sample")
    throughput_mbps: float = Field(..., ge=0, description="Observed throughput in Mbps")
    latency_ms: float = Field(..., ge=0, description="Observed round-trip latency in ms")

    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": "2026-09-18T10:00:00Z",
                "throughput_mbps": 412.5,
                "latency_ms": 8.2,
            }
        }
    }


class ConfidenceInterval(BaseModel):
    lower: float = Field(..., description="Lower bound of the prediction interval (Mbps)")
    upper: float = Field(..., description="Upper bound of the prediction interval (Mbps)")

    @property
    def width(self) -> float:
        return max(self.upper - self.lower, 0.0)


class Order(BaseModel):
    """A resting order in the (mock) order book."""
    order_id: str
    slice_id: str
    side: OrderSide
    price: float = Field(..., ge=0, description="Price per Mbps-hour")
    quantity_mbps: float = Field(..., gt=0)
    qos_priority: QosPriority = QosPriority.SILVER
    expires_at: Optional[datetime] = None
