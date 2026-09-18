"""
Shared "submit this decision somewhere it can actually clear" logic, used by
the autonomous market-maker loop (app/services/autonomous.py) so it doesn't
duplicate the live-backend-vs-local-fallback branching inline.

If JAVA_BACKEND_BASE_URL is configured, a LIST/BUY decision is submitted as a
real order to the Java backend (POST /api/orders) instead of matched against
the AI engine's own in-memory book -- the backend has its own matching
engine, per the integration note. If the backend isn't configured, or the
submission call fails for any reason (backend down, a mid-demo network
blip, an unrecognized response), this transparently falls back to the
original local order-book matching (node_confirm_trade), so the AI engine
keeps working standalone exactly as it always has.

Note: the price the rest of this codebase carries everywhere (PriceResponse,
Order.price, an agent's decided "price") is USD per Mbps-HOUR. The backend's
/api/orders wants pricePerMbpsPerMin -- that's a straight /60, not a
total-vs-rate conversion (confirmed by reading pricing.py directly: it's a
rate on both sides, just a different time unit).
"""
from __future__ import annotations

from typing import List

from app.agents.graph import node_confirm_trade
from app.config import JAVA_BACKEND_BASE_URL, JAVA_BACKEND_ORDER_DURATION_MINUTES
from app.schemas.agent import SliceState
from app.schemas.common import AgentDecisionType, AgentRole, Order
from app.services import backend_client


async def settle_decision(
    role: AgentRole,
    slice_state: SliceState,
    agent_state: dict,
    order_book_snapshot: List[Order],
) -> dict:
    """Takes the AgentState produced by evaluate_and_decide() (BEFORE any
    local matching), and either submits it live or matches it locally.
    Returns an AgentState-shaped dict with the same keys node_confirm_trade
    would have produced (decision/quantity_mbps/price/matched_order_id/
    reasoning), plus "settled_live": bool so callers know which path was
    taken -- when True, no local order-book bookkeeping is needed, because
    the fill (if any) will be observed later by the backend trade poller."""
    decision = agent_state.get("decision")

    if decision not in (AgentDecisionType.LIST.value, AgentDecisionType.BUY.value):
        return {**agent_state, "settled_live": False}

    if JAVA_BACKEND_BASE_URL:
        price = agent_state.get("price")
        quantity = agent_state.get("quantity_mbps")
        if price is not None and quantity:
            side = "ask" if role == AgentRole.SELLER else "bid"
            response = await backend_client.submit_order(
                slice_id=slice_state.slice_id,
                capacity_mbps=slice_state.capacity_mbps,
                side=side,
                quantity_mbps=quantity,
                price_per_mbps_per_min=price / 60.0,
                duration_minutes=JAVA_BACKEND_ORDER_DURATION_MINUTES,
                qos_tier=slice_state.qos_priority.value.upper(),
            )
            if response is not None:
                reasoning = agent_state.get("reasoning", "") + (
                    " Order submitted to the live backend order book "
                    "(POST /api/orders) -- any fill will be observed via "
                    "the backend trade poller, not matched locally."
                )
                return {**agent_state, "matched_order_id": None, "reasoning": reasoning, "settled_live": True}
            # Submission failed for any reason -- fall through to local matching.

    local_result = node_confirm_trade({
        **agent_state,
        "role": role.value,
        "slice_state": slice_state,
        "order_book": order_book_snapshot,
    })
    return {**agent_state, **local_result, "settled_live": False}