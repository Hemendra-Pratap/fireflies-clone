from fastapi import APIRouter

from app.api.v1.routes import action_items, auth, calendar, health, meetings, notifications, search, workspaces

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
router.include_router(action_items.router, prefix="/action-items", tags=["action-items"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(calendar.router)
router.include_router(notifications.router)


