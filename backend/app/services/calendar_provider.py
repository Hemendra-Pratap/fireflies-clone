from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CalendarEventData:
    external_event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    description: str | None = None
    timezone: str | None = "UTC"
    organizer_email: str | None = None
    attendees: list[dict[str, str]] = field(default_factory=list)  # e.g. [{"email": "user@example.com", "name": "User"}]
    meeting_url: str | None = None
    status: str = "confirmed"  # "confirmed", "cancelled", "tentative"


class CalendarProvider(ABC):
    """Abstract Base Class for Calendar Providers (Google Calendar, Outlook, etc.)."""

    @abstractmethod
    def get_auth_url(self, state: str) -> str:
        """Generate the OAuth authorization URL with CSRF state token."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> dict:
        """Exchange OAuth authorization code for tokens and user profile info.
        
        Returns dict with keys:
            - access_token: str
            - refresh_token: str | None
            - expires_at: datetime | None
            - account_email: str | None
        """
        pass

    @abstractmethod
    async def list_upcoming_events(
        self,
        connection: any,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[CalendarEventData]:
        """Fetch upcoming calendar events for the connection."""
        pass

    @abstractmethod
    async def disconnect(self, connection: any) -> None:
        """Disconnect/revoke calendar authorization."""
        pass
