from fastapi import FastAPI
from app.routers import items, orders

app = FastAPI(title="Acme FastAPI fixture")
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(orders.router)


@app.get("/health")
def health():
    return {"ok": True}
