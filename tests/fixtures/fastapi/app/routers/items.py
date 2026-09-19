from fastapi import APIRouter, Depends
from app.deps import get_current_user

router = APIRouter()


@router.get("/")
def list_items(user=Depends(get_current_user)):
    return []


@router.get("/{item_id}")
def get_item(item_id: int, user=Depends(get_current_user)):
    return {"id": item_id}


@router.post("/")
def create_item(user=Depends(get_current_user)):
    return {}
