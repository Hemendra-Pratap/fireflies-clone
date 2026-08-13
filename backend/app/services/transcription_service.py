import logging
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import Participant
from app.models.transcript_segment import TranscriptSegment
from app.services.storage_service import storage_service
from app.services.transcription_provider import (
    TranscriptionProvider,
    TranscriptionResult,
    get_transcription_provider,
)

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service orchestrating audio transcription, participant resolution, and segment persistence."""

    async def transcribe_meeting(
        self,
        db: Session,
        meeting_id: int,
        provider: TranscriptionProvider | None = None,
    ) -> Meeting:
        """Run speech-to-text transcription for a meeting audio file and persist segments."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise KeyError(f"Meeting with ID {meeting_id} not found.")

        if not meeting.audio_file_path:
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = "Meeting has no uploaded audio file."
            db.commit()
            raise ValueError(f"Meeting {meeting_id} has no uploaded audio file.")

        full_audio_path = storage_service.get_full_path(meeting.audio_file_path)
        if not full_audio_path.exists():
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = "Audio file missing from storage."
            db.commit()
            raise FileNotFoundError(f"Audio file missing on disk: {full_audio_path}")

        # Update status to TRANSCRIBING before running provider
        meeting.status = MeetingStatus.TRANSCRIBING
        meeting.error_message = None
        db.commit()

        active_provider = provider or get_transcription_provider()

        try:
            result: TranscriptionResult = await active_provider.transcribe(full_audio_path)
        except Exception as exc:
            logger.error(f"Transcription failed for meeting {meeting_id}: {exc}")
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = f"Transcription failed: {exc}"
            db.commit()
            db.refresh(meeting)
            raise

        # Check for empty transcript
        valid_segments = [s for s in result.segments if s.text and s.text.strip()]
        if not valid_segments:
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = "Transcription produced an empty transcript."
            db.commit()
            db.refresh(meeting)
            raise ValueError("Transcription produced an empty transcript.")

        # Successful provider execution -> clear any existing segments for clean retry
        db.query(TranscriptSegment).filter(TranscriptSegment.meeting_id == meeting_id).delete(
            synchronize_session=False
        )

        # Participant cache to prevent duplicate inserts within this meeting
        participant_cache: dict[str, Participant] = {}
        existing_participants = (
            db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
        )
        for p in existing_participants:
            if p.speaker_label:
                participant_cache[p.speaker_label] = p
            participant_cache[p.display_name] = p

        # Sort segments deterministically by sequence_number
        sorted_segments = sorted(result.segments, key=lambda s: s.sequence_number)

        for seq_idx, seg_data in enumerate(sorted_segments, start=1):
            participant_id = None
            if seg_data.speaker_label and seg_data.speaker_label.strip():
                label = seg_data.speaker_label.strip()
                if label not in participant_cache:
                    new_participant = Participant(
                        meeting_id=meeting_id,
                        display_name=label,
                        speaker_label=label,
                        is_host=False,
                    )
                    db.add(new_participant)
                    db.flush()  # Assign ID
                    participant_cache[label] = new_participant
                participant_id = participant_cache[label].id

            # Validate timestamps
            start_ms = max(0, seg_data.start_time_ms)
            end_ms = max(start_ms, seg_data.end_time_ms)

            db_segment = TranscriptSegment(
                meeting_id=meeting_id,
                participant_id=participant_id,
                sequence_number=seq_idx,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                text=seg_data.text.strip(),
            )
            db.add(db_segment)

        # Update meeting metadata & state
        if result.duration_ms and result.duration_ms > 0:
            meeting.duration_ms = result.duration_ms
        elif sorted_segments:
            meeting.duration_ms = sorted_segments[-1].end_time_ms

        meeting.status = MeetingStatus.TRANSCRIBED
        meeting.error_message = None

        db.commit()
        db.refresh(meeting)

        logger.info(f"[TRANSCRIPTION] database persistence completed: {len(sorted_segments)} segments saved for meeting {meeting_id}")
        logger.info(f"[TRANSCRIPTION] processing completed: meeting {meeting_id} status set to TRANSCRIBED")
        return meeting


transcription_service = TranscriptionService()
