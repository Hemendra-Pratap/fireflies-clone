import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
import httpx

from app.core.middleware import correlation_id_var
from app.models.job import Job, JobStatus, JobType
from app.models.meeting import Meeting, MeetingStatus
from app.models.notification import NotificationType
from app.models.transcript_segment import TranscriptSegment
from app.services.ai.meeting_intelligence import meeting_intelligence_service
from app.services.notification_service import notification_service
from app.services.transcription_service import transcription_service

logger = logging.getLogger(__name__)

NON_RETRYABLE_EXCEPTIONS = (
    FileNotFoundError,
    KeyError,
    TypeError,
    AttributeError,
    PermissionError,
)


def is_transient_error(exc: Exception) -> bool:
    """Determine whether an exception represents a transient failure suitable for automatic retry."""
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        # 429 Too Many Requests, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout
        return exc.response.status_code in (429, 502, 503, 504)
    # Database connection locks or timeouts
    exc_str = str(exc).lower()
    if "lock" in exc_str or "deadlock" in exc_str or "timeout" in exc_str or "connection" in exc_str:
        return True
    return False


class JobProcessor:
    """Durable job processor managing background task execution, bounded retries, state transitions, and notifications."""

    def enqueue_job(
        self,
        db: Session,
        job_type: str,
        meeting_id: int,
        max_retries: int = 3,
        correlation_id: str | None = None,
    ) -> Job:
        """Create and persist a new durable Job record or return existing active job (deduplication)."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise KeyError(f"Meeting {meeting_id} does not exist.")

        eff_corr_id = correlation_id or correlation_id_var.get("")

        # Deduplication check: return existing pending or processing job if present
        stmt = select(Job).where(
            Job.job_type == job_type,
            Job.meeting_id == meeting_id,
            Job.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),
        )
        existing_job = db.scalar(stmt)
        if existing_job:
            return existing_job

        job = Job(
            job_type=job_type,
            meeting_id=meeting_id,
            status=JobStatus.PENDING,
            attempts=0,
            max_retries=max_retries,
            correlation_id=eff_corr_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def recover_stale_jobs(self, db: Session, stale_timeout_seconds: int = 300) -> int:
        """Scan and recover stale jobs stuck in PROCESSING state due to worker crashes."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=stale_timeout_seconds)

        stmt = select(Job).where(
            Job.status == JobStatus.PROCESSING,
            or_(
                Job.last_heartbeat_at < cutoff,
                Job.started_at < cutoff,
                Job.last_heartbeat_at.is_(None),
            ),
        )
        stale_jobs = db.scalars(stmt).all()
        recovered_count = 0

        for job in stale_jobs:
            meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
            if job.attempts < job.max_retries:
                logger.warning(f"Reclaiming stale job {job.id} (Meeting {job.meeting_id}) after worker timeout.")
                job.status = JobStatus.PENDING
                job.error_message = f"Reclaimed after worker crash/timeout (attempt {job.attempts}/{job.max_retries})."
                recovered_count += 1
            else:
                logger.error(f"Failing stale job {job.id} (Meeting {job.meeting_id}) after retry exhaustion.")
                job.status = JobStatus.FAILED
                job.error_message = "Failed after worker crash and retry exhaustion."
                if meeting:
                    meeting.status = MeetingStatus.FAILED
                    meeting.error_message = "Processing failed due to worker timeout."
            db.commit()

        return recovered_count

    def run_job(self, db: Session, job_id: int, worker_id: str = "worker-1") -> Job:
        """Execute job logic with bounded retry loop, deterministic status updates, and notification triggers."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise KeyError(f"Job with ID {job_id} not found.")

        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        if not meeting:
            job.status = JobStatus.FAILED
            job.error_message = f"Meeting {job.meeting_id} not found."
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return job

        now = datetime.now(timezone.utc)
        job.attempts += 1
        job.status = JobStatus.PROCESSING
        job.started_at = now
        job.last_heartbeat_at = now
        job.worker_id = worker_id
        if not job.correlation_id:
            job.correlation_id = correlation_id_var.get("")
        db.commit()

        try:
            if job.job_type == JobType.TRANSCRIPTION:
                asyncio.run(transcription_service.transcribe_meeting(db, job.meeting_id))
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = None
                db.commit()

                # Automatically chain AI analysis job upon successful transcription
                ai_job = self.enqueue_job(db, JobType.AI_ANALYSIS, job.meeting_id)
                return self.run_job(db, ai_job.id, worker_id=worker_id)

            elif job.job_type == JobType.AI_ANALYSIS:
                asyncio.run(meeting_intelligence_service.analyze_meeting(db, job.meeting_id))
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = None
                db.commit()

                # Trigger meeting completion notification if user_id is present
                if meeting.user_id:
                    notification_service.create_notification(
                        db=db,
                        user_id=meeting.user_id,
                        notification_type=NotificationType.MEETING_COMPLETED,
                        title="Meeting Processing Completed",
                        message=f"Meeting '{meeting.title}' has been successfully transcribed and analyzed.",
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                    )

                return job

        except Exception as exc:
            logger.error(f"Error processing job {job.id} (attempt {job.attempts}/{job.max_retries}): {exc}")

            # Check if exception is permanent/non-retryable or transient
            is_perm = isinstance(exc, NON_RETRYABLE_EXCEPTIONS) or (
                isinstance(exc, ValueError)
                and ("GEMINI_API_KEY" in str(exc) or "empty transcript" in str(exc) or "no uploaded audio" in str(exc))
            )
            is_transient = is_transient_error(exc)

            if is_perm or not is_transient or job.attempts >= job.max_retries:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = f"Failed after {job.attempts} attempt(s): {exc}"

                # Ensure meeting status is set to FAILED
                meeting.status = MeetingStatus.FAILED
                meeting.error_message = f"Processing failed: {exc}"
                db.commit()

                # Trigger meeting failure notification if user_id is present
                if meeting.user_id:
                    notification_service.create_notification(
                        db=db,
                        user_id=meeting.user_id,
                        notification_type=NotificationType.MEETING_FAILED,
                        title="Meeting Processing Failed",
                        message=f"Processing for meeting '{meeting.title}' failed: {exc}",
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                    )
            else:
                # Mark PENDING for transient retry attempt
                job.status = JobStatus.PENDING
                job.error_message = f"Transient error (attempt {job.attempts}/{job.max_retries}): {exc}"
                db.commit()
                # Execute transient retry immediately
                return self.run_job(db, job.id, worker_id=worker_id)

        return job

    def enqueue_and_process(self, db: Session, job_type: str, meeting_id: int) -> Job:
        """Enqueue and execute job for a meeting."""
        job = self.enqueue_job(db, job_type, meeting_id)
        return self.run_job(db, job.id)


job_processor = JobProcessor()
