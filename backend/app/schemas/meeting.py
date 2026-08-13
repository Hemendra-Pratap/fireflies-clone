from datetime import datetime
from math import ceil

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel, TimestampedModel


class MeetingBase(ORMModel):
    title: str = Field(..., min_length=1, max_length=255, description="Title of the meeting")
    source_name: str | None = Field(None, max_length=100, description="Platform or source name (e.g. Zoom, Teams)")
    recorded_at: datetime = Field(..., description="Timestamp when the meeting was recorded")
    duration_ms: int | None = Field(None, ge=0, description="Meeting duration in milliseconds")
    status: str = Field("created", max_length=30, description="Meeting processing status")


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Title of the meeting")
    source_name: str | None = Field(None, max_length=100, description="Platform or source name")
    recorded_at: datetime = Field(..., description="Timestamp when the meeting was recorded")
    duration_ms: int | None = Field(None, ge=0, description="Meeting duration in milliseconds")
    status: str = Field("created", max_length=30, description="Meeting status")


class MeetingUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255, description="Updated title")
    source_name: str | None = Field(None, max_length=100, description="Updated source name")
    recorded_at: datetime | None = Field(None, description="Updated recorded timestamp")
    duration_ms: int | None = Field(None, ge=0, description="Updated duration in milliseconds")
    status: str | None = Field(None, max_length=30, description="Updated status")


class MeetingRead(TimestampedModel):
    id: int
    title: str
    source_name: str | None = None
    recorded_at: datetime
    duration_ms: int | None = None
    status: str
    audio_file_path: str | None = None
    audio_filename: str | None = None
    audio_mime_type: str | None = None
    audio_size_bytes: int | None = None
    error_message: str | None = None
    user_id: int | None = None


class MeetingStatusRead(ORMModel):
    id: int
    status: str
    error_message: str | None = None
    updated_at: datetime


class MeetingDetailRead(MeetingRead):
    participant_count: int = 0
    transcript_segment_count: int = 0
    has_summary: bool = False
    action_item_count: int = 0
    chapter_count: int = 0


class MeetingListResponse(BaseModel):
    items: list[MeetingRead]
    total: int = Field(..., ge=0, description="Total number of matching meeting records")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Number of items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    @classmethod
    def create(cls, items: list[MeetingRead], total: int, page: int, size: int) -> "MeetingListResponse":
        pages = ceil(total / size) if size > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)
