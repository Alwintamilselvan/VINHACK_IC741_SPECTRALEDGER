from fastapi import APIRouter

from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.services.forecasting import predict

router = APIRouter(tags=["forecast"])


@router.post("/forecast", response_model=ForecastResponse)
async def forecast(req: ForecastRequest) -> ForecastResponse:
    """Predict bandwidth demand for a slice over the next 15-60 minutes,
    with a prediction interval, from a recent telemetry window."""
    return predict(
        telemetry=req.telemetry,
        slice_id=req.slice_id,
        slice_type=req.slice_type.value,
        horizon_minutes=req.horizon_minutes,
    )
