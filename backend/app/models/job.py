from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class JobType:
    TRANSCRIPTION = "transcription"
    AI_ANALYSIS = "ai_analysis"


class JobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_meeting_id", "meeting_id"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_created_at", "created_at"),
        Index("ix_jobs_last_heartbeat", "last_heartbeat_at"),
    )

    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    meeting_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=JobStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    meeting = relationship("Meeting")
