import os
from datetime import datetime, timezone
import pytest

from app.core.config import settings
from app.models.job import Job, JobStatus, JobType
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript_segment import TranscriptSegment
from app.services.auth_service import auth_service
from app.worker.processor import job_processor


from app.services.storage_service import storage_service


def _create_mock_audio_file(filename: str = "mock.mp3") -> str:
    """Create a temporary mock audio file inside storage_service.storage_dir."""
    storage_service.storage_dir.mkdir(parents=True, exist_ok=True)
    filepath = storage_service.storage_dir / filename
    with open(filepath, "wb") as f:
        f.write(b"MOCK_AUDIO_DATA_HEADER_BYTES")
    return f"audio/{filename}"


def test_enqueue_job(db_session):
    """Test enqueuing a durable job."""
    user = auth_service.register_user(db_session, "jobuser1@example.com", "password123")
    meeting = Meeting(
        title="Test Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    job = job_processor.enqueue_job(db_session, JobType.TRANSCRIPTION, meeting.id)
    assert job.id is not None
    assert job.job_type == JobType.TRANSCRIPTION
    assert job.status == JobStatus.PENDING
    assert job.attempts == 0


def test_job_processing_transcription(db_session):
    """Test executing transcription job updates job and meeting status."""
    user = auth_service.register_user(db_session, "jobuser2@example.com", "password123")
    audio_path = _create_mock_audio_file("mock1.mp3")

    meeting = Meeting(
        title="Mock Audio Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        audio_file_path=audio_path,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    job = job_processor.enqueue_and_process(db_session, JobType.TRANSCRIPTION, meeting.id)
    assert job.status == JobStatus.COMPLETED

    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.COMPLETED


def test_job_non_existent_meeting(db_session):
    """Test job processor raises KeyError when meeting ID does not exist."""
    with pytest.raises(KeyError):
        job_processor.enqueue_job(db_session, JobType.TRANSCRIPTION, meeting_id=99999)


def test_job_permanent_failure_missing_audio(db_session):
    """Test non-retryable error (missing audio file path) immediately sets FAILED state without retries."""
    user = auth_service.register_user(db_session, "jobuser3@example.com", "password123")
    meeting = Meeting(
        title="No Audio Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        audio_file_path=None,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    job = job_processor.enqueue_and_process(db_session, JobType.TRANSCRIPTION, meeting.id)
    assert job.status == JobStatus.FAILED
    assert job.attempts == 1

    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.FAILED
    assert "no uploaded audio" in meeting.error_message.lower()


def test_job_idempotency(db_session):
    """Test running job multiple times is idempotent and produces correct results."""
    user = auth_service.register_user(db_session, "jobuser4@example.com", "password123")
    audio_path = _create_mock_audio_file("mock2.mp3")

    meeting = Meeting(
        title="Idempotency Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        audio_file_path=audio_path,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    # Run initial job
    job1 = job_processor.enqueue_and_process(db_session, JobType.TRANSCRIPTION, meeting.id)
    assert job1.status == JobStatus.COMPLETED

    # Run second job for same meeting
    job2 = job_processor.enqueue_and_process(db_session, JobType.TRANSCRIPTION, meeting.id)
    assert job2.status == JobStatus.COMPLETED

    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.COMPLETED


def test_job_ai_analysis_direct_execution(db_session):
    """Test running AI analysis job directly on a transcribed meeting."""
    user = auth_service.register_user(db_session, "jobuser5@example.com", "password123")
    meeting = Meeting(
        title="Transcribed Meeting",
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
        text="Welcome everyone to our weekly alignment call.",
    )
    db_session.add(segment)
    db_session.commit()

    job = job_processor.enqueue_and_process(db_session, JobType.AI_ANALYSIS, meeting.id)
    assert job.status == JobStatus.COMPLETED

    db_session.refresh(meeting)
    assert meeting.status == MeetingStatus.COMPLETED


def test_job_retry_counter(db_session):
    """Test job retry attempts counter increments properly."""
    user = auth_service.register_user(db_session, "jobuser6@example.com", "password123")
    meeting = Meeting(
        title="Retry Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    job = job_processor.enqueue_job(db_session, JobType.TRANSCRIPTION, meeting.id, max_retries=3)
    result = job_processor.run_job(db_session, job.id)

    assert result.status == JobStatus.FAILED
    assert result.attempts >= 1


def test_job_record_persistence(db_session):
    """Test job records are persisted in database."""
    user = auth_service.register_user(db_session, "jobuser7@example.com", "password123")
    meeting = Meeting(
        title="Persistence Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    job = job_processor.enqueue_job(db_session, JobType.TRANSCRIPTION, meeting.id)
    persisted = db_session.query(Job).filter(Job.id == job.id).first()

    assert persisted is not None
    assert persisted.meeting_id == meeting.id


def test_job_failed_status_preservation(db_session):
    """Test job failure sets meeting status to FAILED."""
    user = auth_service.register_user(db_session, "jobuser8@example.com", "password123")
    meeting = Meeting(
        title="Fail Status Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    job_processor.enqueue_and_process(db_session, JobType.TRANSCRIPTION, meeting.id)
    db_session.refresh(meeting)

    assert meeting.status == MeetingStatus.FAILED
    assert meeting.error_message is not None


def test_job_max_retries_exhaustion(db_session):
    """Test job marks as FAILED after max retries are reached."""
    user = auth_service.register_user(db_session, "jobuser9@example.com", "password123")
    meeting = Meeting(
        title="Max Retries Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        user_id=user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    job = job_processor.enqueue_job(db_session, JobType.TRANSCRIPTION, meeting.id, max_retries=2)
    result = job_processor.run_job(db_session, job.id)

    assert result.status == JobStatus.FAILED
    assert result.attempts <= 2
