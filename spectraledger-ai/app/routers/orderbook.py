"""
Manual access to the persistent order book -- useful for the Java backend
or a human tester to submit/cancel an order directly, and to see the live
market state the autonomous loop is trading against. Not required for the
autonomous loop itself (it writes to the same shared `book` directly), but
gives anyone outside the AI Engine a way to participate in or observe the
same market.
"""
from fastapi import APIRouter, HTTPException

from app.schemas.common import Order
from app.services.orderbook import book

router = APIRouter(prefix="/orderbook", tags=["orderbook"])


@router.get("")
async def list_order_book():
    """Every resting order across every slice right now -- both orders the
    autonomous agents placed and any submitted manually via POST below."""
    orders = book.all_orders()
    return {
        "count": len(orders),
        "orders": [o.model_dump(mode="json") for o in orders],
    }


@router.post("/orders", response_model=Order)
async def submit_order(order: Order):
    """Manually place a resting order into the shared book (e.g. from the
    Java backend on behalf of a company, or for testing). The autonomous
    loop's next tick will consider it as a match candidate for any slice's
    seller/buyer decision."""
    return book.submit(order)


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    if not book.cancel(order_id):
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found in the order book.")
    return {"cancelled": order_id}
