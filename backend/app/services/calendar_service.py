import json
from datetime import datetime, timezone
import hmac
import hashlib
import time

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.core.config import settings
from app.models.calendar_connection import CalendarConnection, CalendarConnectionStatus, CalendarProviderType
from app.models.calendar_event import CalendarEvent, CalendarEventStatus
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import Participant
from app.services.google_calendar_provider import google_calendar_provider
from app.services.workspace_service import workspace_service


class CalendarService:
    """Service handling calendar connections, state protection, event synchronization, and meeting ingestion."""

    def generate_oauth_state(self, user_id: int, workspace_id: int) -> str:
        """Generate a secure, signed state string to prevent CSRF during OAuth flow."""
        timestamp = int(time.time())
        raw_payload = f"{user_id}:{workspace_id}:{timestamp}"
        signature = hmac.new(
            settings.jwt_secret_key.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{raw_payload}:{signature}"

    def verify_oauth_state(self, state: str) -> tuple[int, int]:
        """Verify CSRF OAuth state parameter signature and return (user_id, workspace_id)."""
        parts = state.split(":")
        if len(parts) != 4:
            raise ValueError("Invalid OAuth state parameter format.")

        user_id_str, workspace_id_str, timestamp_str, signature = parts
        try:
            user_id = int(user_id_str)
            workspace_id = int(workspace_id_str)
            timestamp = int(timestamp_str)
        except ValueError:
            raise ValueError("Malformed OAuth state parameter.")

        # Check timestamp expiry (allow 15 minutes for OAuth flow completion)
        if time.time() - timestamp > 900:
            raise ValueError("OAuth state token has expired. Please try connecting again.")

        raw_payload = f"{user_id}:{workspace_id}:{timestamp}"
        expected_sig = hmac.new(
            settings.jwt_secret_key.encode("utf-8"),
            raw_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("OAuth state parameter signature verification failed (possible CSRF attempt).")

        return user_id, workspace_id

    def get_connection(self, db: Session, workspace_id: int, user_id: int) -> CalendarConnection | None:
        """Retrieve active calendar connection for a workspace and user."""
        if not workspace_service.is_member(db, workspace_id, user_id):
            raise ValueError("Access denied: You are not a member of this workspace.")

        stmt = select(CalendarConnection).where(
            CalendarConnection.workspace_id == workspace_id,
            CalendarConnection.status == CalendarConnectionStatus.ACTIVE,
        )
        return db.scalar(stmt)

    async def connect_calendar(
        self,
        db: Session,
        workspace_id: int,
        user_id: int,
        provider_name: str,
        code: str,
    ) -> tuple[CalendarConnection, int, int]:
        """Exchange OAuth code, create/update CalendarConnection, and sync upcoming events."""
        if not workspace_service.is_member(db, workspace_id, user_id):
            raise ValueError("Access denied: You are not a member of this workspace.")

        provider = self._get_provider(provider_name)
        token_payload = await provider.exchange_code(code)

        account_email = token_payload.get("account_email") or f"user_{user_id}@calendar.com"

        # Check if existing connection exists
        stmt = select(CalendarConnection).where(
            CalendarConnection.workspace_id == workspace_id,
            CalendarConnection.provider == provider_name,
            CalendarConnection.account_email == account_email,
        )
        conn = db.scalar(stmt)

        now = datetime.now(timezone.utc)
        if not conn:
            conn = CalendarConnection(
                user_id=user_id,
                workspace_id=workspace_id,
                provider=provider_name,
                account_email=account_email,
                access_token=token_payload.get("access_token"),
                refresh_token=token_payload.get("refresh_token"),
                expires_at=token_payload.get("expires_at"),
                status=CalendarConnectionStatus.ACTIVE,
                last_synced_at=now,
            )
            db.add(conn)
        else:
            conn.user_id = user_id
            conn.access_token = token_payload.get("access_token")
            if token_payload.get("refresh_token"):
                conn.refresh_token = token_payload.get("refresh_token")
            conn.expires_at = token_payload.get("expires_at")
            conn.status = CalendarConnectionStatus.ACTIVE
            conn.last_synced_at = now

        db.commit()
        db.refresh(conn)

        # Trigger event sync
        synced_count, created_meetings = await self.sync_calendar_events(db, conn)
        return conn, synced_count, created_meetings

    async def disconnect_calendar(self, db: Session, workspace_id: int, user_id: int) -> bool:
        """Disconnect active calendar connection for workspace."""
        conn = self.get_connection(db, workspace_id, user_id)
        if not conn:
            return False

        provider = self._get_provider(conn.provider)
        await provider.disconnect(conn)

        conn.status = CalendarConnectionStatus.DISCONNECTED
        conn.access_token = None
        conn.refresh_token = None
        db.commit()
        return True

    async def sync_calendar_events(
        self,
        db: Session,
        connection: CalendarConnection,
    ) -> tuple[int, int]:
        """Synchronize calendar events and create corresponding local Meeting metadata records idempotently."""
        provider = self._get_provider(connection.provider)
        events_data = await provider.list_upcoming_events(connection)

        synced_count = 0
        created_meetings_count = 0
        now = datetime.now(timezone.utc)

        for data in events_data:
            # Query existing CalendarEvent record
            stmt = select(CalendarEvent).where(
                CalendarEvent.calendar_connection_id == connection.id,
                CalendarEvent.external_event_id == data.external_event_id,
            )
            event_rec = db.scalar(stmt)

            attendees_json = json.dumps(data.attendees) if data.attendees else None

            if not event_rec:
                event_rec = CalendarEvent(
                    calendar_connection_id=connection.id,
                    workspace_id=connection.workspace_id,
                    user_id=connection.user_id,
                    external_event_id=data.external_event_id,
                    title=data.title,
                    description=data.description,
                    start_time=data.start_time,
                    end_time=data.end_time,
                    timezone=data.timezone or "UTC",
                    organizer_email=data.organizer_email,
                    attendees_json=attendees_json,
                    meeting_url=data.meeting_url,
                    status=data.status,
                    synced_at=now,
                )
                db.add(event_rec)
                db.flush()
            else:
                event_rec.title = data.title
                event_rec.description = data.description
                event_rec.start_time = data.start_time
                event_rec.end_time = data.end_time
                event_rec.timezone = data.timezone or "UTC"
                event_rec.organizer_email = data.organizer_email
                event_rec.attendees_json = attendees_json
                event_rec.meeting_url = data.meeting_url
                event_rec.status = data.status
                event_rec.synced_at = now

            synced_count += 1

            # Phase 5 — Meeting Ingestion Foundation:
            # Create or update linked local Meeting metadata record if event is confirmed and has no meeting_id
            if data.status != CalendarEventStatus.CANCELLED and not event_rec.meeting_id:
                # Check if a meeting with same title and start time already exists in workspace to avoid duplicates
                existing_meeting_stmt = select(Meeting).where(
                    Meeting.workspace_id == connection.workspace_id,
                    Meeting.title == data.title,
                    Meeting.recorded_at == data.start_time,
                )
                existing_meeting = db.scalar(existing_meeting_stmt)

                if not existing_meeting:
                    duration_ms = (
                        int((data.end_time - data.start_time).total_seconds() * 1000)
                        if data.start_time and data.end_time
                        else None
                    )
                    source_provider = "Google Calendar" if connection.provider == "google" else connection.provider
                    meeting = Meeting(
                        title=data.title,
                        source_name=f"{source_provider} ({connection.account_email or 'Calendar'})",
                        recorded_at=data.start_time,
                        duration_ms=duration_ms,
                        status=MeetingStatus.CREATED,
                        audio_file_path=None,  # Audio remains None until explicitly uploaded
                        user_id=connection.user_id,
                        workspace_id=connection.workspace_id,
                    )
                    db.add(meeting)
                    db.flush()

                    # Ingest participants/attendees into Participant model
                    if data.organizer_email:
                        p_org = Participant(
                            meeting_id=meeting.id,
                            speaker_label="Organizer",
                            display_name=data.organizer_email.split("@")[0],
                            email=data.organizer_email,
                        )
                        db.add(p_org)

                    if data.attendees:
                        for idx, att in enumerate(data.attendees, start=1):
                            if att.get("email") and att.get("email") != data.organizer_email:
                                p_att = Participant(
                                    meeting_id=meeting.id,
                                    speaker_label=f"Attendee {idx}",
                                    display_name=att.get("name") or att.get("email", "").split("@")[0],
                                    email=att.get("email"),
                                )
                                db.add(p_att)

                    event_rec.meeting_id = meeting.id
                    created_meetings_count += 1
                else:
                    event_rec.meeting_id = existing_meeting.id

            # Trigger idempotent upcoming meeting notification if event is in future and confirmed
            if data.status != CalendarEventStatus.CANCELLED and data.start_time > now:
                from app.models.notification import NotificationType
                from app.services.notification_service import notification_service

                time_str = data.start_time.strftime("%b %d at %H:%M UTC")
                notification_service.create_notification(
                    db=db,
                    user_id=connection.user_id,
                    notification_type=NotificationType.UPCOMING_MEETING,
                    title="Upcoming Scheduled Meeting",
                    message=f"Meeting '{data.title}' is scheduled for {time_str}.",
                    workspace_id=connection.workspace_id,
                    meeting_id=event_rec.meeting_id,
                )

        connection.last_synced_at = now
        db.commit()
        return synced_count, created_meetings_count

    def list_upcoming_events(
        self,
        db: Session,
        workspace_id: int,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[CalendarEvent], int]:
        """Fetch workspace-scoped upcoming calendar events (start_time >= now, not cancelled)."""
        if not workspace_service.is_member(db, workspace_id, user_id):
            raise ValueError("Access denied: You are not a member of this workspace.")

        now = datetime.now(timezone.utc)
        base_query = select(CalendarEvent).where(
            CalendarEvent.workspace_id == workspace_id,
            CalendarEvent.end_time >= now,
            CalendarEvent.status != CalendarEventStatus.CANCELLED,
        )

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = db.scalar(count_stmt) or 0

        # Paginate and order by start_time ASC
        offset = (page - 1) * size
        query = base_query.order_by(CalendarEvent.start_time.asc()).offset(offset).limit(size)
        events = list(db.scalars(query).all())

        return events, total

    def _get_provider(self, provider_name: str):
        if provider_name.lower() == "google":
            return google_calendar_provider
        raise ValueError(f"Unsupported calendar provider '{provider_name}'.")


calendar_service = CalendarService()
