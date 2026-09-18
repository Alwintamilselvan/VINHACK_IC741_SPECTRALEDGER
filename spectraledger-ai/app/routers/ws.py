from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.broadcast import manager

router = APIRouter(tags=["integration"])


@router.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    """Single WebSocket firehose for all three topics (telemetry.raw,
    trade.executed, agent.decision), each frame tagged with a "topic"
    field per app/schemas/events.py. Stands in for a Kafka topic set for
    the hackathon demo -- swap ConnectionManager for a Kafka producer
    later without touching the event schemas or router code that calls
    broadcast_event()."""
    await manager.connect(websocket)
    try:
        while True:
            # Agents don't expect client->server messages; just drain
            # anything sent (e.g. browser keepalive pings) and stay open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
