from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class Participant(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "participants"
    __table_args__ = (
        Index("ix_participants_meeting_id_display_name", "meeting_id", "display_name"),
    )

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    speaker_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_host: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    meeting = relationship("Meeting", back_populates="participants")
    transcript_segments = relationship(
        "TranscriptSegment",
        back_populates="participant",
        passive_deletes=True,
    )
    action_items = relationship(
        "ActionItem",
        back_populates="participant",
        passive_deletes=True,
    )
