import logging
from sqlalchemy.orm import Session

from app.models.action_item import ActionItem
from app.models.chapter import Chapter
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment
from app.models.workspace_member import WorkspaceMember
from app.schemas.search import SearchResponse, SearchResultItem

logger = logging.getLogger(__name__)


class SearchService:
    """Service handling multi-entity text search scoped strictly to authorized user workspaces."""

    def _get_user_workspace_ids(self, db: Session, user_id: int) -> list[int]:
        """Fetch all workspace IDs where user is a member."""
        memberships = db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == user_id).all()
        return [m[0] for m in memberships]

    def search(
        self,
        db: Session,
        *,
        user_id: int,
        query_str: str,
        page: int = 1,
        size: int = 20,
        status: str | None = None,
        workspace_id: int | None = None,
    ) -> SearchResponse:
        """Search across meetings, summaries, action items, chapters, transcripts, and participants."""
        if not query_str or not query_str.strip():
            return SearchResponse.create(items=[], total=0, page=page, size=size)

        pattern = f"%{query_str.strip()}%"
        user_w_ids = self._get_user_workspace_ids(db, user_id)

        # Base meeting filter for tenant security isolation
        meeting_query = db.query(Meeting)
        if workspace_id is not None:
            if workspace_id not in user_w_ids:
                return SearchResponse.create(items=[], total=0, page=page, size=size)
            meeting_query = meeting_query.filter(Meeting.workspace_id == workspace_id)
        else:
            meeting_query = meeting_query.filter(
                (Meeting.workspace_id.in_(user_w_ids)) | (Meeting.user_id == user_id)
            )

        if status:
            meeting_query = meeting_query.filter(Meeting.status == status)

        allowed_meetings = {m.id: m for m in meeting_query.all()}
        allowed_ids = list(allowed_meetings.keys())

        if not allowed_ids:
            return SearchResponse.create(items=[], total=0, page=page, size=size)

        results: list[SearchResultItem] = []

        # 1. Search Meeting Titles
        for m_id, meeting in allowed_meetings.items():
            if query_str.strip().lower() in meeting.title.lower():
                results.append(
                    SearchResultItem(
                        meeting_id=meeting.id,
                        meeting_title=meeting.title,
                        meeting_status=meeting.status,
                        recorded_at=meeting.recorded_at,
                        match_type="title",
                        matched_text=meeting.title,
                        relevance=2.0,
                    )
                )

        # 2. Search Summaries
        summaries = (
            db.query(Summary)
            .filter(
                Summary.meeting_id.in_(allowed_ids),
                (Summary.overview.ilike(pattern)) | (Summary.key_points.ilike(pattern)),
            )
            .all()
        )
        for summ in summaries:
            meeting = allowed_meetings[summ.meeting_id]
            matched_snippet = summ.overview if query_str.strip().lower() in summ.overview.lower() else summ.key_points
            results.append(
                SearchResultItem(
                    meeting_id=meeting.id,
                    meeting_title=meeting.title,
                    meeting_status=meeting.status,
                    recorded_at=meeting.recorded_at,
                    match_type="summary",
                    matched_text=matched_snippet[:200],
                    relevance=1.5,
                )
            )

        # 3. Search Action Items
        action_items = (
            db.query(ActionItem)
            .filter(
                ActionItem.meeting_id.in_(allowed_ids),
                ActionItem.description.ilike(pattern),
            )
            .all()
        )
        for ai in action_items:
            meeting = allowed_meetings[ai.meeting_id]
            results.append(
                SearchResultItem(
                    meeting_id=meeting.id,
                    meeting_title=meeting.title,
                    meeting_status=meeting.status,
                    recorded_at=meeting.recorded_at,
                    match_type="action_item",
                    matched_text=ai.description,
                    relevance=1.4,
                )
            )

        # 4. Search Chapters
        chapters = (
            db.query(Chapter)
            .filter(
                Chapter.meeting_id.in_(allowed_ids),
                (Chapter.title.ilike(pattern)) | (Chapter.summary.ilike(pattern)),
            )
            .all()
        )
        for ch in chapters:
            meeting = allowed_meetings[ch.meeting_id]
            snippet = ch.title if query_str.strip().lower() in ch.title.lower() else (ch.summary or ch.title)
            results.append(
                SearchResultItem(
                    meeting_id=meeting.id,
                    meeting_title=meeting.title,
                    meeting_status=meeting.status,
                    recorded_at=meeting.recorded_at,
                    match_type="chapter",
                    matched_text=snippet,
                    timestamp_ms=ch.start_time_ms,
                    relevance=1.3,
                )
            )

        # 5. Search Transcript Segments
        segments = (
            db.query(TranscriptSegment)
            .filter(
                TranscriptSegment.meeting_id.in_(allowed_ids),
                TranscriptSegment.text.ilike(pattern),
            )
            .all()
        )
        for seg in segments:
            meeting = allowed_meetings[seg.meeting_id]
            results.append(
                SearchResultItem(
                    meeting_id=meeting.id,
                    meeting_title=meeting.title,
                    meeting_status=meeting.status,
                    recorded_at=meeting.recorded_at,
                    match_type="transcript",
                    matched_text=seg.text,
                    timestamp_ms=seg.start_time_ms,
                    relevance=1.2,
                )
            )

        # 6. Search Participants
        participants = (
            db.query(Participant)
            .filter(
                Participant.meeting_id.in_(allowed_ids),
                (Participant.display_name.ilike(pattern)) | (Participant.speaker_label.ilike(pattern)),
            )
            .all()
        )
        for p in participants:
            meeting = allowed_meetings[p.meeting_id]
            matched_label = p.display_name or p.speaker_label
            results.append(
                SearchResultItem(
                    meeting_id=meeting.id,
                    meeting_title=meeting.title,
                    meeting_status=meeting.status,
                    recorded_at=meeting.recorded_at,
                    match_type="participant",
                    matched_text=f"Participant: {matched_label}",
                    relevance=1.1,
                )
            )

        # Deduplicate results per meeting + match_type to ensure clean pagination
        seen_keys = set()
        unique_results = []
        for r in sorted(results, key=lambda x: (-x.relevance, x.recorded_at), reverse=True):
            key = (r.meeting_id, r.match_type, r.matched_text)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_results.append(r)

        total = len(unique_results)
        skip = (page - 1) * size
        paginated_items = unique_results[skip : skip + size]

        return SearchResponse.create(items=paginated_items, total=total, page=page, size=size)


search_service = SearchService()
