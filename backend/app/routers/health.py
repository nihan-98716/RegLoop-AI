"""Health check router."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger

log = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Return backend status and database connectivity."""
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        log.error("health.db_error", error=str(exc))
        db_status = "error"

    log.info("health.checked", database=db_status)
    return {"status": "ok", "database": db_status}
