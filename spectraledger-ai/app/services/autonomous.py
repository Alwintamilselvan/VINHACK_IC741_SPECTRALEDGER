"""
Autonomous market-maker loop.

This is what makes the AI Engine an actual broker instead of a library
that only reacts to /agent/evaluate calls: a background task that, on its
own, re-evaluates every demo slice as both a potential seller and a
potential buyer -- against the live telemetry feed and the shared
persistent order book (app/services/orderbook.py) -- every few seconds,
with zero external API calls required.

Each tick, for every slice:
    1. Pull its live rolling telemetry window (broadcast.py's feed loop
       keeps this updated every ~2s).
    2. Run the Seller Agent graph and the Buyer Agent graph against it,
       exactly as /agent/evaluate does -- same forecast, same price, same
       SLA gate, same LangGraph nodes. Nothing about the decision logic is
       duplicated or special-cased for "autonomous mode."
    3. If a decision matched a resting order already in the book, settle
       it: shrink/remove that order, broadcast trade.executed, and fire
       the outbound webhook to the Java backend.
    4. If a decision didn't match anything yet (an unmatched list/buy),
       rest it in the shared order book as that slice's live quote, so a
       DIFFERENT slice's agent can match against it on a later tick --
       this is the actual cross-slice, central-market-maker behavior.
    5. Broadcast every non-trivial decision (skip HOLDs to avoid spamming
       the event stream every tick with "nothing to do").

This closes two of the three gaps flagged earlier: (1) continuous,
unprompted surplus/shortfall detection instead of only on-demand, and
(3) a persistent market that pairs ANY buyer with ANY seller over time,
not just whoever's order book snapshot happened to be passed into one
request.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.agents.graph import evaluate_and_decide
from app.config import AUTONOMOUS_LOOP_TICK_SECONDS, DEFAULT_SLA_MIN_CONFIDENCE
from app.schemas.agent import SliceState
from app.schemas.common import AgentDecisionType, AgentRole, OrderSide, QosPriority
from app.schemas.events import AgentDecisionEvent, TradeExecutedEvent
from app.services.broadcast import broadcast_event, get_live_window
from app.services.orderbook import book
from app.services.revenue import ledger as revenue_ledger
from app.services.telemetry_generator import DEFAULT_PROFILES
from app.services.trade_settlement import settle_decision
from app.services.webhook import fire_trade_webhook

logger = logging.getLogger("spectraledger.autonomous")

# Rough default QoS tier per workload type for the autonomous loop, since
# the live simulator doesn't have a human specifying this per request the
# way /agent/evaluate callers do. Purely a demo default -- a real deployment
# would pull each slice's actual contracted QoS tier from the backend.
_DEFAULT_QOS_BY_TYPE = {
    "URLLC": QosPriority.GOLD,
    "AI_TRAINING": QosPriority.GOLD,
    "eMBB": QosPriority.SILVER,
    "mMTC": QosPriority.BRONZE,
}

_MIN_WINDOW_POINTS = 6  # matches ForecastRequest's minimum telemetry window


def _build_slice_state(profile):
    window = get_live_window(profile.slice_id, n=8)
    if len(window) < _MIN_WINDOW_POINTS:
        return None, window

    latest_throughput = window[-1].throughput_mbps
    utilization = float(min(latest_throughput / profile.capacity_mbps, 1.15))

    return SliceState(
        slice_id=profile.slice_id,
        slice_type=profile.slice_type,
        capacity_mbps=profile.capacity_mbps,
        current_utilization=utilization,
        qos_priority=_DEFAULT_QOS_BY_TYPE.get(profile.slice_type, QosPriority.SILVER),
        sla_min_confidence=DEFAULT_SLA_MIN_CONFIDENCE,
    ), window


async def _settle_match(role: AgentRole, slice_state: SliceState, result: dict) -> None:
    """A decision matched a resting order in the shared book -- shrink/remove
    that order, broadcast the trade, and fire the outbound webhook."""
    matched_order_id = result["matched_order_id"]
    matched_order = book.get(matched_order_id)
    counterparty_slice_id = matched_order.slice_id if matched_order else matched_order_id
    qty = result["quantity_mbps"]
    decided_at = result.get("decided_at") or datetime.now(timezone.utc)

    book.reduce_or_remove(matched_order_id, qty)

    if role == AgentRole.SELLER:
        seller_slice_id, buyer_slice_id = slice_state.slice_id, counterparty_slice_id
    else:
        buyer_slice_id, seller_slice_id = slice_state.slice_id, counterparty_slice_id

    trade_event = TradeExecutedEvent(
        trade_id=str(uuid.uuid4()),
        buyer_slice_id=buyer_slice_id,
        seller_slice_id=seller_slice_id,
        price=result["price"],
        quantity_mbps=qty,
        executed_at=decided_at,
    )
    await broadcast_event(trade_event)
    await fire_trade_webhook(trade_event)
    revenue_ledger.record_trade_fee(trade_event)
    logger.info(
        "AUTONOMOUS TRADE: %s Mbps @ %.4f USD/Mbps-hr (buyer=%s, seller=%s)",
        qty, result["price"], buyer_slice_id, seller_slice_id,
    )


async def _process_role(profile, role: AgentRole) -> None:
    slice_state, window = _build_slice_state(profile)
    if slice_state is None:
        return  # not enough live telemetry yet -- skip this slice this tick

    order_book_snapshot = book.all_orders()

    # Same forecast -> price -> SLA-gate -> decide pipeline as always
    # (evaluate_and_decide runs read_state/evaluate/decide, just without
    # confirm_trade's local matching -- see app/agents/graph.py). What
    # happens to a LIST/BUY decision next is settle_decision's job: submit
    # it to the real Java backend's order book if one is configured and
    # reachable, otherwise match it locally exactly as before.
    decision_only = evaluate_and_decide(role, slice_state, window, horizon_minutes=30)
    result = await settle_decision(role, slice_state, decision_only, order_book_snapshot)

    decision = result["decision"]
    decided_at = result.get("decided_at") or datetime.now(timezone.utc)

    if decision != AgentDecisionType.HOLD.value:
        await broadcast_event(AgentDecisionEvent(
            slice_id=slice_state.slice_id,
            role=role,
            decision=AgentDecisionType(decision),
            quantity_mbps=result.get("quantity_mbps"),
            price=result.get("price"),
            qos_priority=slice_state.qos_priority,
            reasoning=result["reasoning"],
            sla_gate_passed=result["sla_passed"],
            decided_at=decided_at,
        ))

    if result.get("settled_live"):
        # Submitted to the real backend -- any fill will be observed and
        # broadcast later by the backend trade poller, not here. Nothing to
        # do to our own local order book for this slice/role this tick.
        return

    if result.get("matched_order_id") and decision in (AgentDecisionType.SELL.value, AgentDecisionType.BUY.value):
        await _settle_match(role, slice_state, result)
    elif decision in (AgentDecisionType.LIST.value, AgentDecisionType.BUY.value):
        # Unmatched -- rest this slice's quote in the shared book so a
        # DIFFERENT slice can match it on a future tick.
        side = OrderSide.ASK if role == AgentRole.SELLER else OrderSide.BID
        book.upsert_slice_quote(
            slice_state.slice_id, side, result["price"], result.get("quantity_mbps") or 0.0,
            slice_state.qos_priority,
        )
    else:
        # HOLD -- clear any stale resting quote from this slice on the
        # relevant side, since it no longer wants to trade.
        side = OrderSide.ASK if role == AgentRole.SELLER else OrderSide.BID
        book.upsert_slice_quote(slice_state.slice_id, side, 0.0, 0.0, slice_state.qos_priority)


async def _tick() -> None:
    for profile in DEFAULT_PROFILES:
        for role in (AgentRole.SELLER, AgentRole.BUYER):
            try:
                await _process_role(profile, role)
            except Exception:
                logger.exception("Autonomous tick failed for slice=%s role=%s", profile.slice_id, role.value)


async def autonomous_market_loop(tick_seconds: float = AUTONOMOUS_LOOP_TICK_SECONDS) -> None:
    logger.info(
        "Starting autonomous market-maker loop (%d slices, every %.0fs)",
        len(DEFAULT_PROFILES), tick_seconds,
    )
    try:
        while True:
            await _tick()
            await asyncio.sleep(tick_seconds)
    except asyncio.CancelledError:
        logger.info("Autonomous market-maker loop stopped")
        raise


_TASK: "asyncio.Task | None" = None


def start_autonomous_loop() -> None:
    global _TASK
    if _TASK is None or _TASK.done():
        _TASK = asyncio.create_task(autonomous_market_loop())


def stop_autonomous_loop() -> None:
    global _TASK
    if _TASK is not None:
        _TASK.cancel()
        _TASK = None