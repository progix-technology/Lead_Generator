from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.connection import get_database
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory error store (persists across requests, resets on server restart)
_error_store: list[dict] = []
MAX_ERRORS = 50


def push_notification(level: str, message: str, source: str = "system"):
    """
    Call this from anywhere in the backend to push a notification.
    level: 'error' | 'warning' | 'info'
    """
    _error_store.insert(0, {
        "id": len(_error_store) + 1,
        "level": level,
        "message": message,
        "source": source,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "read": False
    })
    # Keep store capped
    if len(_error_store) > MAX_ERRORS:
        _error_store.pop()


@router.get("/")
async def get_notifications():
    """Get all notifications (unread first)."""
    unread_count = sum(1 for n in _error_store if not n.get("read"))
    return {
        "notifications": _error_store[:30],
        "unread_count": unread_count,
        "total": len(_error_store)
    }


@router.post("/read-all")
async def mark_all_read():
    """Mark all notifications as read."""
    for n in _error_store:
        n["read"] = True
    return {"status": "ok"}


@router.delete("/clear")
async def clear_notifications():
    """Clear all notifications."""
    _error_store.clear()
    return {"status": "cleared"}
