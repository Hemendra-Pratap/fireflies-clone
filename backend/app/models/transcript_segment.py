from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class TranscriptSegment(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "sequence_number",
            name="uq_transcript_segments_meeting_sequence",
        ),
        CheckConstraint("start_time_ms >= 0", name="ck_transcript_segments_start_nonnegative"),
        CheckConstraint(
            "end_time_ms >= start_time_ms",
            name="ck_transcript_segments_end_after_start",
        ),
        CheckConstraint("sequence_number >= 1", name="ck_transcript_segments_sequence_positive"),
        Index("ix_transcript_segments_meeting_id_sequence_number", "meeting_id", "sequence_number"),
        Index("ix_transcript_segments_meeting_id_start_time_ms", "meeting_id", "start_time_ms"),
    )

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    meeting = relationship("Meeting", back_populates="transcript_segments")
    participant = relationship("Participant", back_populates="transcript_segments")
