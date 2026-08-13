from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import Settings
from app.models.action_item import ActionItem
from app.models.chapter import Chapter
from app.models.job import Job, JobStatus, JobType
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import Participant
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment
from app.services.ai.meeting_intelligence import meeting_intelligence_service
from app.services.auth_service import auth_service
from app.services.storage_service import storage_service
from app.services.transcription_provider import (
    GeminiTranscriptionProvider,
    get_transcription_provider,
)
from app.worker.processor import job_processor


def test_gemini_provider_unconfigured_api_key(monkeypatch):
    """Test Gemini STT provider raises ValueError when GEMINI_API_KEY is unconfigured."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mock_settings = Settings(gemini_api_key=None)
    monkeypatch.setattr("app.services.transcription_provider.settings", mock_settings)

    provider = GeminiTranscriptionProvider(api_key=None)
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        import asyncio
        asyncio.run(provider.transcribe(storage_service.storage_dir / "dummy.mp3"))


def test_get_transcription_provider_gemini_missing_key(monkeypatch):
    """Test get_transcription_provider raises ValueError if provider is 'gemini' but key is missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    mock_settings = Settings(gemini_api_key=None, transcription_provider="gemini")
    monkeypatch.setattr("app.services.transcription_provider.settings", mock_settings)

    with pytest.raises(ValueError, match="GEMINI_API_KEY is missing or unconfigured"):
        get_transcription_provider(provider_name="gemini")


def test_gemini_remote_file_deleted_in_finally_block(tmp_path):
    """Test uploaded audio file on Google Cloud is deleted in finally block even when generation fails."""
    fake_audio_file = tmp_path / "test.mp3"
    fake_audio_file.write_bytes(b"FAKE_AUDIO_DATA_FOR_TESTING")

    mock_client = MagicMock()
    mock_uploaded_file = MagicMock()
    mock_uploaded_file.name = "files/test12345"
    mock_client.files.upload.return_value = mock_uploaded_file
    mock_client.models.generate_content.side_effect = RuntimeError("API Generation Error")

    with patch("google.genai.Client", return_value=mock_client):
        provider = GeminiTranscriptionProvider(api_key="fake_key_123")
        with pytest.raises(RuntimeError, match="API Generation Error"):
            import asyncio
            asyncio.run(provider.transcribe(fake_audio_file))

    # Verify upload was called and delete was unconditionally executed in finally block
    mock_client.files.upload.assert_called_once()
    mock_client.files.delete.assert_called_once_with(name="files/test12345")


def test_upload_zero_byte_audio_rejected(unauth_client, db_session):
    """Test upload endpoint rejects 0-byte audio file immediately with 400 Bad Request."""
    user = auth_service.register_user(db_session, "zerobyte@example.com", "password123")

    meeting = Meeting(
        title="Zero Byte Test Meeting",
        recorded_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    from app.core.security import create_access_token
    token, _ = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    empty_file = ("empty.mp3", BytesIO(b""), "audio/mpeg")
    res = unauth_client.post(
        f"/api/v1/meetings/{meeting.id}/audio",
        files={"file": empty_file},
        headers=headers,
    )
    assert res.status_code == 400
    assert "empty (0 bytes)" in res.json()["detail"].lower()


def test_transcription_failure_halts_pipeline(db_session):
    """Test transcription failure marks meeting FAILED and prevents AI analysis job from executing."""
    user = auth_service.register_user(db_session, "haltpipeline@example.com", "password123")
    meeting = Meeting(
        title="Halt Pipeline Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        audio_file_path=None,  # missing audio path triggers failure
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    job = job_processor.enqueue_and_process(db_session, JobType.TRANSCRIPTION, meeting.id)

    assert job.status == JobStatus.FAILED
    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.FAILED

    # Verify no AI Analysis jobs were enqueued for this meeting
    ai_jobs = db_session.query(Job).filter(
        Job.meeting_id == meeting.id, Job.job_type == JobType.AI_ANALYSIS
    ).all()
    assert len(ai_jobs) == 0


def test_malformed_gemini_output_handling(db_session):
    """Test malformed JSON output from Gemini raises exception and transitions status cleanly without corrupting DB."""
    user = auth_service.register_user(db_session, "malformed@example.com", "password123")
    meeting = Meeting(
        title="Malformed JSON Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.TRANSCRIBED,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.flush()

    segment = TranscriptSegment(
        meeting_id=meeting.id,
        sequence_number=1,
        start_time_ms=0,
        end_time_ms=5000,
        text="Discussed launch details.",
    )
    db_session.add(segment)
    db_session.commit()

    mock_provider = MagicMock()

    async def mock_bad_analyze(transcript_text, meeting_title):
        raise ValueError("Invalid JSON output from model")

    mock_provider.analyze.side_effect = mock_bad_analyze

    with pytest.raises(ValueError, match="Invalid JSON output from model"):
        import asyncio
        asyncio.run(meeting_intelligence_service.analyze_meeting(db_session, meeting.id, provider=mock_provider))

    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.FAILED
    assert "Invalid JSON output" in meeting.error_message

    # Verify database tables remain clean
    assert db_session.query(Summary).filter(Summary.meeting_id == meeting.id).first() is None
    assert len(db_session.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).all()) == 0


def test_pipeline_idempotency_no_duplicates(db_session):
    """Test running transcription and intelligence repeatedly replaces records atomically without duplicates."""
    user = auth_service.register_user(db_session, "idempotent_full@example.com", "password123")

    # Create mock audio file
    storage_service.storage_dir.mkdir(parents=True, exist_ok=True)
    audio_path = storage_service.storage_dir / "idempotent.mp3"
    audio_path.write_bytes(b"MOCK_AUDIO_DATA")

    meeting = Meeting(
        title="Idempotency Audit Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        audio_file_path="audio/idempotent.mp3",
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    # Process first pass
    job_processor.enqueue_and_process(db_session, JobType.TRANSCRIPTION, meeting.id)
    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.COMPLETED

    segs_count1 = db_session.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting.id).count()
    actions_count1 = db_session.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).count()
    chapters_count1 = db_session.query(Chapter).filter(Chapter.meeting_id == meeting.id).count()

    # Process second pass (retry)
    job_processor.enqueue_and_process(db_session, JobType.TRANSCRIPTION, meeting.id)
    db_session.refresh(meeting)

    segs_count2 = db_session.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting.id).count()
    actions_count2 = db_session.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).count()
    chapters_count2 = db_session.query(Chapter).filter(Chapter.meeting_id == meeting.id).count()

    assert segs_count1 == segs_count2
    assert actions_count1 == actions_count2
    assert chapters_count1 == chapters_count2


def test_pipeline_workspace_authorization_guard(unauth_client, db_session):
    """Test unauthorized users cannot trigger transcription or fetch intelligence for another user's meeting."""
    user1 = auth_service.register_user(db_session, "user_w1@example.com", "password123")
    user2 = auth_service.register_user(db_session, "user_w2@example.com", "password123")

    m1 = Meeting(
        title="User 1 Confidential Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        audio_file_path="audio/mock.mp3",
        user_id=user1.id,
    )
    db_session.add(m1)
    db_session.commit()

    from app.core.security import create_access_token
    user2_token, _ = create_access_token(str(user2.id))
    headers2 = {"Authorization": f"Bearer {user2_token}"}

    # User 2 attempts to trigger transcription on User 1's meeting
    res1 = unauth_client.post(f"/api/v1/meetings/{m1.id}/transcribe", headers=headers2)
    assert res1.status_code == 404

    # User 2 attempts to fetch intelligence on User 1's meeting
    res2 = unauth_client.get(f"/api/v1/meetings/{m1.id}/intelligence", headers=headers2)
    assert res2.status_code == 404
