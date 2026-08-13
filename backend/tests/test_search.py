from datetime import datetime, timezone
import pytest

from app.core.security import create_access_token
from app.models.action_item import ActionItem
from app.models.chapter import Chapter
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import Participant
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment
from app.services.auth_service import auth_service
from app.services.search_service import search_service
from app.services.workspace_service import workspace_service


def test_search_by_meeting_title(db_session):
    """Test searching meetings by title match."""
    user = auth_service.register_user(db_session, "search1@example.com", "password123")
    ws = workspace_service.get_or_create_default_workspace(db_session, user)

    meeting = Meeting(
        title="Q4 Financial Review",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
        user_id=user.id,
        workspace_id=ws.id,
    )
    db_session.add(meeting)
    db_session.commit()

    res = search_service.search(db_session, user_id=user.id, query_str="Financial")
    assert res.total == 1
    assert res.items[0].meeting_id == meeting.id
    assert res.items[0].match_type == "title"


def test_search_by_transcript_segment(db_session):
    """Test searching meetings by transcript segment content."""
    user = auth_service.register_user(db_session, "search2@example.com", "password123")
    ws = workspace_service.get_or_create_default_workspace(db_session, user)

    meeting = Meeting(
        title="Engineering Sync",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
        user_id=user.id,
        workspace_id=ws.id,
    )
    db_session.add(meeting)
    db_session.flush()

    segment = TranscriptSegment(
        meeting_id=meeting.id,
        start_time_ms=5000,
        end_time_ms=10000,
        text="We decided to deploy the new Kubernetes cluster today.",
        sequence_number=1,
    )
    db_session.add(segment)
    db_session.commit()

    res = search_service.search(db_session, user_id=user.id, query_str="Kubernetes")
    assert res.total == 1
    assert res.items[0].match_type == "transcript"
    assert "Kubernetes" in res.items[0].matched_text


def test_search_by_summary(db_session):
    """Test searching meetings by AI summary text."""
    user = auth_service.register_user(db_session, "search3@example.com", "password123")
    ws = workspace_service.get_or_create_default_workspace(db_session, user)

    meeting = Meeting(
        title="Product Planning",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
        user_id=user.id,
        workspace_id=ws.id,
    )
    db_session.add(meeting)
    db_session.flush()

    summary = Summary(
        meeting_id=meeting.id,
        overview="Discussed launch strategy for the mobile application.",
        key_points="Finalized iOS release date.",
    )
    db_session.add(summary)
    db_session.commit()

    res = search_service.search(db_session, user_id=user.id, query_str="mobile application")
    assert res.total == 1
    assert res.items[0].match_type == "summary"


def test_search_by_action_item(db_session):
    """Test searching meetings by action item description."""
    user = auth_service.register_user(db_session, "search4@example.com", "password123")
    ws = workspace_service.get_or_create_default_workspace(db_session, user)

    meeting = Meeting(
        title="Sprint Retrospective",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
        user_id=user.id,
        workspace_id=ws.id,
    )
    db_session.add(meeting)
    db_session.flush()

    ai = ActionItem(
        meeting_id=meeting.id,
        description="Update database migration scripts for PostgreSQL.",
    )
    db_session.add(ai)
    db_session.commit()

    res = search_service.search(db_session, user_id=user.id, query_str="PostgreSQL")
    assert res.total == 1
    assert res.items[0].match_type == "action_item"


def test_search_by_chapter(db_session):
    """Test searching meetings by chapter title or summary."""
    user = auth_service.register_user(db_session, "search5@example.com", "password123")
    ws = workspace_service.get_or_create_default_workspace(db_session, user)

    meeting = Meeting(
        title="Architecture Review",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
        user_id=user.id,
        workspace_id=ws.id,
    )
    db_session.add(meeting)
    db_session.flush()

    chapter = Chapter(
        meeting_id=meeting.id,
        title="Microservice Decoupling",
        summary="Detailed plan to refactor monolithic services.",
        start_time_ms=12000,
        end_time_ms=45000,
        sequence_number=1,
    )
    db_session.add(chapter)
    db_session.commit()

    res = search_service.search(db_session, user_id=user.id, query_str="Microservice")
    assert res.total == 1
    assert res.items[0].match_type == "chapter"


def test_search_tenant_isolation(db_session):
    """Test search results are strictly isolated to user's authorized workspaces."""
    user1 = auth_service.register_user(db_session, "userA@example.com", "password123")
    user2 = auth_service.register_user(db_session, "userB@example.com", "password123")
    ws1 = workspace_service.get_or_create_default_workspace(db_session, user1)
    ws2 = workspace_service.get_or_create_default_workspace(db_session, user2)

    m1 = Meeting(title="Secret Project Alpha", recorded_at=datetime.now(timezone.utc), user_id=user1.id, workspace_id=ws1.id)
    m2 = Meeting(title="Secret Project Beta", recorded_at=datetime.now(timezone.utc), user_id=user2.id, workspace_id=ws2.id)
    db_session.add_all([m1, m2])
    db_session.commit()

    res1 = search_service.search(db_session, user_id=user1.id, query_str="Secret Project")
    assert res1.total == 1
    assert res1.items[0].meeting_id == m1.id

    res2 = search_service.search(db_session, user_id=user2.id, query_str="Secret Project")
    assert res2.total == 1
    assert res2.items[0].meeting_id == m2.id


def test_search_api_endpoint(unauth_client, db_session):
    """Test GET /api/v1/search API endpoint."""
    user = auth_service.register_user(db_session, "searchapi@example.com", "password123")
    ws = workspace_service.get_or_create_default_workspace(db_session, user)

    meeting = Meeting(
        title="Weekly Executive Sync",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
        user_id=user.id,
        workspace_id=ws.id,
    )
    db_session.add(meeting)
    db_session.commit()

    token, _ = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = unauth_client.get("/api/v1/search?q=Executive", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["meeting_title"] == "Weekly Executive Sync"


def test_meetings_search_endpoint_compatibility(unauth_client, db_session):
    """Test GET /api/v1/meetings/search frontend compatibility endpoint."""
    user = auth_service.register_user(db_session, "searchcompat@example.com", "password123")
    ws = workspace_service.get_or_create_default_workspace(db_session, user)

    meeting = Meeting(
        title="Quarterly Roadmap Update",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
        user_id=user.id,
        workspace_id=ws.id,
    )
    db_session.add(meeting)
    db_session.commit()

    token, _ = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = unauth_client.get("/api/v1/meetings/search?q=Roadmap", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Quarterly Roadmap Update"


def test_search_empty_query(db_session):
    """Test search with empty query returns empty results cleanly."""
    user = auth_service.register_user(db_session, "searchempty@example.com", "password123")
    res = search_service.search(db_session, user_id=user.id, query_str="")
    assert res.total == 0
    assert len(res.items) == 0
