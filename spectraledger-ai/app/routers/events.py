from fastapi import APIRouter, HTTPException

from app.services.broadcast import recent_events

router = APIRouter(tags=["integration"])

VALID_TOPICS = {"telemetry.raw", "trade.executed", "agent.decision"}


@router.get("/events/{topic}")
async def get_recent_events(topic: str, limit: int = 20):
    """Polling fallback for teams that don't want to stand up a WebSocket
    client yet: returns the most recent events broadcast on a topic, from
    an in-memory ring buffer. Same JSON shape as the WebSocket frames."""
    if topic not in VALID_TOPICS:
        raise HTTPException(status_code=404, detail=f"Unknown topic '{topic}'. Valid: {sorted(VALID_TOPICS)}")
    return {"topic": topic, "events": recent_events(topic, limit)}
