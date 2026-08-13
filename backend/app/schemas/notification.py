from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: int
    user_id: int
    workspace_id: int | None = None
    type: str
    title: str
    message: str
    meeting_id: int | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationRead]
    total: int
    unread_count: int
    page: int
    size: int


class UnreadCountResponse(BaseModel):
    unread_count: int
