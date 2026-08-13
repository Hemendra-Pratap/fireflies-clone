from fastapi import APIRouter

from app.api.v1.routes import health, meetings

router = APIRouter()
router.include_router(health.router)
router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])

