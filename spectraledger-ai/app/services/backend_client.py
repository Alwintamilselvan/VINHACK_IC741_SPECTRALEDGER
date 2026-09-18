"""
Live integration client for the Java Spring Boot backend's real, already-
built order-book API. This is what the autonomous loop's decisions settle
against when JAVA_BACKEND_BASE_URL is configured, instead of the AI engine's
own in-memory order book (app/services/orderbook.py). When it isn't
configured, or any call here fails for any reason, callers fall back to the
original local-only path untouched -- see app/services/trade_settlement.py
for exactly where that fallback happens. Nothing in this file ever raises
out to a caller; every public function returns None / [] on failure and logs
what went wrong.

Five endpoints used, nothing else, per the backend team's integration note:

    POST /api/auth/register      - once per simulated company, creates its
                                    Tenant + first NetworkSlice. Returns a
                                    JWT + tenantId.
    GET  /api/accounts/me/slices - fetch that company's real sliceId right
                                    after registering/logging in (register's
                                    response doesn't include it directly).
    POST /api/auth/login         - refresh a JWT for a company that already
                                    exists (tokens last ~12h).
    POST /api/orders             - submit an order; {sliceId, side,
                                    quantityMbps, pricePerMbpsPerMin,
                                    durationMinutes, qosTier} + Authorization
                                    header. The backend's own matching engine
                                    clears it against resting counter-orders
                                    -- we do NOT match locally once this
                                    succeeds.
    GET  /api/trades/me          - poll for this company's fills, so the AI
                                    engine can broadcast trade.executed
                                    locally (see backend_trade_poller.py)
                                    without needing an inbound webhook.

============================================================================
ASSUMPTIONS FLAGGED -- confirm these against the real backend before a demo
run, ideally from its /swagger-ui.html or /v3/api-docs, or by asking whoever
built it. Everything else in this file is exact per the integration note;
these are the only guessed shapes, and each is isolated to one small spot:

  1. _register_payload() / _login_payload() -- the exact JSON body fields
     for POST /api/auth/register and /api/auth/login weren't specified
     (only the response: "a JWT and tenantId"). Guessed as
     {companyName/email/password[/capacityMbps/qosTier]} below.
  2. The HTTP status /api/auth/register returns for "this company already
     exists" (guessed as 409) -- ensure_session() falls back to /login on
     ANY non-2xx from /register as a safety net, so this matters less than
     it looks like it does, but a 409 is assumed for the log message.
  3. The JWT field name in the auth response -- hedged by trying "token",
     "jwt", and "accessToken" in that order.
  4. The sliceId field name in GET /api/accounts/me/slices -- hedged by
     trying "sliceId" (matches POST /api/orders' own field name) then "id".
============================================================================
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

from app.config import (
    JAVA_BACKEND_BASE_URL,
    JAVA_BACKEND_DEMO_PASSWORD,
    JAVA_BACKEND_TIMEOUT_SECONDS,
)

logger = logging.getLogger("spectraledger.backend_client")

_TOKEN_LIFETIME_SECONDS = 11 * 3600  # refresh a bit before the real ~12h expiry


@dataclass
class CompanySession:
    slice_id: str  # our synthetic slice_id, e.g. "slice-embb-02" -- used as this company's login identity
    jwt: Optional[str] = None
    tenant_id: Optional[str] = None
    backend_slice_id: Optional[str] = None
    token_issued_at: float = 0.0
    last_seen_trade_id: Optional[str] = None
    last_seen_trade_id_initialized: bool = False


_sessions: Dict[str, CompanySession] = {}
_lock = threading.Lock()


def backend_enabled() -> bool:
    return bool(JAVA_BACKEND_BASE_URL)


def _email_for(slice_id: str) -> str:
    # Deterministic synthetic email per demo company -- not a real inbox.
    return f"{slice_id.replace('_', '-')}@spectraledger.demo"


def _register_payload(slice_id: str, capacity_mbps: float) -> dict:
    """ASSUMPTION #1 -- see module docstring."""
    return {
        "companyName": slice_id,
        "email": _email_for(slice_id),
        "password": JAVA_BACKEND_DEMO_PASSWORD,
        "capacityMbps": capacity_mbps,
        "qosTier": "SILVER",
    }


def _login_payload(slice_id: str) -> dict:
    """ASSUMPTION #1 -- see module docstring."""
    return {
        "email": _email_for(slice_id),
        "password": JAVA_BACKEND_DEMO_PASSWORD,
    }


def _extract_jwt(body: dict) -> Optional[str]:
    """ASSUMPTION #3 -- see module docstring."""
    return body.get("token") or body.get("jwt") or body.get("accessToken")


async def _fetch_backend_slice_id(client: httpx.AsyncClient, jwt: str) -> Optional[str]:
    """ASSUMPTION #4 -- see module docstring."""
    resp = await client.get(
        f"{JAVA_BACKEND_BASE_URL}/api/accounts/me/slices",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    resp.raise_for_status()
    slices = resp.json()
    if not slices:
        return None
    first = slices[0]
    return first.get("sliceId") or first.get("id")


async def ensure_session(slice_id: str, capacity_mbps: float) -> Optional[CompanySession]:
    """Returns a valid, logged-in CompanySession for this demo company,
    registering it on first contact with a fresh backend and logging back in
    on later runs or once the token is due to expire. Returns None (never
    raises) if the backend can't be reached at all -- callers treat that as
    'fall back to local mode for this tick.'"""
    with _lock:
        session = _sessions.get(slice_id)
    if session and session.jwt and (time.time() - session.token_issued_at) < _TOKEN_LIFETIME_SECONDS:
        return session

    try:
        async with httpx.AsyncClient(timeout=JAVA_BACKEND_TIMEOUT_SECONDS) as client:
            body: dict = {}
            if session is None:
                # First contact ever for this company this process -- try to
                # register; fall back to login if it's already registered
                # from a previous run (any non-2xx is treated as "exists").
                resp = await client.post(
                    f"{JAVA_BACKEND_BASE_URL}/api/auth/register",
                    json=_register_payload(slice_id, capacity_mbps),
                )
                if resp.status_code >= 300:
                    logger.info(
                        "Register for %s returned HTTP %s -- assuming it already exists, logging in instead",
                        slice_id, resp.status_code,
                    )
                    resp = await client.post(
                        f"{JAVA_BACKEND_BASE_URL}/api/auth/login",
                        json=_login_payload(slice_id),
                    )
                resp.raise_for_status()
                body = resp.json()
            else:
                # Existing session, token just expired -- log back in.
                resp = await client.post(
                    f"{JAVA_BACKEND_BASE_URL}/api/auth/login",
                    json=_login_payload(slice_id),
                )
                resp.raise_for_status()
                body = resp.json()

            jwt = _extract_jwt(body)
            tenant_id = body.get("tenantId") or (session.tenant_id if session else None)

            if not jwt:
                logger.warning("Backend auth for %s returned no recognizable token field: %s", slice_id, body)
                return None

            backend_slice_id = await _fetch_backend_slice_id(client, jwt)

        new_session = CompanySession(
            slice_id=slice_id,
            jwt=jwt,
            tenant_id=tenant_id,
            backend_slice_id=backend_slice_id,
            token_issued_at=time.time(),
            last_seen_trade_id=session.last_seen_trade_id if session else None,
            last_seen_trade_id_initialized=session.last_seen_trade_id_initialized if session else False,
        )
        with _lock:
            _sessions[slice_id] = new_session
        logger.info(
            "Backend session ready for %s (tenantId=%s, backendSliceId=%s)",
            slice_id, tenant_id, backend_slice_id,
        )
        return new_session
    except Exception:
        logger.exception(
            "Could not establish a backend session for %s -- falling back to local mode this tick", slice_id
        )
        return None


async def submit_order(
    slice_id: str,
    capacity_mbps: float,
    side: str,  # "bid" or "ask"
    quantity_mbps: float,
    price_per_mbps_per_min: float,
    duration_minutes: int,
    qos_tier: str,
) -> Optional[dict]:
    """POSTs a real order to the backend's order book. Returns the parsed
    response body on success, or None (never raises) on any failure --
    callers fall back to local matching for this tick when this returns
    None."""
    session = await ensure_session(slice_id, capacity_mbps)
    if session is None or session.backend_slice_id is None:
        return None

    payload = {
        "sliceId": session.backend_slice_id,
        "side": side,
        "quantityMbps": quantity_mbps,
        "pricePerMbpsPerMin": round(price_per_mbps_per_min, 6),
        "durationMinutes": duration_minutes,
        "qosTier": qos_tier,
    }
    try:
        async with httpx.AsyncClient(timeout=JAVA_BACKEND_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{JAVA_BACKEND_BASE_URL}/api/orders",
                json=payload,
                headers={"Authorization": f"Bearer {session.jwt}"},
            )
            resp.raise_for_status()
        logger.info(
            "Order submitted to backend for %s: %.0f Mbps @ %.6f USD/Mbps/min (%s)",
            slice_id, quantity_mbps, price_per_mbps_per_min, side,
        )
        return resp.json()
    except Exception:
        logger.exception("Order submission FAILED for %s -- falling back to local book this tick", slice_id)
        return None


async def fetch_new_trades(slice_id: str, capacity_mbps: float) -> List[dict]:
    """Polls GET /api/trades/me for this company and returns any trades not
    already seen (tracked per-session), oldest-first. Assumes the endpoint
    returns newest-first, the common REST convention -- flagged since it
    wasn't specified. Returns [] on any failure or on the very first poll
    for a company (so we start tracking from 'now' instead of replaying a
    backend's entire pre-existing trade history as if it just happened)."""
    session = await ensure_session(slice_id, capacity_mbps)
    if session is None:
        return []

    try:
        async with httpx.AsyncClient(timeout=JAVA_BACKEND_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                f"{JAVA_BACKEND_BASE_URL}/api/trades/me",
                headers={"Authorization": f"Bearer {session.jwt}"},
            )
            resp.raise_for_status()
            trades = resp.json()
    except Exception:
        logger.exception("Polling /api/trades/me FAILED for %s", slice_id)
        return []

    if not isinstance(trades, list) or not trades:
        with _lock:
            session.last_seen_trade_id_initialized = True
        return []

    def _trade_id(t: dict) -> str:
        return str(t.get("tradeId") or t.get("id") or "")

    if not session.last_seen_trade_id_initialized:
        # First poll ever for this company -- don't replay pre-existing
        # history as brand-new trades, just start tracking from here.
        with _lock:
            session.last_seen_trade_id = _trade_id(trades[0])
            session.last_seen_trade_id_initialized = True
        return []

    last_seen = session.last_seen_trade_id
    seen_index = next((i for i, t in enumerate(trades) if _trade_id(t) == last_seen), None)
    new_trades = trades[:seen_index] if seen_index is not None else trades

    if new_trades:
        with _lock:
            session.last_seen_trade_id = _trade_id(trades[0])

    return list(reversed(new_trades))  # oldest-first for orderly broadcasting