"""
Dynamic pricing engine.

Deliberately NOT a black-box model -- a transparent formula so every
number in the price can be explained to a judge (or a trading partner)
in one sentence:

    price = base_rate * congestion_multiplier * qos_priority_weight * urgency_factor

congestion_multiplier
    Scales with how "tight" the slice's capacity is, blending current
    utilization with the forecast's projected utilization (weighted
    towards the forecast, since pricing should be forward-looking).

qos_priority_weight
    Flat lookup by QoS tier (gold/silver/bronze) -- SLA-critical slices
    pay/charge more.

urgency_factor
    Scales with how soon the forecasted surplus window closes: a short
    horizon (the near-term prediction) combined with a "rising" demand
    trend means the window to trade this surplus is closing fast, so
    urgency -- and price -- go up. A long horizon with a flat/falling
    trend means there's no rush, so urgency stays near its floor.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from app.config import (
    BID_ASK_SPREAD_PCT,
    CONGESTION_MULTIPLIER_MAX,
    CONGESTION_MULTIPLIER_MIN,
    DEFAULT_BASE_RATE,
    QOS_PRIORITY_WEIGHTS,
    URGENCY_FACTOR_MAX,
    URGENCY_FACTOR_MIN,
)
from app.schemas.pricing import PriceComponents, PriceRequest, PriceResponse

# Horizon range accepted by ForecastRequest/AgentEvaluateRequest -- used to
# normalize horizon_minutes into a 0-1 urgency signal.
_HORIZON_MIN = 15
_HORIZON_MAX = 60

_TREND_URGENCY_COMPONENT = {
    "rising": 1.0,
    "stable": 0.5,
    "falling": 0.1,
}


def _congestion_multiplier(current_utilization: float, predicted_demand_mbps: float, capacity_mbps: float) -> float:
    projected_utilization = predicted_demand_mbps / capacity_mbps if capacity_mbps > 0 else 0.0
    blended = 0.3 * current_utilization + 0.7 * projected_utilization
    raw = 0.5 + 1.5 * blended  # 0.5 at 0% blended utilization, 2.0 at 100%
    return float(np.clip(raw, CONGESTION_MULTIPLIER_MIN, CONGESTION_MULTIPLIER_MAX)), projected_utilization, blended


def _urgency_factor(horizon_minutes: int, trend: str) -> tuple[float, float, float]:
    span = max(_HORIZON_MAX - _HORIZON_MIN, 1)
    horizon_urgency = 1.0 - (horizon_minutes - _HORIZON_MIN) / span  # short horizon -> more urgent
    horizon_urgency = float(np.clip(horizon_urgency, 0.0, 1.0))
    trend_component = _TREND_URGENCY_COMPONENT.get(trend, 0.5)
    urgency_score = 0.6 * horizon_urgency + 0.4 * trend_component
    urgency_factor = URGENCY_FACTOR_MIN + urgency_score * (URGENCY_FACTOR_MAX - URGENCY_FACTOR_MIN)
    return float(urgency_factor), horizon_urgency, trend_component


def compute_price(req: PriceRequest) -> PriceResponse:
    base_rate = req.base_rate if req.base_rate is not None else DEFAULT_BASE_RATE
    forecast = req.forecast

    congestion_multiplier, projected_utilization, blended_utilization = _congestion_multiplier(
        req.current_utilization, forecast.predicted_demand_mbps, req.capacity_mbps
    )
    qos_priority_weight = QOS_PRIORITY_WEIGHTS.get(req.qos_priority.value, 1.0)
    urgency_factor, horizon_urgency, trend_component = _urgency_factor(forecast.horizon_minutes, forecast.trend)

    mid_price = base_rate * congestion_multiplier * qos_priority_weight * urgency_factor
    half_spread = mid_price * (BID_ASK_SPREAD_PCT / 2.0)
    bid_price = max(mid_price - half_spread, 0.0)
    ask_price = mid_price + half_spread

    components = PriceComponents(
        base_rate=round(base_rate, 6),
        congestion_multiplier=round(congestion_multiplier, 4),
        qos_priority_weight=round(qos_priority_weight, 4),
        urgency_factor=round(urgency_factor, 4),
    )

    explanation = (
        f"Forecast projects {forecast.predicted_demand_mbps:.0f} Mbps demand "
        f"({projected_utilization * 100:.0f}% of {req.capacity_mbps:.0f} Mbps capacity) vs. "
        f"{req.current_utilization * 100:.0f}% current utilization, blending to "
        f"{blended_utilization * 100:.0f}% -> congestion_multiplier={components.congestion_multiplier:.2f}x. "
        f"{req.qos_priority.value.capitalize()} QoS applies a {components.qos_priority_weight:.2f}x weight. "
        f"Trend is '{forecast.trend}' at a {forecast.horizon_minutes}-min horizon "
        f"(horizon urgency {horizon_urgency:.2f}, trend component {trend_component:.2f}) -> "
        f"urgency_factor={components.urgency_factor:.2f}x. "
        f"Mid price = {base_rate:.4f} x {components.congestion_multiplier:.2f} x "
        f"{components.qos_priority_weight:.2f} x {components.urgency_factor:.2f} = {mid_price:.4f} "
        f"USD/Mbps-hour."
    )

    return PriceResponse(
        slice_id=req.slice_id,
        generated_at=datetime.now(timezone.utc),
        bid_price=round(bid_price, 6),
        ask_price=round(ask_price, 6),
        mid_price=round(mid_price, 6),
        confidence_score=forecast.confidence_score,
        components=components,
        explanation=explanation,
    )
