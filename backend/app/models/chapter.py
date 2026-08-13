from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class Chapter(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("meeting_id", "sequence_number", name="uq_chapters_meeting_sequence"),
        CheckConstraint("start_time_ms >= 0", name="ck_chapters_start_nonnegative"),
        CheckConstraint(
            "end_time_ms IS NULL OR end_time_ms >= start_time_ms",
            name="ck_chapters_end_after_start",
        ),
        Index("ix_chapters_meeting_id_sequence_number", "meeting_id", "sequence_number"),
        Index("ix_chapters_meeting_id_start_time_ms", "meeting_id", "start_time_ms"),
    )

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="chapters")
