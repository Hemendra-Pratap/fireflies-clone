from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import IntegerPrimaryKeyMixin, TimestampMixin


class Workspace(IntegerPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        Index("ix_workspaces_owner_id", "owner_id"),
        Index("ix_workspaces_created_at", "created_at"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    meetings = relationship("Meeting", back_populates="workspace")
    calendar_connections = relationship(
        "CalendarConnection",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
