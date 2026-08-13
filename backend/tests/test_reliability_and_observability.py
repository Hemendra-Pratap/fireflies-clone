import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus, JobType
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript_segment import TranscriptSegment
from app.models.user import User
from app.worker.processor import job_processor, is_transient_error
import httpx


@pytest.fixture
def sample_meeting(db_session: Session, test_user: User) -> Meeting:
    m = Meeting(
        title="Reliability Test Meeting",
        status=MeetingStatus.CREATED,
        user_id=test_user.id,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


def test_stale_job_recovery(db_session: Session, sample_meeting: Meeting):
    # Simulate worker crash: job left in PROCESSING with old heartbeat
    old_time = datetime.now(timezone.utc) - timedelta(seconds=600)
    job = Job(
        job_type=JobType.TRANSCRIPTION,
        meeting_id=sample_meeting.id,
        status=JobStatus.PROCESSING,
        attempts=1,
        max_retries=3,
        started_at=old_time,
        last_heartbeat_at=old_time,
    )
    db_session.add(job)
    db_session.commit()

    # Trigger recovery
    recovered = job_processor.recover_stale_jobs(db_session, stale_timeout_seconds=300)
    assert recovered == 1

    db_session.refresh(job)
    assert job.status == JobStatus.PENDING
    assert "Reclaimed after worker crash" in job.error_message


def test_stale_job_recovery_exhaustion(db_session: Session, sample_meeting: Meeting):
    # Simulate worker crash after max attempts
    old_time = datetime.now(timezone.utc) - timedelta(seconds=600)
    job = Job(
        job_type=JobType.TRANSCRIPTION,
        meeting_id=sample_meeting.id,
        status=JobStatus.PROCESSING,
        attempts=3,
        max_retries=3,
        started_at=old_time,
        last_heartbeat_at=old_time,
    )
    db_session.add(job)
    db_session.commit()

    recovered = job_processor.recover_stale_jobs(db_session, stale_timeout_seconds=300)
    assert recovered == 0

    db_session.refresh(job)
    db_session.refresh(sample_meeting)
    assert job.status == JobStatus.FAILED
    assert sample_meeting.status == MeetingStatus.FAILED


def test_retry_classification_transient_vs_permanent():
    assert is_transient_error(httpx.ConnectTimeout("Timeout")) is True
    res_429 = MagicMock()
    res_429.status_code = 429
    assert is_transient_error(httpx.HTTPStatusError("Rate limit", request=MagicMock(), response=res_429)) is True

    res_400 = MagicMock()
    res_400.status_code = 400
    assert is_transient_error(httpx.HTTPStatusError("Bad request", request=MagicMock(), response=res_400)) is False

    assert is_transient_error(FileNotFoundError("Missing file")) is False
    assert is_transient_error(ValueError("Invalid argument")) is False


def test_transcript_preservation_on_ai_failure(db_session: Session, sample_meeting: Meeting):
    # Set meeting as TRANSCRIBED with transcript segments
    sample_meeting.status = MeetingStatus.TRANSCRIBED
    seg = TranscriptSegment(
        meeting_id=sample_meeting.id,
        sequence_number=1,
        start_time_ms=0,
        end_time_ms=1000,
        text="Hello world transcript",
    )
    db_session.add(seg)
    db_session.commit()

    # Enqueue AI analysis job and simulate failure
    job = job_processor.enqueue_job(db_session, JobType.AI_ANALYSIS, sample_meeting.id)
    with patch("app.worker.processor.meeting_intelligence_service.analyze_meeting", side_effect=ValueError("AI model overload")):
        job_processor.run_job(db_session, job.id)

    db_session.refresh(sample_meeting)
    assert sample_meeting.status == MeetingStatus.FAILED

    # Transcript segments must remain intact!
    remaining_segs = db_session.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == sample_meeting.id).all()
    assert len(remaining_segs) == 1
    assert remaining_segs[0].text == "Hello world transcript"


def test_retry_meeting_processing_endpoint(client: TestClient, sample_meeting: Meeting, db_session: Session):
    # Attach audio to meeting
    sample_meeting.audio_file_path = "audio/sample.mp3"
    sample_meeting.status = MeetingStatus.FAILED
    db_session.commit()

    res = client.post(f"/api/v1/meetings/{sample_meeting.id}/retry")
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == MeetingStatus.TRANSCRIBING


def test_unauthorized_retry(unauth_client: TestClient, sample_meeting: Meeting):
    res = unauth_client.post(f"/api/v1/meetings/{sample_meeting.id}/retry")
    assert res.status_code == 401


def test_correlation_id_tracing(unauth_client: TestClient):
    custom_corr_id = "test-corr-id-12345"
    res = unauth_client.get("/api/v1/health", headers={"X-Correlation-ID": custom_corr_id})
    assert res.status_code == 200
    assert res.headers.get("X-Correlation-ID") == custom_corr_id


def test_consistent_api_error_responses(unauth_client: TestClient):
    res = unauth_client.get("/api/v1/meetings/999999")
    assert res.status_code in (401, 404)
    data = res.json()
    assert "detail" in data
    assert "Traceback" not in res.text
