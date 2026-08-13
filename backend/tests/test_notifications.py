from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.meeting import Meeting, MeetingStatus
from app.models.notification import Notification, NotificationType
from app.services.auth_service import auth_service
from app.services.notification_service import notification_service
from app.services.workspace_service import workspace_service
from app.worker.processor import job_processor


def setup_test_users_and_workspaces(db_session: Session):
    user1 = auth_service.register_user(db_session, "notif_user1@example.com", "password123")
    user2 = auth_service.register_user(db_session, "notif_user2@example.com", "password123")

    ws1 = workspace_service.get_or_create_default_workspace(db_session, user1)
    ws2 = workspace_service.get_or_create_default_workspace(db_session, user2)

    token1, _ = create_access_token(str(user1.id))
    token2, _ = create_access_token(str(user2.id))

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    return user1, user2, ws1, ws2, headers1, headers2


def test_notification_creation_and_listing(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_test_users_and_workspaces(db_session)

    # Create notifications for user 1
    n1 = notification_service.create_notification(
        db=db_session,
        user_id=u1.id,
        notification_type=NotificationType.MEETING_COMPLETED,
        title="Meeting Completed",
        message="Sprint Planning has been processed.",
        workspace_id=ws1.id,
    )
    n2 = notification_service.create_notification(
        db=db_session,
        user_id=u1.id,
        notification_type=NotificationType.UPCOMING_MEETING,
        title="Upcoming Meeting",
        message="Design review starts in 30 minutes.",
        workspace_id=ws1.id,
    )

    # Fetch notifications list via API
    res = unauth_client.get(f"/api/v1/notifications?workspace_id={ws1.id}", headers=h1)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["unread_count"] == 2
    assert data["items"][0]["title"] == "Upcoming Meeting"  # Order DESC by created_at


def test_notification_unread_count_and_mark_read(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_test_users_and_workspaces(db_session)

    n1 = notification_service.create_notification(
        db=db_session,
        user_id=u1.id,
        notification_type=NotificationType.MEETING_COMPLETED,
        title="Test Unread 1",
        message="Message 1",
        workspace_id=ws1.id,
    )
    n2 = notification_service.create_notification(
        db=db_session,
        user_id=u1.id,
        notification_type=NotificationType.MEETING_FAILED,
        title="Test Unread 2",
        message="Message 2",
        workspace_id=ws1.id,
    )

    # Check unread count
    res_count = unauth_client.get(f"/api/v1/notifications/unread-count?workspace_id={ws1.id}", headers=h1)
    assert res_count.status_code == 200
    assert res_count.json()["unread_count"] == 2

    # Mark single notification as read
    res_read = unauth_client.post(f"/api/v1/notifications/{n1.id}/read", headers=h1)
    assert res_read.status_code == 200
    assert res_read.json()["read_at"] is not None

    # Verify unread count is now 1
    res_count2 = unauth_client.get(f"/api/v1/notifications/unread-count?workspace_id={ws1.id}", headers=h1)
    assert res_count2.json()["unread_count"] == 1

    # Mark all as read
    res_all = unauth_client.post(f"/api/v1/notifications/read-all?workspace_id={ws1.id}", headers=h1)
    assert res_all.status_code == 200
    assert res_all.json()["marked_count"] == 1

    # Verify unread count is 0
    res_count3 = unauth_client.get(f"/api/v1/notifications/unread-count?workspace_id={ws1.id}", headers=h1)
    assert res_count3.json()["unread_count"] == 0


def test_notification_user_and_workspace_isolation(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_test_users_and_workspaces(db_session)

    n1 = notification_service.create_notification(
        db=db_session,
        user_id=u1.id,
        notification_type=NotificationType.MEETING_COMPLETED,
        title="Private Notification User 1",
        message="Secret data",
        workspace_id=ws1.id,
    )

    # User 2 attempts to fetch User 1's notifications -> Empty items list for user 2
    res_u2 = unauth_client.get(f"/api/v1/notifications?workspace_id={ws2.id}", headers=h2)
    assert res_u2.status_code == 200
    assert res_u2.json()["total"] == 0

    # User 2 attempts to mark User 1's notification as read -> 404 Not Found
    res_hack = unauth_client.post(f"/api/v1/notifications/{n1.id}/read", headers=h2)
    assert res_hack.status_code == 404

    # User 2 attempts to fetch notifications from User 1's workspace -> 403 Forbidden
    res_forbidden = unauth_client.get(f"/api/v1/notifications?workspace_id={ws1.id}", headers=h2)
    assert res_forbidden.status_code == 403


def test_meeting_completion_and_failure_notifications(db_session: Session):
    u1 = auth_service.register_user(db_session, "job_notif_user@example.com", "password123")
    ws1 = workspace_service.get_or_create_default_workspace(db_session, u1)

    m1 = Meeting(
        title="Job Notification Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.CREATED,
        user_id=u1.id,
        workspace_id=ws1.id,
    )
    db_session.add(m1)
    db_session.commit()

    # Trigger job failure notification on invalid audio
    try:
        job_processor.enqueue_and_process(db_session, "transcription", m1.id)
    except Exception:
        pass

    # Verify MEETING_FAILED notification created
    notifs = notification_service.list_notifications(db_session, user_id=u1.id)[0]
    assert len(notifs) == 1
    assert notifs[0].type == NotificationType.MEETING_FAILED
    assert notifs[0].meeting_id == m1.id
    assert "Processing for meeting" in notifs[0].message


def test_duplicate_notification_prevention(db_session: Session):
    u1 = auth_service.register_user(db_session, "dedup_notif@example.com", "password123")
    ws1 = workspace_service.get_or_create_default_workspace(db_session, u1)

    m1 = Meeting(
        title="Dedup Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
        user_id=u1.id,
        workspace_id=ws1.id,
    )
    db_session.add(m1)
    db_session.commit()

    # Attempt to create duplicate meeting completion notifications
    n1 = notification_service.create_notification(
        db=db_session,
        user_id=u1.id,
        notification_type=NotificationType.MEETING_COMPLETED,
        title="Completed",
        message="Done",
        workspace_id=ws1.id,
        meeting_id=m1.id,
    )
    n2 = notification_service.create_notification(
        db=db_session,
        user_id=u1.id,
        notification_type=NotificationType.MEETING_COMPLETED,
        title="Completed",
        message="Done",
        workspace_id=ws1.id,
        meeting_id=m1.id,
    )

    assert n1.id == n2.id  # Same notification record returned (idempotency)
    total_notifs = db_session.query(Notification).filter_by(user_id=u1.id).count()
    assert total_notifs == 1
