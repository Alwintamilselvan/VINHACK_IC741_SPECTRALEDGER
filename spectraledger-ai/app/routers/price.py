from fastapi import APIRouter

from app.schemas.pricing import PriceRequest, PriceResponse
from app.services.pricing import compute_price

router = APIRouter(tags=["price"])


@router.post("/price", response_model=PriceResponse)
async def price(req: PriceRequest) -> PriceResponse:
    """Compute a bid/ask price from utilization + a prior /forecast output,
    using the transparent formula: base_rate * congestion_multiplier *
    qos_priority_weight * urgency_factor. Every factor is echoed back in
    `components` for explainability."""
    return compute_price(req)
