import asyncio
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.action_item import ActionItem
from app.models.chapter import Chapter
from app.models.meeting import MeetingStatus
from app.models.participant import Participant
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment
from app.schemas.intelligence import (
    ActionItemRead,
    ChapterRead,
    MeetingIntelligenceRead,
    ParticipantRead,
    SummaryRead,
    TranscriptSegmentRead,
)
from app.schemas.meeting import (
    MeetingCreate,
    MeetingListResponse,
    MeetingRead,
    MeetingStatusRead,
    MeetingUpdate,
)
from app.services.ai.meeting_intelligence import meeting_intelligence_service
from app.services.meeting_service import meeting_service
from app.services.storage_service import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    storage_service,
)
from app.services.transcription_service import transcription_service

router = APIRouter()


def _run_transcription_in_background(meeting_id: int) -> None:
    """Worker function for running async transcription in background thread."""
    db = SessionLocal()
    try:
        asyncio.run(transcription_service.transcribe_meeting(db, meeting_id))
    except Exception:
        pass
    finally:
        db.close()


def _run_ai_analysis_in_background(meeting_id: int) -> None:
    """Worker function for running async AI Meeting Intelligence in background thread."""
    db = SessionLocal()
    try:
        asyncio.run(meeting_intelligence_service.analyze_meeting(db, meeting_id))
    except Exception:
        pass
    finally:
        db.close()


@router.post(
    "",
    response_model=MeetingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new meeting",
)
def create_meeting(
    meeting_in: MeetingCreate,
    db: Session = Depends(get_db),
) -> MeetingRead:
    """Create a new meeting record in the database."""
    meeting = meeting_service.create(db, meeting_in)
    return MeetingRead.model_validate(meeting)


@router.get(
    "",
    response_model=MeetingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List meetings with pagination and search",
)
def list_meetings(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status (e.g. completed)"),
    search: str | None = Query(None, description="Search in title"),
    db: Session = Depends(get_db),
) -> MeetingListResponse:
    """List meetings with pagination, optional status filtering, and title search."""
    items, total = meeting_service.list(
        db, page=page, size=size, status=status, search=search
    )
    items_read = [MeetingRead.model_validate(item) for item in items]
    return MeetingListResponse.create(
        items=items_read, total=total, page=page, size=size
    )


@router.get(
    "/{meeting_id}",
    response_model=MeetingRead,
    status_code=status.HTTP_200_OK,
    summary="Get meeting by ID",
)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> MeetingRead:
    """Retrieve details of a single meeting by ID."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    return MeetingRead.model_validate(meeting)


@router.patch(
    "/{meeting_id}",
    response_model=MeetingRead,
    status_code=status.HTTP_200_OK,
    summary="Update a meeting",
)
def update_meeting(
    meeting_id: int,
    meeting_in: MeetingUpdate,
    db: Session = Depends(get_db),
) -> MeetingRead:
    """Perform a partial update on an existing meeting."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    updated_meeting = meeting_service.update(db, meeting, meeting_in)
    return MeetingRead.model_validate(updated_meeting)


@router.get(
    "/{meeting_id}/status",
    response_model=MeetingStatusRead,
    status_code=status.HTTP_200_OK,
    summary="Get meeting processing status",
)
def get_meeting_status(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> MeetingStatusRead:
    """Retrieve current processing status and optional error message of a meeting."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    return MeetingStatusRead.model_validate(meeting)


@router.post(
    "/{meeting_id}/audio",
    response_model=MeetingRead,
    status_code=status.HTTP_200_OK,
    summary="Upload meeting audio file",
)
async def upload_meeting_audio(
    meeting_id: int,
    file: UploadFile = File(..., description="Audio recording file"),
    db: Session = Depends(get_db),
) -> MeetingRead:
    """Upload an audio file for a meeting, persist to storage, and update processing status."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    # Validate file presence
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload",
        )

    # Validate MIME type and extension
    content_type = file.content_type.lower() if file.content_type else ""
    safe_name = Path(file.filename).name
    ext = Path(safe_name).suffix.lower()

    if content_type not in ALLOWED_MIME_TYPES and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{content_type or ext}'. Allowed types: MP3, WAV, M4A, OGG, WEBM, MP4, AAC, FLAC.",
        )

    # Persist file using storage service
    try:
        relative_path, safe_filename, size_bytes = await storage_service.save_file(file)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist audio file: {exc}",
        )

    # Persist metadata to DB; if DB update fails, clean up stored file
    try:
        updated_meeting = meeting_service.attach_audio(
            db,
            meeting,
            audio_file_path=relative_path,
            audio_filename=safe_filename,
            audio_mime_type=content_type or "audio/mpeg",
            audio_size_bytes=size_bytes,
        )
    except Exception:
        storage_service.delete_file(relative_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update database with audio metadata",
        )

    return MeetingRead.model_validate(updated_meeting)


@router.post(
    "/{meeting_id}/transcribe",
    response_model=MeetingRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger or retry meeting transcription",
)
def trigger_transcription(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MeetingRead:
    """Trigger or retry audio transcription for a meeting in the background."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    if not meeting.audio_file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting has no uploaded audio file",
        )

    if meeting.status == MeetingStatus.TRANSCRIBING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transcription is already in progress",
        )

    updated_meeting = meeting_service.update_status(db, meeting, MeetingStatus.TRANSCRIBING)
    background_tasks.add_task(_run_transcription_in_background, meeting_id)
    return MeetingRead.model_validate(updated_meeting)


@router.post(
    "/{meeting_id}/analyze",
    response_model=MeetingRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger AI meeting intelligence analysis",
)
def trigger_ai_analysis(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MeetingRead:
    """Trigger or retry AI analysis for a meeting in the background."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    valid_statuses = {MeetingStatus.TRANSCRIBED, MeetingStatus.COMPLETED, MeetingStatus.FAILED}
    if meeting.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Meeting status is '{meeting.status}'. Must be transcribed before running AI analysis.",
        )

    if meeting.status == MeetingStatus.ANALYZING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI Analysis is already in progress for this meeting",
        )

    updated_meeting = meeting_service.update_status(db, meeting, MeetingStatus.ANALYZING)
    background_tasks.add_task(_run_ai_analysis_in_background, meeting_id)
    return MeetingRead.model_validate(updated_meeting)


@router.get(
    "/{meeting_id}/summary",
    response_model=SummaryRead,
    status_code=status.HTTP_200_OK,
    summary="Get meeting summary",
)
def get_meeting_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> SummaryRead:
    """Retrieve AI-generated summary for a meeting."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting summary not found")

    return SummaryRead.model_validate(summary)


@router.get(
    "/{meeting_id}/action-items",
    response_model=list[ActionItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get meeting action items",
)
def get_meeting_action_items(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> list[ActionItemRead]:
    """Retrieve AI-extracted action items for a meeting."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    return [ActionItemRead.model_validate(item) for item in items]


@router.get(
    "/{meeting_id}/chapters",
    response_model=list[ChapterRead],
    status_code=status.HTTP_200_OK,
    summary="Get meeting chapters",
)
def get_meeting_chapters(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> list[ChapterRead]:
    """Retrieve topic chapters for a meeting."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    chapters = (
        db.query(Chapter)
        .filter(Chapter.meeting_id == meeting_id)
        .order_by(Chapter.sequence_number.asc())
        .all()
    )
    return [ChapterRead.model_validate(ch) for ch in chapters]


@router.get(
    "/{meeting_id}/transcript",
    response_model=list[TranscriptSegmentRead],
    status_code=status.HTTP_200_OK,
    summary="Get meeting transcript segments",
)
def get_meeting_transcript(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> list[TranscriptSegmentRead]:
    """Retrieve ordered transcript segments for a meeting."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.sequence_number.asc())
        .all()
    )
    return [TranscriptSegmentRead.model_validate(seg) for seg in segments]


@router.get(
    "/{meeting_id}/intelligence",
    response_model=MeetingIntelligenceRead,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated meeting intelligence",
)
def get_meeting_intelligence(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> MeetingIntelligenceRead:
    """Retrieve aggregated meeting intelligence (meeting, summary, action items, chapters, participants, transcript)."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    summary_obj = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
    summary_read = SummaryRead.model_validate(summary_obj) if summary_obj else None

    action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    action_items_read = [ActionItemRead.model_validate(item) for item in action_items]

    chapters = (
        db.query(Chapter)
        .filter(Chapter.meeting_id == meeting_id)
        .order_by(Chapter.sequence_number.asc())
        .all()
    )
    chapters_read = [ChapterRead.model_validate(ch) for ch in chapters]

    participants = db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
    participants_read = [ParticipantRead.model_validate(p) for p in participants]

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.sequence_number.asc())
        .all()
    )
    segments_read = [TranscriptSegmentRead.model_validate(seg) for seg in segments]

    return MeetingIntelligenceRead(
        meeting=MeetingRead.model_validate(meeting),
        summary=summary_read,
        action_items=action_items_read,
        chapters=chapters_read,
        participants=participants_read,
        transcript_segments=segments_read,
    )


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a meeting",
)
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a meeting by ID and cascade child records."""
    meeting = meeting_service.get_by_id(db, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    # If meeting has an attached audio file, delete it from storage
    if meeting.audio_file_path:
        storage_service.delete_file(meeting.audio_file_path)
    meeting_service.delete(db, meeting)
