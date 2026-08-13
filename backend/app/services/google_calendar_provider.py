from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx

from app.core.config import settings
from app.services.calendar_provider import CalendarEventData, CalendarProvider


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar Provider implementation using OAuth 2.0 and Google Calendar REST API v3."""

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def get_auth_url(self, state: str) -> str:
        """Generate Google OAuth 2.0 authorization URL with CSRF state token."""
        client_id = settings.google_client_id or "mock-google-client-id"
        redirect_uri = settings.google_redirect_uri or "http://localhost:5173/calendar/callback"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access & refresh tokens and user email."""
        client_id = settings.google_client_id
        client_secret = settings.google_client_secret
        redirect_uri = settings.google_redirect_uri or "http://localhost:5173/calendar/callback"

        # If credentials are not configured or code is mock code, return mock tokens for testing/development
        if not client_id or not client_secret or code.startswith("mock_code_"):
            now = datetime.now(timezone.utc)
            return {
                "access_token": f"mock_access_token_{code}",
                "refresh_token": f"mock_refresh_token_{code}",
                "expires_at": now + timedelta(hours=1),
                "account_email": "google_user@example.com",
            }

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise ValueError(f"Failed to exchange Google OAuth code: {token_resp.text}")

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Fetch user email
            user_resp = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            email = user_resp.json().get("email") if user_resp.status_code == 200 else None

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "account_email": email,
            }

    async def list_upcoming_events(
        self,
        connection: any,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[CalendarEventData]:
        """Fetch upcoming events from Google Calendar API."""
        now = datetime.now(timezone.utc)
        if start_time is None:
            start_time = now - timedelta(hours=1)
        if end_time is None:
            end_time = now + timedelta(days=14)

        access_token = getattr(connection, "access_token", None)

        # If access token is a mock token or empty, return synthetic mock upcoming events for test environments
        if not access_token or access_token.startswith("mock_"):
            return self._generate_mock_events(start_time, end_time)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.EVENTS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin": start_time.isoformat(),
                    "timeMax": end_time.isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                },
            )
            if resp.status_code != 200:
                return []

            items = resp.json().get("items", [])
            events: list[CalendarEventData] = []
            for item in items:
                event_data = self._parse_google_event(item)
                if event_data:
                    events.append(event_data)
            return events

    async def disconnect(self, connection: any) -> None:
        """Revoke Google OAuth tokens."""
        access_token = getattr(connection, "access_token", None)
        if not access_token or access_token.startswith("mock_"):
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.post(self.REVOKE_URL, params={"token": access_token})
        except Exception:
            pass

    def _parse_google_event(self, item: dict) -> CalendarEventData | None:
        """Parse raw Google Calendar API JSON item into CalendarEventData."""
        event_id = item.get("id")
        if not event_id:
            return None

        title = item.get("summary") or "Untitled Meeting"
        description = item.get("description")
        status_raw = item.get("status", "confirmed")
        status = "cancelled" if status_raw == "cancelled" else "confirmed"

        # Parse start and end times
        start_dict = item.get("start", {})
        end_dict = item.get("end", {})
        start_str = start_dict.get("dateTime") or start_dict.get("date")
        end_str = end_dict.get("dateTime") or end_dict.get("date")

        if not start_str or not end_str:
            return None

        try:
            start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except ValueError:
            return None

        tz = start_dict.get("timeZone") or "UTC"
        organizer = item.get("organizer", {}).get("email")

        # Parse attendees
        attendees_raw = item.get("attendees", [])
        attendees = [
            {"email": a.get("email"), "name": a.get("displayName") or a.get("email")}
            for a in attendees_raw
            if a.get("email")
        ]

        # Extract meeting URL
        meeting_url = item.get("hangoutLink")
        if not meeting_url:
            entry_points = item.get("conferenceData", {}).get("entryPoints", [])
            for ep in entry_points:
                if ep.get("uri"):
                    meeting_url = ep.get("uri")
                    break

        return CalendarEventData(
            external_event_id=event_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            timezone=tz,
            organizer_email=organizer,
            attendees=attendees,
            meeting_url=meeting_url,
            status=status,
        )

    def _generate_mock_events(self, start_time: datetime, end_time: datetime) -> list[CalendarEventData]:
        """Generate clean synthetic mock events for local development / testing."""
        now = datetime.now(timezone.utc)
        return [
            CalendarEventData(
                external_event_id="mock_evt_001",
                title="Product Sync & Architecture Review",
                description="Weekly sync on architecture, calendar integration, and AI meeting intelligence.",
                start_time=now + timedelta(hours=2),
                end_time=now + timedelta(hours=3),
                timezone="UTC",
                organizer_email="alex.lead@company.com",
                attendees=[
                    {"email": "alex.lead@company.com", "name": "Alex Lead"},
                    {"email": "dev.user@company.com", "name": "Dev User"},
                ],
                meeting_url="https://meet.google.com/abc-defg-hij",
                status="confirmed",
            ),
            CalendarEventData(
                external_event_id="mock_evt_002",
                title="Client Q3 Planning & Roadmap Session",
                description="Discussion with client stakeholders on feature deliverables.",
                start_time=now + timedelta(days=1, hours=4),
                end_time=now + timedelta(days=1, hours=5),
                timezone="UTC",
                organizer_email="sarah.pm@company.com",
                attendees=[
                    {"email": "sarah.pm@company.com", "name": "Sarah PM"},
                    {"email": "client.boss@client.org", "name": "Client Boss"},
                ],
                meeting_url="https://zoom.us/j/9876543210",
                status="confirmed",
            ),
        ]


google_calendar_provider = GoogleCalendarProvider()
