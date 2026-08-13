from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class CalendarConnectionStatus:
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class CalendarProviderType:
    GOOGLE = "google"


class CalendarConnection(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calendar_connections"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "account_email",
            name="uq_calendar_conn_workspace_provider_email",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="google",
        server_default="google",
    )
    account_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        server_default="active",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user = relationship("User", backref="calendar_connections")
    workspace = relationship("Workspace", back_populates="calendar_connections")
    events = relationship(
        "CalendarEvent",
        back_populates="connection",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
