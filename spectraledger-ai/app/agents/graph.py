"""
Autonomous trading agents, built as small LangGraph graphs.

Two roles, two graphs (so each is independently inspectable/demoable),
sharing the same underlying forecast -> price -> SLA-gate pipeline:

    Seller Agent graph:  read_state -> evaluate -> seller_decide -> confirm_trade -> END
    Buyer Agent graph:   read_state -> evaluate -> buyer_decide  -> confirm_trade -> END

Single-round evaluate-and-decide only (no multi-round negotiation, per the
hackathon time budget). "evaluate" is where the agent calls the real
/forecast and /price pipeline (via the forecasting/pricing services
directly -- same process, real computation, not a stub) and where the SLA
risk gate + safety buffer are applied. "decide" turns that into a
list/hold/buy/sell decision with a natural-language reasoning string.
"confirm_trade" checks the supplied order book for a matching counter-order
and upgrades the decision to an executed trade if one clears.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.config import DEFAULT_SLA_MIN_CONFIDENCE
from app.schemas.agent import SliceState
from app.schemas.common import (
    AgentDecisionType,
    AgentRole,
    Order,
    OrderSide,
    QosPriority,
    TelemetryPoint,
)
from app.schemas.forecast import ForecastResponse
from app.schemas.pricing import PriceRequest, PriceResponse
from app.services import pricing as pricing_service
from app.services import sla as sla_service
from app.services.forecasting import predict as forecast_predict

# Minimum quantity worth acting on -- avoids "list 0.3 Mbps" noise decisions.
_MIN_ACTIONABLE_MBPS = 5.0


class AgentState(TypedDict, total=False):
    role: str
    slice_state: SliceState
    telemetry: List[TelemetryPoint]
    order_book: List[Order]
    horizon_minutes: int

    forecast: ForecastResponse
    pricing: PriceResponse
    sla_passed: bool
    sla_reason: str
    max_safe_qty: float

    decision: str
    quantity_mbps: Optional[float]
    price: Optional[float]
    matched_order_id: Optional[str]
    reasoning: str
    decided_at: datetime


# --------------------------------------------------------------------------
# Shared nodes
# --------------------------------------------------------------------------

def node_read_state(state: AgentState) -> AgentState:
    """Entry node: no transformation needed (FastAPI/Pydantic already
    validated the input), but kept as its own node so the graph visibly
    starts with a 'read state' step, matching the intended agent loop."""
    # Re-affirm the role as a no-op write -- LangGraph requires every node
    # to write at least one key, and this keeps the node a true pass-through.
    return {"role": state["role"]}


def node_evaluate(state: AgentState) -> AgentState:
    """Calls the real forecasting + pricing pipeline, then applies the SLA
    risk gate and safety-buffer sizing. This is the node that makes the
    agent a real pipeline rather than a disconnected stub."""
    slice_state = state["slice_state"]
    telemetry = state["telemetry"]
    horizon_minutes = state.get("horizon_minutes", 30)

    forecast = forecast_predict(
        telemetry=telemetry,
        slice_id=slice_state.slice_id,
        slice_type=slice_state.slice_type.value,
        horizon_minutes=horizon_minutes,
    )

    price_req = PriceRequest(
        slice_id=slice_state.slice_id,
        capacity_mbps=slice_state.capacity_mbps,
        current_utilization=slice_state.current_utilization,
        qos_priority=slice_state.qos_priority,
        forecast=forecast,
    )
    price = pricing_service.compute_price(price_req)

    min_conf = slice_state.sla_min_confidence or DEFAULT_SLA_MIN_CONFIDENCE
    gate = sla_service.evaluate_listing_risk(forecast, min_confidence=min_conf)
    max_safe_qty = sla_service.max_safe_listing_quantity(
        slice_state.capacity_mbps, forecast.predicted_demand_mbps
    )

    return {
        "forecast": forecast,
        "pricing": price,
        "sla_passed": gate.passed,
        "sla_reason": gate.reason,
        "max_safe_qty": max_safe_qty,
    }


def node_confirm_trade(state: AgentState) -> AgentState:
    """Looks for a matching resting order on the opposite side. If one
    clears, upgrades the tentative decision (list/buy) into an executed
    trade (sell/buy) against that order, at that order's price."""
    decision = state.get("decision", AgentDecisionType.HOLD.value)
    role = state["role"]
    order_book = state.get("order_book", [])
    reasoning = state.get("reasoning", "")
    own_slice_id = state["slice_state"].slice_id

    if decision not in (AgentDecisionType.LIST.value, AgentDecisionType.BUY.value):
        return {"decision": decision}

    our_price = state.get("price")
    our_qty = state.get("quantity_mbps") or 0.0
    if our_price is None or our_qty <= 0:
        return {"decision": decision}

    if role == AgentRole.SELLER.value:
        # A seller looks for a resting BID priced at or above our ask.
        # Exclude the slice's own resting orders -- a slice can't trade with itself.
        candidates = [
            o for o in order_book
            if o.side == OrderSide.BID and o.price >= our_price and o.quantity_mbps > 0
            and o.slice_id != own_slice_id
        ]
        candidates.sort(key=lambda o: -o.price)
    else:
        # A buyer looks for a resting ASK priced at or below our bid.
        candidates = [
            o for o in order_book
            if o.side == OrderSide.ASK and o.price <= our_price and o.quantity_mbps > 0
            and o.slice_id != own_slice_id
        ]
        candidates.sort(key=lambda o: o.price)

    if not candidates:
        reasoning += " No matching counter-order in the current order book -- decision stands unmatched."
        return {"reasoning": reasoning}

    match = candidates[0]
    matched_qty = min(our_qty, match.quantity_mbps)
    final_decision = AgentDecisionType.SELL.value if role == AgentRole.SELLER.value else AgentDecisionType.BUY.value

    reasoning += (
        f" Matched against order {match.order_id} (price {match.price:.4f}, "
        f"qty {match.quantity_mbps:.0f} Mbps) -> trade executed for "
        f"{matched_qty:.0f} Mbps at {match.price:.4f} USD/Mbps-hour."
    )

    return {
        "decision": final_decision,
        "quantity_mbps": matched_qty,
        "price": match.price,
        "matched_order_id": match.order_id,
        "reasoning": reasoning,
    }


# --------------------------------------------------------------------------
# Seller Agent
# --------------------------------------------------------------------------

def node_seller_decide(state: AgentState) -> AgentState:
    slice_state = state["slice_state"]
    forecast = state["forecast"]
    price = state["pricing"]
    sla_passed = state["sla_passed"]
    sla_reason = state["sla_reason"]
    max_safe_qty = state["max_safe_qty"]

    if not sla_passed:
        return {
            "decision": AgentDecisionType.HOLD.value,
            "quantity_mbps": None,
            "price": None,
            "matched_order_id": None,
            "reasoning": f"SLA risk gate BLOCKED listing: {sla_reason}",
            "decided_at": datetime.now(timezone.utc),
        }

    if max_safe_qty < _MIN_ACTIONABLE_MBPS:
        reasoning = (
            f"SLA gate passed ({sla_reason}) but forecasted demand "
            f"({forecast.predicted_demand_mbps:.0f} Mbps) leaves only "
            f"{max_safe_qty:.1f} Mbps of safe surplus on "
            f"{slice_state.capacity_mbps:.0f} Mbps capacity -- too little to "
            f"list without risking the safety buffer. Holding."
        )
        return {
            "decision": AgentDecisionType.HOLD.value,
            "quantity_mbps": None,
            "price": None,
            "matched_order_id": None,
            "reasoning": reasoning,
            "decided_at": datetime.now(timezone.utc),
        }

    reasoning = (
        f"SLA gate passed ({sla_reason}). Forecast predicts "
        f"{forecast.predicted_demand_mbps:.0f} Mbps demand ({forecast.trend}) over the next "
        f"{forecast.horizon_minutes} min, leaving a safe surplus of {max_safe_qty:.0f} Mbps on "
        f"{slice_state.capacity_mbps:.0f} Mbps capacity. Listing {max_safe_qty:.0f} Mbps at ask "
        f"price {price.ask_price:.4f} USD/Mbps-hour ({slice_state.qos_priority.value} QoS)."
    )
    return {
        "decision": AgentDecisionType.LIST.value,
        "quantity_mbps": round(max_safe_qty, 2),
        "price": price.ask_price,
        "matched_order_id": None,
        "reasoning": reasoning,
        "decided_at": datetime.now(timezone.utc),
    }


def build_seller_graph():
    graph = StateGraph(AgentState)
    graph.add_node("read_state", node_read_state)
    graph.add_node("evaluate", node_evaluate)
    graph.add_node("decide", node_seller_decide)
    graph.add_node("confirm_trade", node_confirm_trade)

    graph.set_entry_point("read_state")
    graph.add_edge("read_state", "evaluate")
    graph.add_edge("evaluate", "decide")
    graph.add_edge("decide", "confirm_trade")
    graph.add_edge("confirm_trade", END)
    return graph.compile()


# --------------------------------------------------------------------------
# Buyer Agent
# --------------------------------------------------------------------------

def node_buyer_decide(state: AgentState) -> AgentState:
    slice_state = state["slice_state"]
    forecast = state["forecast"]
    price = state["pricing"]

    from app.config import SLA_MAX_UTILIZATION_AFTER_LISTING

    safe_capacity = slice_state.capacity_mbps * SLA_MAX_UTILIZATION_AFTER_LISTING
    shortfall = forecast.predicted_demand_mbps - safe_capacity

    if shortfall < _MIN_ACTIONABLE_MBPS:
        reasoning = (
            f"Forecast predicts {forecast.predicted_demand_mbps:.0f} Mbps demand "
            f"({forecast.trend}), comfortably under the "
            f"{safe_capacity:.0f} Mbps safety-buffered capacity "
            f"({slice_state.capacity_mbps:.0f} Mbps total). No need to buy extra bandwidth."
        )
        return {
            "decision": AgentDecisionType.HOLD.value,
            "quantity_mbps": None,
            "price": None,
            "matched_order_id": None,
            "reasoning": reasoning,
            "decided_at": datetime.now(timezone.utc),
        }

    reasoning = (
        f"Forecast predicts {forecast.predicted_demand_mbps:.0f} Mbps demand "
        f"({forecast.trend}) over the next {forecast.horizon_minutes} min, "
        f"exceeding the {safe_capacity:.0f} Mbps safety-buffered capacity by "
        f"{shortfall:.0f} Mbps. Bidding for {shortfall:.0f} Mbps at bid price "
        f"{price.bid_price:.4f} USD/Mbps-hour to cover the shortfall before SLA risk builds."
    )
    return {
        "decision": AgentDecisionType.BUY.value,
        "quantity_mbps": round(shortfall, 2),
        "price": price.bid_price,
        "matched_order_id": None,
        "reasoning": reasoning,
        "decided_at": datetime.now(timezone.utc),
    }


def build_buyer_graph():
    graph = StateGraph(AgentState)
    graph.add_node("read_state", node_read_state)
    graph.add_node("evaluate", node_evaluate)
    graph.add_node("decide", node_buyer_decide)
    graph.add_node("confirm_trade", node_confirm_trade)

    graph.set_entry_point("read_state")
    graph.add_edge("read_state", "evaluate")
    graph.add_edge("evaluate", "decide")
    graph.add_edge("decide", "confirm_trade")
    graph.add_edge("confirm_trade", END)
    return graph.compile()


_SELLER_GRAPH = None
_BUYER_GRAPH = None


def get_graph(role: AgentRole):
    global _SELLER_GRAPH, _BUYER_GRAPH
    if role == AgentRole.SELLER:
        if _SELLER_GRAPH is None:
            _SELLER_GRAPH = build_seller_graph()
        return _SELLER_GRAPH
    else:
        if _BUYER_GRAPH is None:
            _BUYER_GRAPH = build_buyer_graph()
        return _BUYER_GRAPH


def run_agent(
    role: AgentRole,
    slice_state: SliceState,
    telemetry: List[TelemetryPoint],
    order_book: List[Order],
    horizon_minutes: int = 30,
) -> AgentState:
    graph = get_graph(role)
    initial_state: AgentState = {
        "role": role.value,
        "slice_state": slice_state,
        "telemetry": telemetry,
        "order_book": order_book,
        "horizon_minutes": horizon_minutes,
    }
    final_state = graph.invoke(initial_state)
    return final_state


def evaluate_and_decide(
    role: AgentRole,
    slice_state: SliceState,
    telemetry: List[TelemetryPoint],
    horizon_minutes: int = 30,
) -> AgentState:
    """Runs read_state -> evaluate -> decide WITHOUT confirm_trade's local
    order-book matching -- for a caller that wants to submit the resulting
    LIST/BUY decision to an external market (the live Java backend's order
    book) instead of matching it against our own in-memory book. See
    app/services/trade_settlement.py, which calls this and then either
    submits live or falls back to node_confirm_trade itself."""
    state: AgentState = {
        "role": role.value,
        "slice_state": slice_state,
        "telemetry": telemetry,
        "order_book": [],
        "horizon_minutes": horizon_minutes,
    }
    state.update(node_read_state(state))
    state.update(node_evaluate(state))
    decide_fn = node_seller_decide if role == AgentRole.SELLER else node_buyer_decide
    state.update(decide_fn(state))
    return state