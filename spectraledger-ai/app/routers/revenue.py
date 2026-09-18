"""
Read-only reporting on the platform revenue ledger (app/services/revenue.py).

Nothing here records a fee -- that happens at the two points a trade
actually clears (app/routers/agent.py and app/services/autonomous.py, each
calling `revenue.ledger.record_trade_fee(...)` right after building its
trade_event). This router just lets you see the running total, e.g. for a
judge asking "so where's SpectraLedger's own cut."
"""
from fastapi import APIRouter

from app.services.revenue import ledger

router = APIRouter(prefix="/revenue", tags=["revenue"])


@router.get("")
async def revenue_summary():
    """Running totals: platform fee %, trade count, total notional volume
    traded, and total fees collected so far this session."""
    return ledger.summary()


@router.get("/trades")
async def revenue_trades(limit: int = 20):
    """The most recent individual fee records, one per cleared trade."""
    return {"records": ledger.recent_records(limit)}