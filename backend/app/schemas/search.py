from datetime import datetime
from math import ceil
from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    meeting_id: int = Field(..., description="ID of the matching meeting")
    meeting_title: str = Field(..., description="Title of the meeting")
    meeting_status: str = Field(..., description="Status of the meeting")
    recorded_at: datetime = Field(..., description="Timestamp when meeting recorded")
    match_type: str = Field(..., description="Matching component type: title, summary, action_item, chapter, transcript, participant")
    matched_text: str = Field(..., description="Snippet of text containing the search term match")
    timestamp_ms: int | None = Field(None, description="Audio offset timestamp in ms if applicable")
    relevance: float = Field(1.0, description="Relevance score")


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int = Field(..., ge=0, description="Total matching search items")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total pages")

    @classmethod
    def create(cls, items: list[SearchResultItem], total: int, page: int, size: int) -> "SearchResponse":
        pages = ceil(total / size) if size > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)
