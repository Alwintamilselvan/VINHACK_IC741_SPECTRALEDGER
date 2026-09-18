import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from app.agents.graph import run_agent
from app.schemas.agent import AgentEvaluateRequest, AgentEvaluateResponse
from app.schemas.common import AgentDecisionType, OrderSide
from app.schemas.events import AgentDecisionEvent, TradeExecutedEvent
from app.services.broadcast import broadcast_event
from app.services.orderbook import book
from app.services.revenue import ledger as revenue_ledger
from app.services.webhook import fire_trade_webhook

router = APIRouter(tags=["agent"])


@router.post("/agent/evaluate", response_model=AgentEvaluateResponse)
async def agent_evaluate(req: AgentEvaluateRequest) -> AgentEvaluateResponse:
    """Runs the Seller or Buyer Agent's LangGraph (read state -> evaluate
    against forecast/price/SLA -> decide -> confirm trade if matched)
    against slice state + an order book.

    If `order_book` is omitted (or empty) in the request, this call falls
    back to the AI Engine's own persistent, cross-slice order book (see
    app/services/orderbook.py) instead of an empty list -- so a manual
    call here sees, and can match against, whatever the autonomous
    market-maker loop (or other manual calls) has already resting in the
    live market. Pass an explicit `order_book` to test against a specific
    snapshot instead; that behavior is unchanged from before.

    Internally calls the real forecasting + pricing pipeline (not stubs),
    and broadcasts an `agent.decision` event -- plus a `trade.executed`
    event and an outbound webhook to the Java backend if the decision
    matched a resting counter-order -- onto the /ws/stream integration
    layer.
    """
    order_book_snapshot = req.order_book or book.all_orders()

    result = run_agent(
        role=req.role,
        slice_state=req.slice_state,
        telemetry=req.telemetry,
        order_book=order_book_snapshot,
        horizon_minutes=req.horizon_minutes,
    )

    decided_at = result.get("decided_at") or datetime.now(timezone.utc)
    decision = AgentDecisionType(result["decision"])

    decision_event = AgentDecisionEvent(
        slice_id=req.slice_state.slice_id,
        role=req.role,
        decision=decision,
        quantity_mbps=result.get("quantity_mbps"),
        price=result.get("price"),
        qos_priority=req.slice_state.qos_priority,
        reasoning=result["reasoning"],
        sla_gate_passed=result["sla_passed"],
        decided_at=decided_at,
    )
    await broadcast_event(decision_event)

    matched_order_id = result.get("matched_order_id")
    if matched_order_id and decision in (AgentDecisionType.SELL, AgentDecisionType.BUY):
        matched_order = next((o for o in order_book_snapshot if o.order_id == matched_order_id), None)
        counterparty_slice_id = matched_order.slice_id if matched_order else matched_order_id
        quantity = result["quantity_mbps"]

        # If the matched order actually lives in the shared persistent book
        # (as opposed to a one-off snapshot the caller made up for this
        # request), settle it there too so the autonomous loop and everyone
        # else sees it as filled/reduced.
        book.reduce_or_remove(matched_order_id, quantity)

        if req.role.value == "seller":
            seller_slice_id, buyer_slice_id = req.slice_state.slice_id, counterparty_slice_id
        else:
            buyer_slice_id, seller_slice_id = req.slice_state.slice_id, counterparty_slice_id

        trade_event = TradeExecutedEvent(
            trade_id=str(uuid.uuid4()),
            buyer_slice_id=buyer_slice_id,
            seller_slice_id=seller_slice_id,
            price=result["price"],
            quantity_mbps=quantity,
            executed_at=decided_at,
        )
        await broadcast_event(trade_event)
        await fire_trade_webhook(trade_event)
        revenue_ledger.record_trade_fee(trade_event)
    elif decision in (AgentDecisionType.LIST, AgentDecisionType.BUY):
        # Unmatched -- rest this slice's quote in the shared book so a
        # later manual call, or the autonomous loop, can match it.
        side = OrderSide.ASK if req.role.value == "seller" else OrderSide.BID
        book.upsert_slice_quote(
            req.slice_state.slice_id, side, result["price"], result.get("quantity_mbps") or 0.0,
            req.slice_state.qos_priority,
        )

    return AgentEvaluateResponse(
        slice_id=req.slice_state.slice_id,
        role=req.role,
        decision=decision,
        quantity_mbps=result.get("quantity_mbps"),
        price=result.get("price"),
        matched_order_id=matched_order_id,
        reasoning=result["reasoning"],
        sla_gate_passed=result["sla_passed"],
        forecast=result["forecast"],
        pricing=result["pricing"],
        decided_at=decided_at,
    )
