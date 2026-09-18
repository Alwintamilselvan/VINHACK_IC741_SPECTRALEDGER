"""
Event shapes for the three pub/sub topics. In production these would be
Kafka topics; for the hackathon demo they are broadcast verbatim (same
JSON shape) over a WebSocket at /ws/stream, keyed by "topic". A Kafka
producer can be swapped in later without changing these schemas — see
app/services/broadcast.py.

Topics:
    telemetry.raw     - raw per-slice telemetry samples as they're generated/ingested
    trade.executed    - a matched trade between a buyer and seller agent
    agent.decision    - every decision an agent makes (list/hold/buy/sell), not just matches
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.common import AgentDecisionType, AgentRole, QosPriority


class TelemetryRawEvent(BaseModel):
    topic: Literal["telemetry.raw"] = "telemetry.raw"
    slice_id: str
    timestamp: datetime
    throughput_mbps: float
    latency_ms: float


class TradeExecutedEvent(BaseModel):
    topic: Literal["trade.executed"] = "trade.executed"
    trade_id: str
    buyer_slice_id: str
    seller_slice_id: str
    price: float = Field(..., description="Cleared price, USD per Mbps-hour")
    quantity_mbps: float
    executed_at: datetime


class AgentDecisionEvent(BaseModel):
    topic: Literal["agent.decision"] = "agent.decision"
    slice_id: str
    role: AgentRole
    decision: AgentDecisionType
    quantity_mbps: Optional[float] = None
    price: Optional[float] = None
    qos_priority: Optional[QosPriority] = None
    reasoning: str
    sla_gate_passed: bool
    decided_at: datetime
