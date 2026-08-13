from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class NotificationType(str, Enum):
    MEETING_COMPLETED = "meeting_completed"
    MEETING_FAILED = "meeting_failed"
    UPCOMING_MEETING = "upcoming_meeting"
    CALENDAR_SYNC_FAILED = "calendar_sync_failed"
    WORKSPACE_INVITATION = "workspace_invitation"


class Notification(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_workspace_id", "workspace_id"),
        Index("ix_notifications_type", "type"),
        Index("ix_notifications_read_at", "read_at"),
        Index("ix_notifications_created_at", "created_at"),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meeting_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("meetings.id", ondelete="SET NULL"),
        nullable=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user = relationship("User", backref="notifications")
    workspace = relationship("Workspace", backref="notifications")
    meeting = relationship("Meeting", backref="notifications")
