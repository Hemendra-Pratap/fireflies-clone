from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class CalendarEventStatus:
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    TENTATIVE = "tentative"


class CalendarEvent(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        UniqueConstraint(
            "calendar_connection_id",
            "external_event_id",
            name="uq_calendar_event_connection_external_id",
        ),
    )

    calendar_connection_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("calendar_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    timezone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default="UTC",
    )
    organizer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attendees_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="confirmed",
        server_default="confirmed",
    )
    meeting_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("meetings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    connection = relationship("CalendarConnection", back_populates="events")
    workspace = relationship("Workspace", backref="calendar_events")
    user = relationship("User", backref="calendar_events")
    meeting = relationship("Meeting", backref="calendar_event", uselist=False)
