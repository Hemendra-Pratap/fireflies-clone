from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingStatus
from app.schemas.meeting import MeetingCreate, MeetingUpdate


class MeetingService:
    """Service layer handling database business logic for Meetings."""

    def create(self, db: Session, obj_in: MeetingCreate) -> Meeting:
        """Create and persist a new Meeting record."""
        meeting = Meeting(**obj_in.model_dump())
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        return meeting

    def get_by_id(self, db: Session, meeting_id: int) -> Meeting | None:
        """Fetch a single Meeting by ID."""
        return db.query(Meeting).filter(Meeting.id == meeting_id).first()

    def list(
        self,
        db: Session,
        *,
        page: int = 1,
        size: int = 20,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Meeting], int]:
        """List meetings with pagination, optional status filtering, and title search."""
        skip = (page - 1) * size
        query = db.query(Meeting)

        if status:
            query = query.filter(Meeting.status == status)

        if search:
            query = query.filter(Meeting.title.ilike(f"%{search}%"))

        total = query.count()
        items = (
            query.order_by(Meeting.created_at.desc())
            .offset(skip)
            .limit(size)
            .all()
        )

        return items, total

    def update(
        self, db: Session, db_obj: Meeting, obj_in: MeetingUpdate
    ) -> Meeting:
        """Perform a partial update on an existing Meeting."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def attach_audio(
        self,
        db: Session,
        db_obj: Meeting,
        *,
        audio_file_path: str,
        audio_filename: str,
        audio_mime_type: str,
        audio_size_bytes: int,
    ) -> Meeting:
        """Attach uploaded audio file metadata and update status to UPLOADED."""
        db_obj.audio_file_path = audio_file_path
        db_obj.audio_filename = audio_filename
        db_obj.audio_mime_type = audio_mime_type
        db_obj.audio_size_bytes = audio_size_bytes
        db_obj.status = MeetingStatus.UPLOADED
        db_obj.error_message = None

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_status(
        self,
        db: Session,
        db_obj: Meeting,
        status: str,
        error_message: str | None = None,
    ) -> Meeting:
        """Update meeting processing status and optional error message."""
        db_obj.status = status
        db_obj.error_message = error_message

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: Meeting) -> None:
        """Delete a Meeting and cascade child records."""
        db.delete(db_obj)
        db.commit()


meeting_service = MeetingService()
