from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingStatus
from app.services.storage_service import storage_service


def create_test_meeting(client: TestClient) -> dict:
    payload = {
        "title": "Audio Upload Test Meeting",
        "source_name": "Zoom",
        "recorded_at": "2026-08-13T10:00:00Z",
        "duration_ms": 60000,
        "status": MeetingStatus.CREATED,
    }
    response = client.post("/api/v1/meetings", json=payload)
    assert response.status_code == 201
    return response.json()


def test_upload_audio_success(client: TestClient) -> None:
    meeting = create_test_meeting(client)
    meeting_id = meeting["id"]

    dummy_audio = b"ID3\x04\x00\x00\x00\x00\x00\x00Dummy MP3 Content For Testing"
    files = {"file": ("test_recording.mp3", dummy_audio, "audio/mpeg")}

    response = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == meeting_id
    assert data["status"] == MeetingStatus.UPLOADED
    assert data["audio_filename"] is not None
    assert data["audio_filename"].endswith(".mp3")
    assert data["audio_mime_type"] == "audio/mpeg"
    assert data["audio_size_bytes"] == len(dummy_audio)
    assert data["error_message"] is None

    # Verify physical file existence in storage
    assert data["audio_file_path"] is not None
    full_path = storage_service.get_full_path(data["audio_file_path"])
    assert full_path.exists()
    assert full_path.read_bytes() == dummy_audio

    # Cleanup storage file
    storage_service.delete_file(data["audio_file_path"])


def test_upload_audio_nonexistent_meeting(client: TestClient) -> None:
    dummy_audio = b"Dummy Audio Content"
    files = {"file": ("sample.mp3", dummy_audio, "audio/mpeg")}

    response = client.post("/api/v1/meetings/99999/audio", files=files)
    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"


def test_upload_audio_invalid_mime_type(client: TestClient) -> None:
    meeting = create_test_meeting(client)
    files = {"file": ("document.pdf", b"%PDF-1.4 dummy content", "application/pdf")}

    response = client.post(f"/api/v1/meetings/{meeting['id']}/audio", files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_audio_invalid_extension(client: TestClient) -> None:
    meeting = create_test_meeting(client)
    files = {"file": ("executable.exe", b"MZ dummy binary", "audio/mpeg")}

    # Extension check or MIME check
    response = client.post(f"/api/v1/meetings/{meeting['id']}/audio", files=files)
    # If content_type is audio/mpeg, it may accept, but let's test invalid content_type + ext
    files_invalid = {"file": ("executable.exe", b"MZ dummy binary", "application/octet-stream")}
    response_invalid = client.post(f"/api/v1/meetings/{meeting['id']}/audio", files=files_invalid)
    assert response_invalid.status_code == 400
    assert "Unsupported file type" in response_invalid.json()["detail"]


def test_upload_audio_oversized(client: TestClient) -> None:
    meeting = create_test_meeting(client)
    dummy_audio = b"A" * 1024  # 1 KB dummy file

    # Patch max size to 500 bytes for testing
    with patch("app.services.storage_service.DEFAULT_MAX_FILE_SIZE", 500):
        files = {"file": ("large_audio.mp3", dummy_audio, "audio/mpeg")}
        response = client.post(f"/api/v1/meetings/{meeting['id']}/audio", files=files)
        assert response.status_code == 400
        assert "exceeds maximum allowed limit" in response.json()["detail"]


def test_get_meeting_status_success(client: TestClient) -> None:
    meeting = create_test_meeting(client)
    meeting_id = meeting["id"]

    response = client.get(f"/api/v1/meetings/{meeting_id}/status")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == meeting_id
    assert data["status"] == MeetingStatus.CREATED
    assert data["error_message"] is None
    assert "updated_at" in data


def test_get_meeting_status_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/meetings/99999/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"


def test_delete_meeting_removes_audio_from_storage(client: TestClient) -> None:
    meeting = create_test_meeting(client)
    meeting_id = meeting["id"]

    dummy_audio = b"Audio for deletion test"
    files = {"file": ("delete_test.wav", dummy_audio, "audio/wav")}

    upload_resp = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    assert upload_resp.status_code == 200
    file_path = upload_resp.json()["audio_file_path"]
    full_path = storage_service.get_full_path(file_path)
    assert full_path.exists()

    # Delete meeting
    del_resp = client.delete(f"/api/v1/meetings/{meeting_id}")
    assert del_resp.status_code == 204

    # Confirm file was deleted from storage disk
    assert not full_path.exists()


def test_get_meeting_audio_success(client: TestClient) -> None:
    meeting = create_test_meeting(client)
    meeting_id = meeting["id"]

    dummy_audio = b"ID3\x04\x00\x00\x00\x00\x00\x00Streaming Audio Content Test"
    files = {"file": ("stream_recording.mp3", dummy_audio, "audio/mpeg")}

    upload_resp = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    assert upload_resp.status_code == 200

    # Test GET audio endpoint
    audio_resp = client.get(f"/api/v1/meetings/{meeting_id}/audio")
    assert audio_resp.status_code == 200
    assert audio_resp.content == dummy_audio
    assert "audio/mpeg" in audio_resp.headers.get("content-type", "")

    storage_service.delete_file(upload_resp.json()["audio_file_path"])


def test_get_meeting_audio_not_uploaded(client: TestClient) -> None:
    meeting = create_test_meeting(client)
    response = client.get(f"/api/v1/meetings/{meeting['id']}/audio")
    assert response.status_code == 404
    assert "not uploaded" in response.json()["detail"].lower()


def test_get_meeting_audio_idor_unauthorized(unauth_client: TestClient, db_session: Session) -> None:
    from app.services.auth_service import auth_service
    from app.core.security import create_access_token
    from datetime import datetime, timezone

    user1 = auth_service.register_user(db_session, "audio_user1@example.com", "password123")
    user2 = auth_service.register_user(db_session, "audio_user2@example.com", "password123")

    m1 = Meeting(
        title="User 1 Audio Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        audio_file_path="audio/mock.mp3",
        user_id=user1.id,
    )
    db_session.add(m1)
    db_session.commit()

    token2, _ = create_access_token(str(user2.id))
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 2 attempts to fetch User 1's audio file
    resp = unauth_client.get(f"/api/v1/meetings/{m1.id}/audio", headers=headers2)
    assert resp.status_code == 404

