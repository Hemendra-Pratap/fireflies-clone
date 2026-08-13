from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.action_item import ActionItem
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript_segment import TranscriptSegment


def test_cors_preflight_headers(client: TestClient) -> None:
    """Verify CORS middleware returns correct Access-Control-Allow-Origin headers."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/v1/meetings", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_search_by_title_and_transcript(client: TestClient, db_session: Session) -> None:
    """Test full-text search across meeting titles and transcript segment text."""
    now = datetime.now(timezone.utc)
    # Meeting 1: title match
    m1 = Meeting(
        title="Architecture Sync with Product",
        recorded_at=now,
        status=MeetingStatus.COMPLETED,
    )
    db_session.add(m1)
    db_session.flush()

    seg1 = TranscriptSegment(
        meeting_id=m1.id,
        sequence_number=1,
        start_time_ms=0,
        end_time_ms=5000,
        text="Discussing backend microservices and deployment.",
    )
    db_session.add(seg1)

    # Meeting 2: transcript text match
    m2 = Meeting(
        title="Weekly Status",
        recorded_at=now,
        status=MeetingStatus.COMPLETED,
    )
    db_session.add(m2)
    db_session.flush()

    seg2 = TranscriptSegment(
        meeting_id=m2.id,
        sequence_number=1,
        start_time_ms=0,
        end_time_ms=5000,
        text="We need to finalize the Gemini AI prompt engineering.",
    )
    db_session.add(seg2)
    db_session.commit()

    # Search title match "Architecture"
    res1 = client.get("/api/v1/meetings/search?q=Architecture")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 1
    assert data1["items"][0]["title"] == "Architecture Sync with Product"

    # Search transcript match "Gemini"
    res2 = client.get("/api/v1/meetings/search?q=Gemini")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["title"] == "Weekly Status"

    # Search no match
    res3 = client.get("/api/v1/meetings/search?q=NonexistentQueryKey")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["total"] == 0
    assert len(data3["items"]) == 0


def test_action_item_completion_toggle(client: TestClient, db_session: Session) -> None:
    """Test PATCH /api/v1/action-items/{id} completion status and timestamp tracking."""
    m = Meeting(
        title="Action Item Test",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.COMPLETED,
    )
    db_session.add(m)
    db_session.flush()

    ai = ActionItem(
        meeting_id=m.id,
        description="Write comprehensive integration tests.",
        is_completed=False,
    )
    db_session.add(ai)
    db_session.commit()
    db_session.refresh(ai)

    action_id = ai.id

    # 1. Complete action item
    res_complete = client.patch(
        f"/api/v1/action-items/{action_id}",
        json={"is_completed": True},
    )
    assert res_complete.status_code == 200
    data_c = res_complete.json()
    assert data_c["is_completed"] is True
    assert data_c["completed_at"] is not None

    # 2. Reopen action item
    res_reopen = client.patch(
        f"/api/v1/action-items/{action_id}",
        json={"is_completed": False},
    )
    assert res_reopen.status_code == 200
    data_r = res_reopen.json()
    assert data_r["is_completed"] is False
    assert data_r["completed_at"] is None


def test_action_item_update_404_and_invalid(client: TestClient) -> None:
    """Test 404 for nonexistent action item."""
    res = client.patch("/api/v1/action-items/99999", json={"is_completed": True})
    assert res.status_code == 404
    assert res.json()["detail"] == "Action item not found"
