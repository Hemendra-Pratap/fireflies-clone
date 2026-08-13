from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user notifications",
)
def list_notifications(
    workspace_id: int | None = Query(None, description="Optional workspace ID filter"),
    unread_only: bool = Query(False, description="Filter unread notifications only"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    """Fetch paginated notifications for the current authenticated user."""
    try:
        items, total = notification_service.list_notifications(
            db=db,
            user_id=current_user.id,
            workspace_id=workspace_id,
            unread_only=unread_only,
            page=page,
            size=size,
        )
        unread_count = notification_service.get_unread_count(
            db=db,
            user_id=current_user.id,
            workspace_id=workspace_id,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(val_err),
        )

    read_items = [NotificationRead.model_validate(n) for n in items]
    return NotificationListResponse(
        items=read_items,
        total=total,
        unread_count=unread_count,
        page=page,
        size=size,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
)
def get_unread_count(
    workspace_id: int | None = Query(None, description="Optional workspace ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCountResponse:
    """Get total count of unread notifications for current user."""
    try:
        count = notification_service.get_unread_count(
            db=db,
            user_id=current_user.id,
            workspace_id=workspace_id,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(val_err),
        )
    return UnreadCountResponse(unread_count=count)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationRead:
    """Mark a specific notification as read."""
    try:
        notification = notification_service.mark_as_read(
            db=db,
            notification_id=notification_id,
            user_id=current_user.id,
        )
    except KeyError as key_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(key_err),
        )

    return NotificationRead.model_validate(notification)


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
)
def mark_all_notifications_read(
    workspace_id: int | None = Query(None, description="Optional workspace ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all unread notifications for current user as read."""
    try:
        count = notification_service.mark_all_as_read(
            db=db,
            user_id=current_user.id,
            workspace_id=workspace_id,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(val_err),
        )

    return {"marked_count": count, "message": f"Marked {count} notifications as read."}
