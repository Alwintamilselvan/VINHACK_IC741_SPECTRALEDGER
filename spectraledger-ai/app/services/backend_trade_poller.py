"""
Polls the Java backend for fills on orders the autonomous loop submitted
live (see trade_settlement.py + backend_client.py), since we're no longer
told about them via an inbound webhook once the real backend owns matching
-- GET /api/trades/me was the simpler of the backend team's two supported
options (the other being a /topic/trades WebSocket), chosen to avoid
building separate WS-reconnect handling under the hackathon time budget.

Every tick, for every demo company: fetch any trades /api/trades/me hasn't
reported to us yet, and for each one, broadcast it locally exactly like a
locally-matched trade would be (trade.executed on /ws/stream and
/events/trade.executed, plus the platform-fee estimate in revenue.py) -- so
anything watching the AI engine's own event stream can't tell the
difference between a trade matched locally and one the real backend
cleared.

ASSUMPTION FLAGGED: the exact field names on a trade returned by
GET /api/trades/me weren't specified in the integration note -- only
POST /api/orders' request fields were. _parse_backend_trade() below guesses
in the same naming style as the rest of the spec (camelCase, *SliceId,
*Mbps) with a couple of fallback names hedged in; if a real response doesn't
match, this is the one function to fix.

Only runs at all if JAVA_BACKEND_BASE_URL is configured; a no-op otherwise.

Every trade the backend returns shows up in BOTH companies' /api/trades/me
history (the buyer's and the seller's) -- and the loop below polls every
demo company independently, so the same trade_id would otherwise be "new"
twice in one tick (once from each side) and get double-broadcast and
double-counted in the revenue ledger. _broadcast_trade_ids is the guard
against that, caught by testing before this shipped.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Set

from app.config import JAVA_BACKEND_BASE_URL, JAVA_BACKEND_POLL_SECONDS
from app.schemas.events import TradeExecutedEvent
from app.services import backend_client
from app.services.broadcast import broadcast_event
from app.services.revenue import ledger as revenue_ledger
from app.services.telemetry_generator import DEFAULT_PROFILES

logger = logging.getLogger("spectraledger.backend_poller")

_broadcast_trade_ids: Set[str] = set()
_dedup_lock = threading.Lock()


def _parse_backend_trade(raw: dict) -> Optional[TradeExecutedEvent]:
    """ASSUMPTION FLAGGED -- see module docstring."""
    try:
        trade_id = str(raw.get("tradeId") or raw.get("id"))
        buyer_slice_id = raw.get("buyerSliceId") or raw.get("buyerId")
        seller_slice_id = raw.get("sellerSliceId") or raw.get("sellerId")
        if not (buyer_slice_id and seller_slice_id):
            return None

        quantity_mbps = float(raw.get("quantityMbps") or raw.get("megabitsRented") or 0.0)

        price_per_min = raw.get("pricePerMbpsPerMin")
        if price_per_min is not None:
            price_per_hour = float(price_per_min) * 60.0  # convert back to our internal USD/Mbps-hour convention
        else:
            price_per_hour = float(raw.get("price", 0.0))

        executed_at_raw = raw.get("executedAt") or raw.get("timestamp")
        if isinstance(executed_at_raw, str):
            executed_at = datetime.fromisoformat(executed_at_raw.replace("Z", "+00:00"))
        else:
            executed_at = datetime.now(timezone.utc)

        return TradeExecutedEvent(
            trade_id=trade_id,
            buyer_slice_id=buyer_slice_id,
            seller_slice_id=seller_slice_id,
            price=round(price_per_hour, 6),
            quantity_mbps=quantity_mbps,
            executed_at=executed_at,
        )
    except Exception:
        logger.exception("Could not parse a backend trade payload, skipping it: %s", raw)
        return None


async def _tick() -> None:
    for profile in DEFAULT_PROFILES:
        try:
            raw_trades = await backend_client.fetch_new_trades(
                slice_id=profile.slice_id, capacity_mbps=profile.capacity_mbps
            )
        except Exception:
            logger.exception("Poll failed for %s", profile.slice_id)
            continue

        for raw in raw_trades:
            event = _parse_backend_trade(raw)
            if event is None:
                continue

            with _dedup_lock:
                if event.trade_id in _broadcast_trade_ids:
                    continue  # already handled when the counterparty's poll surfaced this same trade
                _broadcast_trade_ids.add(event.trade_id)

            await broadcast_event(event)
            revenue_ledger.record_trade_fee(event)
            logger.info(
                "LIVE BACKEND TRADE observed: %.0f Mbps @ %.4f USD/Mbps-hr (buyer=%s, seller=%s)",
                event.quantity_mbps, event.price, event.buyer_slice_id, event.seller_slice_id,
            )


async def backend_trade_poll_loop(tick_seconds: float = JAVA_BACKEND_POLL_SECONDS) -> None:
    logger.info("Starting backend trade poller (every %.0fs)", tick_seconds)
    try:
        while True:
            await _tick()
            await asyncio.sleep(tick_seconds)
    except asyncio.CancelledError:
        logger.info("Backend trade poller stopped")
        raise


_TASK: "asyncio.Task | None" = None


def start_backend_poller() -> None:
    global _TASK
    if not JAVA_BACKEND_BASE_URL:
        return
    if _TASK is None or _TASK.done():
        _TASK = asyncio.create_task(backend_trade_poll_loop())


def stop_backend_poller() -> None:
    global _TASK
    if _TASK is not None:
        _TASK.cancel()
        _TASK = None