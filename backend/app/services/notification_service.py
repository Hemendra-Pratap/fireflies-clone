from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.models.notification import Notification, NotificationType
from app.services.workspace_service import workspace_service

logger = logging.getLogger(__name__)


class NotificationService:
    """Service orchestrating notification persistence, user/workspace authorization, and read state management."""

    def create_notification(
        self,
        db: Session,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        workspace_id: int | None = None,
        meeting_id: int | None = None,
    ) -> Notification:
        """Idempotently create and persist a notification record."""
        # Idempotency check for meeting-linked or duplicate notifications
        if meeting_id:
            stmt = select(Notification).where(
                Notification.user_id == user_id,
                Notification.meeting_id == meeting_id,
                Notification.type == notification_type,
            )
            existing = db.scalar(stmt)
            if existing:
                return existing

        notification = Notification(
            user_id=user_id,
            workspace_id=workspace_id,
            type=notification_type,
            title=title,
            message=message,
            meeting_id=meeting_id,
            read_at=None,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    def list_notifications(
        self,
        db: Session,
        user_id: int,
        workspace_id: int | None = None,
        unread_only: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Notification], int]:
        """Fetch workspace/user scoped notifications ordered by created_at DESC."""
        if workspace_id and not workspace_service.is_member(db, workspace_id, user_id):
            raise ValueError("Access denied: You are not a member of this workspace.")

        filters = [Notification.user_id == user_id]
        if workspace_id:
            filters.append(
                (Notification.workspace_id == workspace_id) | (Notification.workspace_id.is_(None))
            )
        if unread_only:
            filters.append(Notification.read_at.is_(None))

        base_query = select(Notification).where(and_(*filters))

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = db.scalar(count_stmt) or 0

        # Paginate
        offset = (page - 1) * size
        query = base_query.order_by(Notification.created_at.desc(), Notification.id.desc()).offset(offset).limit(size)
        items = list(db.scalars(query).all())

        return items, total

    def get_unread_count(self, db: Session, user_id: int, workspace_id: int | None = None) -> int:
        """Get total unread notification count for user."""
        if workspace_id and not workspace_service.is_member(db, workspace_id, user_id):
            raise ValueError("Access denied: You are not a member of this workspace.")

        filters = [Notification.user_id == user_id, Notification.read_at.is_(None)]
        if workspace_id:
            filters.append(
                (Notification.workspace_id == workspace_id) | (Notification.workspace_id.is_(None))
            )

        stmt = select(func.count(Notification.id)).where(and_(*filters))
        return db.scalar(stmt) or 0

    def mark_as_read(self, db: Session, notification_id: int, user_id: int) -> Notification:
        """Mark a single notification as read."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        notification = db.scalar(stmt)
        if not notification:
            raise KeyError(f"Notification {notification_id} not found or access denied.")

        if not notification.read_at:
            notification.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notification)

        return notification

    def mark_all_as_read(self, db: Session, user_id: int, workspace_id: int | None = None) -> int:
        """Mark all unread notifications for a user as read."""
        if workspace_id and not workspace_service.is_member(db, workspace_id, user_id):
            raise ValueError("Access denied: You are not a member of this workspace.")

        filters = [Notification.user_id == user_id, Notification.read_at.is_(None)]
        if workspace_id:
            filters.append(
                (Notification.workspace_id == workspace_id) | (Notification.workspace_id.is_(None))
            )

        stmt = select(Notification).where(and_(*filters))
        unread_notifications = db.scalars(stmt).all()

        now = datetime.now(timezone.utc)
        count = 0
        for notif in unread_notifications:
            notif.read_at = now
            count += 1

        if count > 0:
            db.commit()

        return count


notification_service = NotificationService()
