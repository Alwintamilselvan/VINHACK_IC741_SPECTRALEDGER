"""
Maps our internal TradeExecutedEvent (the stable, documented AI Engine
event contract used on /ws/stream and /events/trade.executed) onto the
exact JSON shape the Java Spring Boot backend's webhook receiver expects.

Keeping this as a separate translation layer means the internal event
contract never has to change to satisfy an external consumer's schema --
if the Java side's expected fields shift, only this file changes.
"""
from __future__ import annotations

from app.schemas.events import TradeExecutedEvent


def to_java_backend_payload(event: TradeExecutedEvent) -> dict:
    return {
        "action": "EXECUTE_MICRO_TRADE",
        "sellerId": event.seller_slice_id,
        "buyerId": event.buyer_slice_id,
        "megabitsRented": event.quantity_mbps,
        "totalAmountUSD": round(event.price * event.quantity_mbps, 2),
        "timestamp": event.executed_at.isoformat(),
    }


def to_judge_log_line(event: TradeExecutedEvent) -> str:
    total = round(event.price * event.quantity_mbps, 2)
    return (
        f"[SPECTRALEDGER AI]: Detected {event.quantity_mbps:.0f} Mbps idle at "
        f"{event.seller_slice_id}. Automatically brokered "
        f"{event.quantity_mbps:.0f} Mbps lease to {event.buyer_slice_id} "
        f"for ${total:.2f}."
    )