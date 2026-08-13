import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from app.models.action_item import ActionItem
from app.models.chapter import Chapter
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import Participant
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment
from app.services.ai.providers import (
    MeetingIntelligenceProvider,
    MeetingIntelligenceResult,
    get_ai_provider,
)

logger = logging.getLogger(__name__)


def format_timestamp(ms: int) -> str:
    """Format millisecond timestamp into [MM:SS] format."""
    total_seconds = max(0, ms // 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


class MeetingIntelligenceService:
    """Service orchestrating AI transcript analysis and persistence into Summary, ActionItem, and Chapter tables."""

    def assemble_transcript_text(self, db: Session, meeting_id: int) -> str:
        """Fetch and format transcript segments into structured text for AI prompt context."""
        segments = (
            db.query(TranscriptSegment)
            .options(joinedload(TranscriptSegment.participant))
            .filter(TranscriptSegment.meeting_id == meeting_id)
            .order_by(TranscriptSegment.sequence_number.asc())
            .all()
        )

        if not segments:
            return ""

        formatted_lines = []
        for seg in segments:
            start_str = format_timestamp(seg.start_time_ms)
            end_str = format_timestamp(seg.end_time_ms)

            speaker = "Unknown"
            if seg.participant and seg.participant.display_name:
                speaker = seg.participant.display_name
            elif seg.participant and seg.participant.speaker_label:
                speaker = seg.participant.speaker_label

            formatted_lines.append(f"[{start_str} - {end_str}] {speaker}: {seg.text}")

        return "\n".join(formatted_lines)

    async def analyze_meeting(
        self,
        db: Session,
        meeting_id: int,
        provider: MeetingIntelligenceProvider | None = None,
    ) -> Meeting:
        """Run AI analysis on meeting transcript and atomically persist summary, action items, and chapters."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise KeyError(f"Meeting with ID {meeting_id} not found.")

        valid_source_statuses = {
            MeetingStatus.TRANSCRIBED,
            MeetingStatus.COMPLETED,
            MeetingStatus.FAILED,
        }
        if meeting.status not in valid_source_statuses:
            raise ValueError(
                f"Meeting status is '{meeting.status}'. Must be in 'transcribed' status before running AI analysis."
            )

        transcript_text = self.assemble_transcript_text(db, meeting_id)
        if not transcript_text:
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = "No transcript segments available for AI analysis."
            db.commit()
            raise ValueError("No transcript segments available for AI analysis.")

        # Transition status to ANALYZING
        meeting.status = MeetingStatus.ANALYZING
        meeting.error_message = None
        db.commit()

        active_provider = provider or get_ai_provider()

        try:
            result: MeetingIntelligenceResult = await active_provider.analyze(
                transcript_text=transcript_text,
                meeting_title=meeting.title,
            )
        except Exception as exc:
            logger.error(f"AI Meeting Analysis failed for meeting {meeting_id}: {exc}")
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = f"AI Analysis failed: {exc}"
            db.commit()
            db.refresh(meeting)
            raise

        # --- SAFE TRANSACTIONAL ATOMIC REPLACEMENT ---

        # 1. Summary Persistence (1:1 relationship)
        key_points_json = json.dumps(result.summary.key_points)
        existing_summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
        if existing_summary:
            existing_summary.overview = result.summary.overview
            existing_summary.key_points = key_points_json
        else:
            new_summary = Summary(
                meeting_id=meeting_id,
                overview=result.summary.overview,
                key_points=key_points_json,
            )
            db.add(new_summary)

        # 2. Participant Cache for Action Item Assignment
        participant_cache: dict[str, Participant] = {}
        existing_participants = (
            db.query(Participant).filter(Participant.meeting_id == meeting_id).all()
        )
        for p in existing_participants:
            if p.speaker_label:
                participant_cache[p.speaker_label] = p
            participant_cache[p.display_name] = p

        # 3. Action Items Persistence (Delete previous, insert fresh)
        db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).delete(
            synchronize_session=False
        )

        for item_data in result.action_items:
            participant_id = None
            if item_data.speaker_label and item_data.speaker_label.strip():
                label = item_data.speaker_label.strip()
                if label not in participant_cache:
                    new_p = Participant(
                        meeting_id=meeting_id,
                        display_name=label,
                        speaker_label=label,
                        is_host=False,
                    )
                    db.add(new_p)
                    db.flush()
                    participant_cache[label] = new_p
                participant_id = participant_cache[label].id

            # Parse optional due date
            due_at = None
            if item_data.due_date:
                try:
                    due_at = datetime.fromisoformat(item_data.due_date.replace("Z", "+00:00"))
                except ValueError:
                    due_at = None

            action_item = ActionItem(
                meeting_id=meeting_id,
                participant_id=participant_id,
                description=item_data.description.strip(),
                is_completed=False,
                due_at=due_at,
            )
            db.add(action_item)

        # 4. Chapters Persistence (Delete previous, insert fresh)
        db.query(Chapter).filter(Chapter.meeting_id == meeting_id).delete(
            synchronize_session=False
        )

        sorted_chapters = sorted(result.chapters, key=lambda c: c.sequence_number)
        for seq_idx, ch_data in enumerate(sorted_chapters, start=1):
            chapter = Chapter(
                meeting_id=meeting_id,
                sequence_number=seq_idx,
                title=ch_data.title.strip(),
                summary=ch_data.summary.strip() if ch_data.summary else None,
                start_time_ms=max(0, ch_data.start_time_ms),
                end_time_ms=max(ch_data.start_time_ms, ch_data.end_time_ms) if ch_data.end_time_ms else None,
            )
            db.add(chapter)

        # Update meeting status to COMPLETED
        meeting.status = MeetingStatus.COMPLETED
        meeting.error_message = None

        db.commit()
        db.refresh(meeting)
        return meeting


meeting_intelligence_service = MeetingIntelligenceService()
