from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class MeetingStatus:
    CREATED = "created"
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class Meeting(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meetings"
    __table_args__ = (Index("ix_meetings_created_at", "created_at"),)

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="completed",
        server_default="completed",
        index=True,
    )
    audio_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    audio_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    audio_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    participants = relationship(
        "Participant",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    transcript_segments = relationship(
        "TranscriptSegment",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TranscriptSegment.sequence_number",
    )
    summary = relationship(
        "Summary",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
        single_parent=True,
    )
    action_items = relationship(
        "ActionItem",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chapters = relationship(
        "Chapter",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Chapter.sequence_number",
    )
