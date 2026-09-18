"""
Persistent, in-memory, cross-slice order book.

This is what closes the "central market maker" gap: /agent/evaluate on its
own only matches against whatever order_book snapshot one caller happens to
pass in a single request -- it has no memory between calls. This module
gives the AI Engine actual shared state: any slice's resting bid/ask lives
here until it's matched or cancelled, and the autonomous market-maker loop
(app/services/autonomous.py) reads and writes it every tick across ALL
demo slices, so a seller's listing placed on tick N can be matched against
a buyer's bid that shows up on tick N+3, with nobody needing to hand-carry
an order book snapshot between requests.

In-memory and single-process -- fine for a hackathon demo. A production
version would back this with a real datastore (or hand book ownership to
the Java backend entirely, per the README's architecture note), but the
interface below (`submit` / `cancel` / `all_orders`) wouldn't need to
change for that swap.
"""
from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional

from app.schemas.common import Order, OrderSide, QosPriority


class OrderBook:
    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}
        self._lock = threading.Lock()

    def submit(self, order: Order) -> Order:
        with self._lock:
            self._orders[order.order_id] = order
        return order

    def cancel(self, order_id: str) -> bool:
        with self._lock:
            return self._orders.pop(order_id, None) is not None

    def get(self, order_id: str) -> Optional[Order]:
        with self._lock:
            return self._orders.get(order_id)

    def all_orders(self) -> List[Order]:
        with self._lock:
            return list(self._orders.values())

    def reduce_or_remove(self, order_id: str, filled_qty: float) -> None:
        """Called after a trade clears against a resting order: shrink it
        by the filled quantity, or remove it entirely once fully filled."""
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                return
            remaining = order.quantity_mbps - filled_qty
            if remaining <= 1e-6:
                del self._orders[order_id]
            else:
                self._orders[order_id] = order.model_copy(update={"quantity_mbps": remaining})

    def upsert_slice_quote(
        self,
        slice_id: str,
        side: OrderSide,
        price: float,
        quantity_mbps: float,
        qos_priority: QosPriority,
    ) -> Optional[Order]:
        """Replace a slice's resting order on one side with a fresh quote
        (agents re-evaluate and re-quote every autonomous tick rather than
        stacking up stale orders). Passing quantity_mbps <= 0 just clears
        the slice's resting order on that side without adding a new one."""
        with self._lock:
            stale_ids = [
                oid for oid, o in self._orders.items()
                if o.slice_id == slice_id and o.side == side
            ]
            for oid in stale_ids:
                del self._orders[oid]

            if quantity_mbps <= 0:
                return None

            order_id = f"auto-{slice_id}-{side.value}-{uuid.uuid4().hex[:8]}"
            order = Order(
                order_id=order_id,
                slice_id=slice_id,
                side=side,
                price=price,
                quantity_mbps=quantity_mbps,
                qos_priority=qos_priority,
            )
            self._orders[order_id] = order
            return order


# Single shared instance for the process -- imported by the orderbook
# router (manual submit/cancel) and the autonomous loop (auto-quoting).
book = OrderBook()
