import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import Participant
from app.models.transcript_segment import TranscriptSegment
from app.services.storage_service import storage_service
from app.services.transcription_provider import MockTranscriptionProvider
from app.services.transcription_service import transcription_service


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def create_meeting_with_audio(client: TestClient) -> dict:
    # 1. Create meeting
    payload = {
        "title": "Transcription Pipeline Test Meeting",
        "source_name": "Zoom",
        "recorded_at": "2026-08-13T10:00:00Z",
        "duration_ms": 30000,
        "status": MeetingStatus.CREATED,
    }
    res = client.post("/api/v1/meetings", json=payload)
    assert res.status_code == 201
    meeting = res.json()

    # 2. Upload dummy audio file
    dummy_audio = b"ID3\x04\x00\x00\x00\x00\x00\x00Sample MP3 Data For Transcription Test"
    files = {"file": ("test_transcribe.mp3", dummy_audio, "audio/mpeg")}
    upload_res = client.post(f"/api/v1/meetings/{meeting['id']}/audio", files=files)
    assert upload_res.status_code == 200
    return upload_res.json()


@pytest.mark.anyio
async def test_successful_transcription(db_session: Session, client: TestClient) -> None:
    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]

    provider = MockTranscriptionProvider(include_speakers=True)
    updated_meeting = await transcription_service.transcribe_meeting(
        db_session, meeting_id, provider=provider
    )

    assert updated_meeting.status == MeetingStatus.TRANSCRIBED
    assert updated_meeting.error_message is None
    assert updated_meeting.duration_ms == 20000


@pytest.mark.anyio
async def test_transcript_segments_and_sequence_numbers(
    db_session: Session, client: TestClient
) -> None:
    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]

    provider = MockTranscriptionProvider(include_speakers=True)
    await transcription_service.transcribe_meeting(db_session, meeting_id, provider=provider)

    segments = (
        db_session.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.sequence_number)
        .all()
    )

    assert len(segments) == 3
    assert [s.sequence_number for s in segments] == [1, 2, 3]
    assert segments[0].text == "Welcome everyone to today's meeting."
    assert segments[0].start_time_ms == 0
    assert segments[0].end_time_ms == 5000


@pytest.mark.anyio
async def test_participant_creation_and_mapping(
    db_session: Session, client: TestClient
) -> None:
    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]

    provider = MockTranscriptionProvider(include_speakers=True)
    await transcription_service.transcribe_meeting(db_session, meeting_id, provider=provider)

    participants = (
        db_session.query(Participant)
        .filter(Participant.meeting_id == meeting_id)
        .all()
    )

    assert len(participants) == 2
    speaker_labels = {p.speaker_label for p in participants}
    assert speaker_labels == {"Speaker 1", "Speaker 2"}

    segments = (
        db_session.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.sequence_number)
        .all()
    )

    p1 = next(p for p in participants if p.speaker_label == "Speaker 1")
    p2 = next(p for p in participants if p.speaker_label == "Speaker 2")

    assert segments[0].participant_id == p1.id
    assert segments[1].participant_id == p2.id
    assert segments[2].participant_id == p1.id


@pytest.mark.anyio
async def test_missing_speaker_labels_handling(
    db_session: Session, client: TestClient
) -> None:
    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]

    provider = MockTranscriptionProvider(include_speakers=False)
    await transcription_service.transcribe_meeting(db_session, meeting_id, provider=provider)

    participants = (
        db_session.query(Participant)
        .filter(Participant.meeting_id == meeting_id)
        .all()
    )
    assert len(participants) == 0

    segments = (
        db_session.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .all()
    )
    assert len(segments) == 2
    for seg in segments:
        assert seg.participant_id is None


@pytest.mark.anyio
async def test_transcription_provider_failure_preserves_audio(
    db_session: Session, client: TestClient
) -> None:
    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]
    audio_path = meeting["audio_file_path"]

    full_path = storage_service.get_full_path(audio_path)
    assert full_path.exists()

    provider = MockTranscriptionProvider(raise_error=True)

    with pytest.raises(RuntimeError):
        await transcription_service.transcribe_meeting(db_session, meeting_id, provider=provider)

    db_meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
    assert db_meeting.status == MeetingStatus.FAILED
    assert db_meeting.error_message is not None
    assert "Mock transcription provider failure" in db_meeting.error_message

    # Confirm uploaded audio file on disk is NOT deleted
    assert full_path.exists()

    # Cleanup storage file
    storage_service.delete_file(audio_path)


def test_retry_endpoint(client: TestClient) -> None:
    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]

    response = client.post(f"/api/v1/meetings/{meeting_id}/transcribe")
    assert response.status_code == 202
    data = response.json()
    assert data["id"] == meeting_id
    assert data["status"] == MeetingStatus.TRANSCRIBING

    # Cleanup audio
    if data.get("audio_file_path"):
        storage_service.delete_file(data["audio_file_path"])


def test_transcribe_invalid_meeting_id(client: TestClient) -> None:
    response = client.post("/api/v1/meetings/99999/transcribe")
    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"


def test_transcribe_meeting_without_audio(client: TestClient) -> None:
    payload = {
        "title": "No Audio Meeting",
        "recorded_at": "2026-08-13T10:00:00Z",
    }
    m_res = client.post("/api/v1/meetings", json=payload)
    m_id = m_res.json()["id"]

    response = client.post(f"/api/v1/meetings/{m_id}/transcribe")
    assert response.status_code == 400
    assert response.json()["detail"] == "Meeting has no uploaded audio file"


def test_duplicate_transcription_conflict(client: TestClient, db_session: Session) -> None:
    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]

    db_m = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
    db_m.status = MeetingStatus.TRANSCRIBING
    db_session.commit()

    response = client.post(f"/api/v1/meetings/{meeting_id}/transcribe")
    assert response.status_code == 409
    assert response.json()["detail"] == "Transcription is already in progress"

    # Cleanup
    if meeting.get("audio_file_path"):
        storage_service.delete_file(meeting["audio_file_path"])


def test_gemini_provider_config_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.transcription_provider import (
        GeminiTranscriptionProvider,
        get_transcription_provider,
    )

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # Directly creating GeminiTranscriptionProvider without API key raises ValueError on transcribe
    provider = GeminiTranscriptionProvider(api_key="")
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        asyncio.run(provider.transcribe(Path("dummy.mp3")))

    # Requesting gemini provider when API key is unconfigured raises ValueError
    with pytest.raises(ValueError, match="GEMINI_API_KEY is missing or unconfigured"):
        get_transcription_provider(provider_name="gemini")


@pytest.mark.anyio
async def test_empty_transcript_handling(db_session: Session, client: TestClient) -> None:
    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]

    class EmptyTranscriptionProvider:
        async def transcribe(self, audio_file_path: Path):
            from app.services.transcription_provider import TranscriptionResult
            return TranscriptionResult(segments=[])

    with pytest.raises(ValueError, match="empty transcript"):
        await transcription_service.transcribe_meeting(
            db_session, meeting_id, provider=EmptyTranscriptionProvider()
        )

    db_m = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
    assert db_m.status == MeetingStatus.FAILED
    assert "empty transcript" in db_m.error_message.lower()

    if meeting.get("audio_file_path"):
        storage_service.delete_file(meeting["audio_file_path"])


def test_background_worker_auto_chaining_success(client: TestClient, db_session: Session) -> None:
    from app.api.v1.routes.meetings import _run_transcription_in_background

    meeting = create_meeting_with_audio(client)
    meeting_id = meeting["id"]

    _run_transcription_in_background(meeting_id, db=db_session)

    db_session.expire_all()
    db_m = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
    assert db_m.status == MeetingStatus.COMPLETED
    assert db_m.error_message is None

    if meeting.get("audio_file_path"):
        storage_service.delete_file(meeting["audio_file_path"])
