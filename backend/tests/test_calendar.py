from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.calendar_connection import CalendarConnection, CalendarConnectionStatus
from app.models.calendar_event import CalendarEvent, CalendarEventStatus
from app.models.meeting import Meeting, MeetingStatus
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.services.calendar_provider import CalendarEventData
from app.services.calendar_service import calendar_service
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service


@pytest.fixture
def anyio_backend():
    return "asyncio"


def setup_test_users_and_workspaces(db_session: Session):
    user1 = auth_service.register_user(db_session, "cal_user1@example.com", "password123")
    user2 = auth_service.register_user(db_session, "cal_user2@example.com", "password123")

    ws1 = workspace_service.get_or_create_default_workspace(db_session, user1)
    ws2 = workspace_service.get_or_create_default_workspace(db_session, user2)

    token1, _ = create_access_token(str(user1.id))
    token2, _ = create_access_token(str(user2.id))

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    return user1, user2, ws1, ws2, headers1, headers2


def test_calendar_connect_authorization(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_test_users_and_workspaces(db_session)

    # User 1 requests auth URL for User 1's workspace -> Success
    res1 = unauth_client.get(f"/api/v1/calendar/connect?workspace_id={ws1.id}", headers=h1)
    assert res1.status_code == 200
    assert "auth_url" in res1.json()
    assert "state=" in res1.json()["auth_url"]

    # User 2 attempts to connect calendar to User 1's workspace -> 403 Forbidden
    res2 = unauth_client.get(f"/api/v1/calendar/connect?workspace_id={ws1.id}", headers=h2)
    assert res2.status_code == 403
    assert "Access denied" in res2.json()["detail"]


def test_calendar_oauth_state_validation(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_test_users_and_workspaces(db_session)

    # Valid state generated for user 1
    valid_state = calendar_service.generate_oauth_state(u1.id, ws1.id)

    # Attempt callback with invalid state token (forged signature)
    import time
    bad_state = f"1:1:{int(time.time())}:invalid_forged_signature"
    res_bad = unauth_client.post(
        "/api/v1/calendar/callback",
        json={"code": "mock_code_123", "state": bad_state},
        headers=h1,
    )
    assert res_bad.status_code == 400
    assert "verification failed" in res_bad.json()["detail"].lower()

    # User 2 attempts to use User 1's valid state -> User mismatch 403
    res_mismatch = unauth_client.post(
        "/api/v1/calendar/callback",
        json={"code": "mock_code_123", "state": valid_state},
        headers=h2,
    )
    assert res_mismatch.status_code == 403
    assert "User mismatch" in res_mismatch.json()["detail"]


@pytest.mark.anyio
async def test_calendar_event_sync_and_meeting_creation(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_test_users_and_workspaces(db_session)
    valid_state = calendar_service.generate_oauth_state(u1.id, ws1.id)

    now = datetime.now(timezone.utc)
    mock_events = [
        CalendarEventData(
            external_event_id="evt_1001",
            title="Q3 Strategy Meeting",
            description="Discuss quarterly OKRs",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            timezone="UTC",
            organizer_email="cal_user1@example.com",
            attendees=[{"email": "cal_user1@example.com", "name": "User 1"}],
            meeting_url="https://meet.google.com/q3-strategy",
            status="confirmed",
        )
    ]

    with patch(
        "app.services.google_calendar_provider.GoogleCalendarProvider.list_upcoming_events",
        new_callable=AsyncMock,
        return_value=mock_events,
    ):
        res = unauth_client.post(
            "/api/v1/calendar/callback",
            json={"code": "mock_code_test_sync", "state": valid_state},
            headers=h1,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["synced_events_count"] == 1
        assert data["created_meetings_count"] == 1

        # Check CalendarEvent in DB
        evt = db_session.query(CalendarEvent).filter_by(external_event_id="evt_1001").first()
        assert evt is not None
        assert evt.title == "Q3 Strategy Meeting"
        assert evt.meeting_id is not None

        # Phase 5 Check — Local Meeting metadata created with NO audio file path
        meeting = db_session.query(Meeting).filter_by(id=evt.meeting_id).first()
        assert meeting is not None
        assert meeting.title == "Q3 Strategy Meeting"
        assert meeting.status == MeetingStatus.CREATED
        assert meeting.audio_file_path is None


@pytest.mark.anyio
async def test_calendar_sync_idempotency_and_duplicate_prevention(db_session: Session):
    u1 = auth_service.register_user(db_session, "idempotent_user@example.com", "password123")
    ws1 = workspace_service.get_or_create_default_workspace(db_session, u1)

    conn = CalendarConnection(
        user_id=u1.id,
        workspace_id=ws1.id,
        provider="google",
        account_email="idempotent_user@example.com",
        status=CalendarConnectionStatus.ACTIVE,
    )
    db_session.add(conn)
    db_session.commit()

    now = datetime.now(timezone.utc)
    mock_events = [
        CalendarEventData(
            external_event_id="evt_idempotent_1",
            title="Idempotency Test Event",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status="confirmed",
        )
    ]

    with patch(
        "app.services.google_calendar_provider.GoogleCalendarProvider.list_upcoming_events",
        new_callable=AsyncMock,
        return_value=mock_events,
    ):
        # Initial sync
        synced1, created1 = await calendar_service.sync_calendar_events(db_session, conn)
        assert synced1 == 1
        assert created1 == 1

        # Repeat sync with identical event -> NO duplicate CalendarEvents or Meetings created!
        synced2, created2 = await calendar_service.sync_calendar_events(db_session, conn)
        assert synced2 == 1
        assert created2 == 0

        # Verify total database records count remains 1
        total_events = db_session.query(CalendarEvent).filter_by(workspace_id=ws1.id).count()
        total_meetings = db_session.query(Meeting).filter_by(workspace_id=ws1.id).count()
        assert total_events == 1
        assert total_meetings == 1


@pytest.mark.anyio
async def test_calendar_cancelled_event_handling(db_session: Session):
    u1 = auth_service.register_user(db_session, "cancelled_user@example.com", "password123")
    ws1 = workspace_service.get_or_create_default_workspace(db_session, u1)

    conn = CalendarConnection(
        user_id=u1.id,
        workspace_id=ws1.id,
        provider="google",
        account_email="cancelled_user@example.com",
        status=CalendarConnectionStatus.ACTIVE,
    )
    db_session.add(conn)
    db_session.commit()

    now = datetime.now(timezone.utc)
    initial_event = [
        CalendarEventData(
            external_event_id="evt_to_cancel",
            title="To Be Cancelled Meeting",
            start_time=now + timedelta(hours=4),
            end_time=now + timedelta(hours=5),
            status="confirmed",
        )
    ]

    # Sync confirmed event
    with patch(
        "app.services.google_calendar_provider.GoogleCalendarProvider.list_upcoming_events",
        new_callable=AsyncMock,
        return_value=initial_event,
    ):
        await calendar_service.sync_calendar_events(db_session, conn)

    evt = db_session.query(CalendarEvent).filter_by(external_event_id="evt_to_cancel").first()
    assert evt.status == CalendarEventStatus.CONFIRMED

    # Event is now cancelled on Google Calendar
    cancelled_event = [
        CalendarEventData(
            external_event_id="evt_to_cancel",
            title="To Be Cancelled Meeting",
            start_time=now + timedelta(hours=4),
            end_time=now + timedelta(hours=5),
            status="cancelled",
        )
    ]

    with patch(
        "app.services.google_calendar_provider.GoogleCalendarProvider.list_upcoming_events",
        new_callable=AsyncMock,
        return_value=cancelled_event,
    ):
        await calendar_service.sync_calendar_events(db_session, conn)

    db_session.refresh(evt)
    assert evt.status == CalendarEventStatus.CANCELLED

    # Confirm cancelled event is excluded from list_upcoming_events query
    upcoming, total = calendar_service.list_upcoming_events(db_session, ws1.id, u1.id)
    assert total == 0
    assert len(upcoming) == 0


def test_calendar_upcoming_filtering_and_workspace_isolation(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_test_users_and_workspaces(db_session)
    now = datetime.now(timezone.utc)

    conn1 = CalendarConnection(user_id=u1.id, workspace_id=ws1.id, provider="google", account_email="u1@ex.com")
    conn2 = CalendarConnection(user_id=u2.id, workspace_id=ws2.id, provider="google", account_email="u2@ex.com")
    db_session.add_all([conn1, conn2])
    db_session.commit()

    # Past event (should be excluded)
    past_evt = CalendarEvent(
        calendar_connection_id=conn1.id,
        workspace_id=ws1.id,
        user_id=u1.id,
        external_event_id="past_01",
        title="Past Meeting",
        start_time=now - timedelta(days=2),
        end_time=now - timedelta(days=2, hours=-1),
        status="confirmed",
    )
    # Upcoming event in workspace 1
    up1 = CalendarEvent(
        calendar_connection_id=conn1.id,
        workspace_id=ws1.id,
        user_id=u1.id,
        external_event_id="up_01",
        title="Workspace 1 Upcoming",
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, hours=1),
        status="confirmed",
    )
    # Upcoming event in workspace 2
    up2 = CalendarEvent(
        calendar_connection_id=conn2.id,
        workspace_id=ws2.id,
        user_id=u2.id,
        external_event_id="up_02",
        title="Workspace 2 Upcoming",
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=2, hours=1),
        status="confirmed",
    )
    db_session.add_all([past_evt, up1, up2])
    db_session.commit()

    # User 1 fetches upcoming for workspace 1 -> Returns only up1
    res1 = unauth_client.get(f"/api/v1/calendar/upcoming?workspace_id={ws1.id}", headers=h1)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 1
    assert data1["items"][0]["title"] == "Workspace 1 Upcoming"

    # User 1 attempts to fetch upcoming for workspace 2 -> 403 Forbidden
    res_iso = unauth_client.get(f"/api/v1/calendar/upcoming?workspace_id={ws2.id}", headers=h1)
    assert res_iso.status_code == 403
