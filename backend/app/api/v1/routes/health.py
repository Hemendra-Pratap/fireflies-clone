import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse, summary="Liveness probe")
def liveness() -> HealthResponse:
    """Liveness probe indicating application process is running."""
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
    )


@router.get("/ready", summary="Readiness probe")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe verifying backend can reach database."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        logger.error(f"Database readiness probe failed: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "disconnected"},
        )
