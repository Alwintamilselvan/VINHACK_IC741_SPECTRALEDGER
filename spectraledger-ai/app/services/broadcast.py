"""
Integration layer: WebSocket pub/sub standing in for Kafka.

Per the API contract (app/schemas/events.py), three logical topics --
telemetry.raw, trade.executed, agent.decision -- are broadcast as JSON
frames over a single WebSocket endpoint (/ws/stream), each tagged with a
"topic" field. A real deployment would swap this ConnectionManager for a
Kafka producer/consumer without changing the event schemas or the call
sites below (`broadcast_event(...)`), which is the whole point of
defining the event shapes up front in the API contract.

Also hosts the live telemetry simulator: a background asyncio task that
walks the same synthetic-data model used to build the training set (see
telemetry_generator.py) forward in simulated time, broadcasting
telemetry.raw events every couple of seconds. This is both a demo feed
(so the frontend has something to show immediately) and the fallback data
source when no real 5G telemetry pipeline is connected yet.
"""
from __future__ import annotations

import asyncio
import itertools
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List

import numpy as np
from fastapi import WebSocket
from pydantic import BaseModel

from app.config import TELEMETRY_SAMPLE_INTERVAL_MINUTES
from app.schemas.common import TelemetryPoint
from app.schemas.events import AgentDecisionEvent, TelemetryRawEvent, TradeExecutedEvent
from app.services.telemetry_generator import DEFAULT_PROFILES, LiveSpikeState, next_live_sample

logger = logging.getLogger("spectraledger.broadcast")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info("WS client connected (%d total)", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.info("WS client disconnected (%d total)", len(self._connections))

    async def broadcast_json(self, payload: dict) -> None:
        dead = []
        async with self._lock:
            connections = list(self._connections)
        for ws in connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self._connections:
                        self._connections.remove(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()

# Keep a small in-memory ring buffer of recent events per topic so a client
# that connects mid-demo (or the README's curl examples) can see *something*
# even without a live WebSocket client -- handy for judges poking at the API.
_RECENT_EVENTS: Dict[str, List[dict]] = {"telemetry.raw": [], "trade.executed": [], "agent.decision": []}
_RECENT_EVENTS_MAX = 50


async def broadcast_event(event: BaseModel) -> None:
    """Broadcast any of TelemetryRawEvent / TradeExecutedEvent / AgentDecisionEvent."""
    payload = event.model_dump(mode="json")
    topic = payload.get("topic", "unknown")
    bucket = _RECENT_EVENTS.setdefault(topic, [])
    bucket.append(payload)
    if len(bucket) > _RECENT_EVENTS_MAX:
        del bucket[0: len(bucket) - _RECENT_EVENTS_MAX]
    await manager.broadcast_json(payload)


def recent_events(topic: str, limit: int = 20) -> List[dict]:
    return _RECENT_EVENTS.get(topic, [])[-limit:]


# --------------------------------------------------------------------------
# Live rolling telemetry windows
# --------------------------------------------------------------------------
# Maintained by the live feed loop below so background processes (the
# autonomous market-maker loop) can build a /forecast-shaped input without
# needing an external caller to supply a telemetry window -- this is what
# lets the AI Engine watch every slice on its own instead of only reacting
# to an incoming request.

_LIVE_WINDOW_MAXLEN = 12  # 60 min at 5-min simulated ticks
_LIVE_WINDOWS: Dict[str, Deque[TelemetryPoint]] = {
    p.slice_id: deque(maxlen=_LIVE_WINDOW_MAXLEN) for p in DEFAULT_PROFILES
}


def get_live_window(slice_id: str, n: int = _LIVE_WINDOW_MAXLEN) -> List[TelemetryPoint]:
    """Most recent `n` live telemetry samples for a slice, oldest->newest.
    Returns fewer (or zero) points if the feed hasn't produced enough yet
    (e.g. right after startup)."""
    window = _LIVE_WINDOWS.get(slice_id)
    if not window:
        return []
    return list(window)[-n:]


def get_live_capacity(slice_id: str) -> float | None:
    for p in DEFAULT_PROFILES:
        if p.slice_id == slice_id:
            return p.capacity_mbps
    return None


# --------------------------------------------------------------------------
# Live telemetry simulator (fallback feed)
# --------------------------------------------------------------------------

_LIVE_FEED_TASK: "asyncio.Task | None" = None


async def live_telemetry_feed_loop(
    tick_seconds: float = 2.0,
    tick_minutes: float = TELEMETRY_SAMPLE_INTERVAL_MINUTES,
) -> None:
    """Broadcasts one telemetry.raw event per configured slice every
    `tick_seconds` real seconds, advancing simulated time by `tick_minutes`
    each tick (so a demo compresses hours of diurnal cycle into minutes of
    wall-clock time). Runs until cancelled (on app shutdown)."""
    rng_by_slice = {p.slice_id: np.random.default_rng(hash(p.slice_id) % (2**31)) for p in DEFAULT_PROFILES}
    spike_state_by_slice = {p.slice_id: LiveSpikeState() for p in DEFAULT_PROFILES}
    sim_time = datetime.now(timezone.utc)

    logger.info("Starting live telemetry simulator (%d slices)", len(DEFAULT_PROFILES))
    try:
        for tick in itertools.count():
            for profile in DEFAULT_PROFILES:
                rng = rng_by_slice[profile.slice_id]
                state = spike_state_by_slice[profile.slice_id]
                throughput, latency, spike_label = next_live_sample(
                    profile, sim_time, state, rng, tick_minutes
                )
                event = TelemetryRawEvent(
                    slice_id=profile.slice_id,
                    timestamp=sim_time,
                    throughput_mbps=round(throughput, 2),
                    latency_ms=round(latency, 2),
                )
                _LIVE_WINDOWS[profile.slice_id].append(
                    TelemetryPoint(
                        timestamp=sim_time,
                        throughput_mbps=round(throughput, 2),
                        latency_ms=round(latency, 2),
                    )
                )
                await broadcast_event(event)
                if spike_label:
                    logger.debug("Slice %s spike active: %s", profile.slice_id, spike_label)

            sim_time = sim_time.fromtimestamp(sim_time.timestamp() + tick_minutes * 60, tz=timezone.utc)
            await asyncio.sleep(tick_seconds)
    except asyncio.CancelledError:
        logger.info("Live telemetry simulator stopped")
        raise


def start_live_feed(loop: asyncio.AbstractEventLoop | None = None) -> None:
    global _LIVE_FEED_TASK
    if _LIVE_FEED_TASK is None or _LIVE_FEED_TASK.done():
        _LIVE_FEED_TASK = asyncio.create_task(live_telemetry_feed_loop())


def stop_live_feed() -> None:
    global _LIVE_FEED_TASK
    if _LIVE_FEED_TASK is not None:
        _LIVE_FEED_TASK.cancel()
        _LIVE_FEED_TASK = None
