from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.calendar import (
    CalendarCallbackInput,
    CalendarConnectResponse,
    CalendarStatusResponse,
    CalendarSyncResponse,
    UpcomingEventsResponse,
    CalendarConnectionRead,
    CalendarEventRead,
)
from app.services.calendar_service import calendar_service
from app.services.google_calendar_provider import google_calendar_provider
from app.services.workspace_service import workspace_service

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get(
    "/connect",
    response_model=CalendarConnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Google OAuth authorization URL with CSRF state protection",
)
def connect_calendar(
    workspace_id: int = Query(..., description="Workspace ID to connect calendar to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarConnectResponse:
    """Generate OAuth auth URL for Google Calendar connection with CSRF state token."""
    if not workspace_service.is_member(db, workspace_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this workspace.",
        )

    state = calendar_service.generate_oauth_state(current_user.id, workspace_id)
    auth_url = google_calendar_provider.get_auth_url(state)
    return CalendarConnectResponse(auth_url=auth_url)


@router.post(
    "/callback",
    status_code=status.HTTP_200_OK,
    summary="Complete OAuth flow and connect calendar",
)
async def calendar_oauth_callback(
    payload: CalendarCallbackInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify CSRF state token, exchange code, and connect calendar."""
    try:
        state_user_id, workspace_id = calendar_service.verify_oauth_state(payload.state)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )

    if state_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OAuth state verification failed: User mismatch.",
        )

    if not workspace_service.is_member(db, workspace_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this workspace.",
        )

    try:
        conn, synced_count, created_meetings = await calendar_service.connect_calendar(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            provider_name="google",
            code=payload.code,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete calendar connection: {exc}",
        )

    return {
        "message": "Google Calendar connected successfully",
        "connection": CalendarConnectionRead.model_validate(conn),
        "synced_events_count": synced_count,
        "created_meetings_count": created_meetings,
    }


@router.get(
    "/status",
    response_model=CalendarStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active calendar connection status for workspace",
)
def get_calendar_status(
    workspace_id: int = Query(..., description="Workspace ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarStatusResponse:
    """Retrieve active calendar connection for workspace."""
    try:
        conn = calendar_service.get_connection(db, workspace_id, current_user.id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(val_err),
        )

    if not conn:
        return CalendarStatusResponse(connected=False, connection=None)

    return CalendarStatusResponse(
        connected=True,
        connection=CalendarConnectionRead.model_validate(conn),
    )


@router.post(
    "/disconnect",
    status_code=status.HTTP_200_OK,
    summary="Disconnect active calendar connection for workspace",
)
async def disconnect_calendar(
    workspace_id: int = Query(..., description="Workspace ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect active calendar connection."""
    try:
        success = await calendar_service.disconnect_calendar(db, workspace_id, current_user.id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(val_err),
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active calendar connection found for this workspace.",
        )

    return {"message": "Calendar connection disconnected successfully."}


@router.post(
    "/sync",
    response_model=CalendarSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually trigger upcoming events synchronization",
)
async def sync_calendar_events(
    workspace_id: int = Query(..., description="Workspace ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarSyncResponse:
    """Trigger synchronization of upcoming calendar events."""
    try:
        conn = calendar_service.get_connection(db, workspace_id, current_user.id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(val_err),
        )

    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active calendar connection found for this workspace.",
        )

    synced_count, created_meetings = await calendar_service.sync_calendar_events(db, conn)
    return CalendarSyncResponse(
        message="Calendar events synchronized successfully.",
        synced_events_count=synced_count,
        created_meetings_count=created_meetings,
    )


@router.get(
    "/upcoming",
    response_model=UpcomingEventsResponse,
    status_code=status.HTTP_200_OK,
    summary="List workspace upcoming scheduled calendar meetings",
)
def list_upcoming_meetings(
    workspace_id: int = Query(..., description="Workspace ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UpcomingEventsResponse:
    """Fetch paginated upcoming calendar meetings for workspace."""
    try:
        events, total = calendar_service.list_upcoming_events(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            page=page,
            size=size,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(val_err),
        )

    items = [CalendarEventRead.model_validate(e) for e in events]
    return UpcomingEventsResponse(items=items, total=total, page=page, size=size)
