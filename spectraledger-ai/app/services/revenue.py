"""
Platform revenue ledger.

Every trade today is priced strictly slice-to-slice: the buyer pays
exactly what the seller receives, so SpectraLedger itself never captures a
cut. This module fixes that -- it skims a small percentage off each
cleared trade as the platform's own take, and tracks it in an in-memory
ledger.

It's a downstream observer, not a pricing change: nothing here alters how
a trade is priced or matched. Hand it a TradeExecutedEvent right after a
trade clears (see app/routers/agent.py and app/services/autonomous.py,
where each already builds one right before broadcasting it) and it skims
its fee and records it.

Swap the fee percentage via the PLATFORM_FEE_PCT env var -- no code change
needed.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from app.schemas.events import TradeExecutedEvent

# Percentage of each cleared trade's notional value (price * quantity_mbps)
# that SpectraLedger keeps as its own platform fee. 0.02 = 2%.
# Override with e.g. PLATFORM_FEE_PCT=0.015
PLATFORM_FEE_PCT = float(os.environ.get("PLATFORM_FEE_PCT", "0.02"))


@dataclass
class FeeRecord:
    trade_id: str
    buyer_slice_id: str
    seller_slice_id: str
    notional_value: float  # price * quantity_mbps, before the fee is skimmed
    fee_amount: float
    recorded_at: datetime


class RevenueLedger:
    def __init__(self) -> None:
        self._records: List[FeeRecord] = []
        self._lock = threading.Lock()

    def record_trade_fee(self, event: TradeExecutedEvent) -> float:
        """Call this once per cleared trade. Returns the fee amount skimmed
        (in the same USD units /price uses -- see PriceResponse.unit)."""
        notional_value = event.price * event.quantity_mbps
        fee_amount = notional_value * PLATFORM_FEE_PCT

        record = FeeRecord(
            trade_id=event.trade_id,
            buyer_slice_id=event.buyer_slice_id,
            seller_slice_id=event.seller_slice_id,
            notional_value=round(notional_value, 6),
            fee_amount=round(fee_amount, 6),
            recorded_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._records.append(record)
        return fee_amount

    def summary(self) -> dict:
        with self._lock:
            records = list(self._records)

        total_fees = sum(r.fee_amount for r in records)
        total_volume = sum(r.notional_value for r in records)
        return {
            "platform_fee_pct": PLATFORM_FEE_PCT,
            "trade_count": len(records),
            "total_notional_volume": round(total_volume, 6),
            "total_fees_collected": round(total_fees, 6),
            "unit": "USD",
        }

    def recent_records(self, limit: int = 20) -> List[dict]:
        with self._lock:
            records = list(self._records)[-limit:]
        return [
            {
                "trade_id": r.trade_id,
                "buyer_slice_id": r.buyer_slice_id,
                "seller_slice_id": r.seller_slice_id,
                "notional_value": r.notional_value,
                "fee_amount": r.fee_amount,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in records
        ]


# Single shared instance for the process -- imported by the revenue router
# (read-only reporting) and by wherever a trade clears (agent.py,
# autonomous.py) to record the fee.
ledger = RevenueLedger()