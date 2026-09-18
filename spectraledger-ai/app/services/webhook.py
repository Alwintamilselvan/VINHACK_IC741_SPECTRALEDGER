"""
Outbound webhook orchestration: fires a POST to the Java Spring Boot
backend whenever a trade clears, so it can update the ledger/account
balances without polling us.

This is intentionally best-effort and non-blocking to the caller: if
BACKEND_TRADE_WEBHOOK_URL isn't configured yet (the default), or the
backend is down/unreachable, delivery is logged and swallowed rather than
raised -- a missing or flaky Java backend should never break a trade
decision or crash the AI Engine. The event was already broadcast on
/ws/stream and buffered in /events/trade.executed before this is called,
so nothing is lost even if the webhook delivery fails; the backend can
always fall back to polling.
"""
from __future__ import annotations

import logging

import httpx

from app.config import BACKEND_TRADE_WEBHOOK_URL, WEBHOOK_TIMEOUT_SECONDS
from app.schemas.events import TradeExecutedEvent
from app.services.backend_contract import to_java_backend_payload
logger = logging.getLogger("spectraledger.webhook")


async def fire_trade_webhook(event: TradeExecutedEvent) -> None:
    if not BACKEND_TRADE_WEBHOOK_URL:
        logger.debug(
            "BACKEND_TRADE_WEBHOOK_URL not configured -- skipping webhook for trade %s "
            "(event was still broadcast on /ws/stream and buffered in /events/trade.executed)",
            event.trade_id,
        )
        return

    payload = to_java_backend_payload(event)
    logger.info(to_java_backend_payload(event))
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            resp = await client.post(BACKEND_TRADE_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
        logger.info(
            "Webhook delivered for trade %s -> %s (HTTP %s)",
            event.trade_id, BACKEND_TRADE_WEBHOOK_URL, resp.status_code,
        )
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: never let this break a trade
        logger.warning(
            "Webhook delivery FAILED for trade %s -> %s: %s "
            "(backend can still pick this up via /events/trade.executed or /ws/stream)",
            event.trade_id, BACKEND_TRADE_WEBHOOK_URL, exc,
        )
