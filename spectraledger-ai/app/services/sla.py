"""
SLA risk evaluator: a lightweight gate on the Seller Agent's listing
decision.

v1 (implemented): a static threshold check. ForecastResponse.confidence_score
is already derived directly from the prediction interval width relative to
the point forecast (see app/services/forecasting.py: confidence_score =
exp(-relative_width)), so gating on confidence_score *is* gating on
interval width -- just on a normalized 0-1 scale that's easier to reason
about and to set a per-slice threshold on.

v2 (future, if time allows): replace `passes_confidence_gate` with a small
classifier (e.g. LogisticRegression/LightGBM classifier) trained to predict
"was this forecast's error small enough to safely sell against" from the
same feature set forecasting.py already builds, instead of a hand-set
threshold. Left as a TODO given the hackathon time budget -- the interface
below (`evaluate_listing_risk`) would not need to change, only its
internals, so the agent code calling it is unaffected by the upgrade.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import DEFAULT_SLA_MIN_CONFIDENCE, SLA_MAX_UTILIZATION_AFTER_LISTING
from app.schemas.forecast import ForecastResponse


@dataclass
class SlaGateResult:
    passed: bool
    reason: str
    min_confidence_required: float
    observed_confidence: float
    ci_width_mbps: float


def evaluate_listing_risk(
    forecast: ForecastResponse,
    min_confidence: float = DEFAULT_SLA_MIN_CONFIDENCE,
) -> SlaGateResult:
    """Static threshold check (v1). Refuses to list if the forecast's
    confidence_score falls below `min_confidence` -- equivalently, if its
    confidence interval is too wide relative to the point forecast to trust
    for a listing decision."""
    ci_width = forecast.confidence_interval.width
    passed = forecast.confidence_score >= min_confidence

    if passed:
        reason = (
            f"Forecast confidence {forecast.confidence_score:.2f} meets the "
            f"SLA safety threshold ({min_confidence:.2f}); interval width "
            f"{ci_width:.1f} Mbps is tight enough to trust for listing."
        )
    else:
        reason = (
            f"Forecast confidence {forecast.confidence_score:.2f} is below the "
            f"SLA safety threshold ({min_confidence:.2f}); interval width "
            f"{ci_width:.1f} Mbps is too wide to safely commit bandwidth for sale."
        )

    return SlaGateResult(
        passed=passed,
        reason=reason,
        min_confidence_required=min_confidence,
        observed_confidence=forecast.confidence_score,
        ci_width_mbps=ci_width,
    )


def max_safe_listing_quantity(capacity_mbps: float, predicted_demand_mbps: float) -> float:
    """How much bandwidth can be safely listed without projected utilization
    (after listing) exceeding SLA_MAX_UTILIZATION_AFTER_LISTING. This is the
    "safety buffer" the Seller Agent's evaluate node applies on top of the
    confidence gate above."""
    max_committable = capacity_mbps * SLA_MAX_UTILIZATION_AFTER_LISTING
    surplus = max_committable - predicted_demand_mbps
    return max(surplus, 0.0)
