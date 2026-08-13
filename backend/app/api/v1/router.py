from fastapi import APIRouter

from app.api.v1.routes import action_items, auth, health, meetings

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
router.include_router(action_items.router, prefix="/action-items", tags=["action-items"])

