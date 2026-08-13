from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CalendarConnectResponse(BaseModel):
    auth_url: str


class CalendarCallbackInput(BaseModel):
    code: str
    state: str


class CalendarConnectionRead(BaseModel):
    id: int
    provider: str
    account_email: str | None = None
    status: str
    last_synced_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalendarStatusResponse(BaseModel):
    connected: bool
    connection: CalendarConnectionRead | None = None


class CalendarEventRead(BaseModel):
    id: int
    calendar_connection_id: int
    workspace_id: int
    user_id: int
    external_event_id: str
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime
    timezone: str | None = "UTC"
    organizer_email: str | None = None
    attendees_json: str | None = None
    meeting_url: str | None = None
    status: str
    meeting_id: int | None = None
    synced_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UpcomingEventsResponse(BaseModel):
    items: list[CalendarEventRead]
    total: int
    page: int
    size: int


class CalendarSyncResponse(BaseModel):
    message: str
    synced_events_count: int
    created_meetings_count: int
