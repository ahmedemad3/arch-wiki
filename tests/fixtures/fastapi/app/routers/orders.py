from fastapi import APIRouter

router = APIRouter(prefix="/api/orders")


@router.get("/")
def list_orders():
    return []


@router.delete("/{order_id}")
def cancel_order(order_id: int):
    return {}
