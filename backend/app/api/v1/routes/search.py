from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchResponse
from app.services.search_service import search_service

router = APIRouter()


@router.get(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search meetings across text data",
)
def search_meetings(
    q: str = Query("", description="Search term query string"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(None, alias="status", description="Optional status filter"),
    workspace_id: int | None = Query(None, description="Optional target workspace ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    """Multi-entity text search across meetings, transcripts, summaries, action items, chapters, and participants."""
    return search_service.search(
        db,
        user_id=current_user.id,
        query_str=q,
        page=page,
        size=size,
        status=status_filter,
        workspace_id=workspace_id,
    )
