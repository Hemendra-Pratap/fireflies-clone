from datetime import datetime, timezone

from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.summary import Summary


def test_create_meeting_success(client):
    """POST /api/v1/meetings creates a meeting and returns HTTP 201 Created."""
    payload = {
        "title": "Q3 Architecture Review",
        "source_name": "Zoom",
        "recorded_at": "2026-08-13T10:00:00Z",
        "duration_ms": 3600000,
        "status": "completed",
    }
    response = client.post("/api/v1/meetings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == "Q3 Architecture Review"
    assert data["source_name"] == "Zoom"
    assert data["status"] == "completed"
    assert "created_at" in data
    assert "updated_at" in data


def test_create_meeting_default_status(client):
    """POST /api/v1/meetings without status defaults to 'created'."""
    payload = {
        "title": "Default Status Meeting",
        "recorded_at": "2026-08-13T10:00:00Z",
    }
    response = client.post("/api/v1/meetings", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"


def test_create_meeting_validation_error(client):
    """POST /api/v1/meetings with missing title returns HTTP 422 Unprocessable Entity."""
    payload = {
        "source_name": "Zoom",
        "recorded_at": "2026-08-13T10:00:00Z",
    }
    response = client.post("/api/v1/meetings", json=payload)
    assert response.status_code == 422


def test_list_meetings_empty(client):
    """GET /api/v1/meetings returns empty paginated list when no meetings exist."""
    response = client.get("/api/v1/meetings")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["size"] == 20
    assert data["pages"] == 0


def test_list_meetings_pagination(client, db_session, test_user):
    """GET /api/v1/meetings respects page and size parameters."""
    for i in range(5):
        m = Meeting(
            title=f"Meeting {i+1}",
            recorded_at=datetime.now(timezone.utc),
            status="completed",
            user_id=test_user.id,
        )
        db_session.add(m)
    db_session.commit()

    # Request page 1 with size 2
    res1 = client.get("/api/v1/meetings?page=1&size=2")
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["total"] == 5
    assert len(d1["items"]) == 2
    assert d1["page"] == 1
    assert d1["size"] == 2
    assert d1["pages"] == 3

    # Request page 3 with size 2
    res3 = client.get("/api/v1/meetings?page=3&size=2")
    assert res3.status_code == 200
    d3 = res3.json()
    assert len(d3["items"]) == 1


def test_list_meetings_filtering_and_search(client, db_session, test_user):
    """GET /api/v1/meetings filters by status and searches by title."""
    m1 = Meeting(
        title="Sprint Planning",
        recorded_at=datetime.now(timezone.utc),
        status="completed",
        user_id=test_user.id,
    )
    m2 = Meeting(
        title="Product Roadmap Sync",
        recorded_at=datetime.now(timezone.utc),
        status="processing",
        user_id=test_user.id,
    )
    m3 = Meeting(
        title="Sprint Retrospective",
        recorded_at=datetime.now(timezone.utc),
        status="completed",
        user_id=test_user.id,
    )
    db_session.add_all([m1, m2, m3])
    db_session.commit()

    # Filter status="processing"
    res_status = client.get("/api/v1/meetings?status=processing")
    assert res_status.status_code == 200
    d_status = res_status.json()
    assert d_status["total"] == 1
    assert d_status["items"][0]["title"] == "Product Roadmap Sync"

    # Search "Sprint"
    res_search = client.get("/api/v1/meetings?search=Sprint")
    assert res_search.status_code == 200
    d_search = res_search.json()
    assert d_search["total"] == 2


def test_get_meeting_by_id_success(client, db_session, test_user):
    """GET /api/v1/meetings/{id} returns single meeting details."""
    m = Meeting(
        title="Client Demo",
        source_name="Google Meet",
        recorded_at=datetime.now(timezone.utc),
        user_id=test_user.id,
    )
    db_session.add(m)
    db_session.commit()

    response = client.get(f"/api/v1/meetings/{m.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == m.id
    assert data["title"] == "Client Demo"
    assert data["source_name"] == "Google Meet"


def test_get_meeting_by_id_not_found(client):
    """GET /api/v1/meetings/{id} with invalid ID returns HTTP 404 Not Found."""
    response = client.get("/api/v1/meetings/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"


def test_update_meeting_success(client, db_session, test_user):
    """PATCH /api/v1/meetings/{id} performs partial update."""
    m = Meeting(
        title="Original Title",
        recorded_at=datetime.now(timezone.utc),
        status="processing",
        user_id=test_user.id,
    )
    db_session.add(m)
    db_session.commit()

    payload = {"title": "Updated Title", "status": "completed"}
    response = client.patch(f"/api/v1/meetings/{m.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "completed"


def test_update_meeting_not_found(client):
    """PATCH /api/v1/meetings/{id} for non-existent meeting returns 404."""
    payload = {"title": "New Title"}
    response = client.patch("/api/v1/meetings/99999", json=payload)
    assert response.status_code == 404


def test_delete_meeting_success(client, db_session, test_user):
    """DELETE /api/v1/meetings/{id} deletes meeting and returns HTTP 204 No Content."""
    m = Meeting(
        title="Meeting to Delete",
        recorded_at=datetime.now(timezone.utc),
        user_id=test_user.id,
    )
    db_session.add(m)
    db_session.commit()

    response = client.delete(f"/api/v1/meetings/{m.id}")
    assert response.status_code == 204

    # Verify meeting is removed from DB
    assert db_session.query(Meeting).filter(Meeting.id == m.id).count() == 0


def test_delete_meeting_not_found(client):
    """DELETE /api/v1/meetings/{id} for non-existent meeting returns 404."""
    response = client.delete("/api/v1/meetings/99999")
    assert response.status_code == 404


def test_delete_meeting_cascades_children_via_api(client, db_session, test_user):
    """Deleting a meeting via API cascades and deletes child participant and summary records."""
    m = Meeting(
        title="Cascade Test Meeting",
        recorded_at=datetime.now(timezone.utc),
        user_id=test_user.id,
    )
    db_session.add(m)
    db_session.commit()

    p = Participant(meeting_id=m.id, display_name="John Doe")
    s = Summary(meeting_id=m.id, overview="Meeting summary overview")
    db_session.add_all([p, s])
    db_session.commit()

    meeting_id = m.id
    participant_id = p.id
    summary_id = s.id

    response = client.delete(f"/api/v1/meetings/{meeting_id}")
    assert response.status_code == 204

    assert db_session.query(Meeting).filter(Meeting.id == meeting_id).count() == 0
    assert (
        db_session.query(Participant).filter(Participant.id == participant_id).count()
        == 0
    )
    assert db_session.query(Summary).filter(Summary.id == summary_id).count() == 0
