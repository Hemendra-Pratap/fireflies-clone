from datetime import datetime, timezone

from app.models.action_item import ActionItem
from app.models.chapter import Chapter
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment


def test_meeting_persistence(db_session):
    """Verify Meeting record insertion and field persistence."""
    now = datetime.now(timezone.utc)
    meeting = Meeting(
        title="Engineering Sync",
        source_name="Zoom",
        recorded_at=now,
        duration_ms=1800000,
        status="completed",
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)

    assert meeting.id is not None
    assert meeting.title == "Engineering Sync"
    assert meeting.source_name == "Zoom"
    assert meeting.status == "completed"
    assert meeting.created_at is not None
    assert meeting.updated_at is not None


def test_participant_persistence(db_session):
    """Verify Participant record insertion and meeting relationship."""
    meeting = Meeting(title="Team Huddle", recorded_at=datetime.now(timezone.utc))
    db_session.add(meeting)
    db_session.commit()

    participant = Participant(
        meeting_id=meeting.id,
        display_name="Alice Smith",
        speaker_label="Speaker 1",
        email="alice@example.com",
        is_host=True,
    )
    db_session.add(participant)
    db_session.commit()
    db_session.refresh(participant)

    assert participant.id is not None
    assert participant.meeting_id == meeting.id
    assert participant.display_name == "Alice Smith"
    assert participant.is_host is True


def test_transcript_segment_persistence(db_session):
    """Verify TranscriptSegment record insertion and fields."""
    meeting = Meeting(title="Transcript Test", recorded_at=datetime.now(timezone.utc))
    db_session.add(meeting)
    db_session.commit()

    participant = Participant(
        meeting_id=meeting.id,
        display_name="Bob Jones",
        speaker_label="Speaker 2",
    )
    db_session.add(participant)
    db_session.commit()

    segment = TranscriptSegment(
        meeting_id=meeting.id,
        participant_id=participant.id,
        sequence_number=1,
        start_time_ms=0,
        end_time_ms=5000,
        text="Welcome to the meeting.",
    )
    db_session.add(segment)
    db_session.commit()
    db_session.refresh(segment)

    assert segment.id is not None
    assert segment.meeting_id == meeting.id
    assert segment.participant_id == participant.id
    assert segment.sequence_number == 1
    assert segment.text == "Welcome to the meeting."


def test_action_item_persistence(db_session):
    """Verify ActionItem record insertion and completion tracking."""
    meeting = Meeting(title="Action Item Test", recorded_at=datetime.now(timezone.utc))
    db_session.add(meeting)
    db_session.commit()

    participant = Participant(meeting_id=meeting.id, display_name="Charlie Brown")
    db_session.add(participant)
    db_session.commit()

    action_item = ActionItem(
        meeting_id=meeting.id,
        participant_id=participant.id,
        description="Prepare project slides for Monday",
        is_completed=False,
    )
    db_session.add(action_item)
    db_session.commit()
    db_session.refresh(action_item)

    assert action_item.id is not None
    assert action_item.meeting_id == meeting.id
    assert action_item.participant_id == participant.id
    assert action_item.description == "Prepare project slides for Monday"
    assert action_item.is_completed is False


def test_summary_persistence(db_session):
    """Verify Summary record insertion and 1-to-1 meeting relationship."""
    meeting = Meeting(title="Summary Test", recorded_at=datetime.now(timezone.utc))
    db_session.add(meeting)
    db_session.commit()

    summary = Summary(
        meeting_id=meeting.id,
        overview="Discussed Q3 roadmap and feature priorities.",
        key_points="1. Prioritize backend REST API.\n2. Fix database hygiene.",
    )
    db_session.add(summary)
    db_session.commit()
    db_session.refresh(summary)

    assert summary.id is not None
    assert summary.meeting_id == meeting.id
    assert "Q3 roadmap" in summary.overview
    assert "backend REST API" in summary.key_points


def test_chapter_persistence(db_session):
    """Verify Chapter record insertion and sequence numbers."""
    meeting = Meeting(title="Chapter Test", recorded_at=datetime.now(timezone.utc))
    db_session.add(meeting)
    db_session.commit()

    chapter = Chapter(
        meeting_id=meeting.id,
        sequence_number=1,
        title="Introduction & Agenda",
        start_time_ms=0,
        end_time_ms=60000,
        summary="Brief introduction of team members and agenda overview.",
    )
    db_session.add(chapter)
    db_session.commit()
    db_session.refresh(chapter)

    assert chapter.id is not None
    assert chapter.meeting_id == meeting.id
    assert chapter.sequence_number == 1
    assert chapter.title == "Introduction & Agenda"


def test_participant_deletion_sets_null(db_session):
    """Deleting a participant must set participant_id to NULL on dependent segments and action items."""
    meeting = Meeting(
        title="Participant Deletion Test", recorded_at=datetime.now(timezone.utc)
    )
    db_session.add(meeting)
    db_session.commit()

    participant = Participant(meeting_id=meeting.id, display_name="Eve")
    db_session.add(participant)
    db_session.commit()

    segment = TranscriptSegment(
        meeting_id=meeting.id,
        participant_id=participant.id,
        sequence_number=1,
        start_time_ms=0,
        end_time_ms=2000,
        text="Hello world",
    )
    action_item = ActionItem(
        meeting_id=meeting.id,
        participant_id=participant.id,
        description="Follow up with client",
    )
    db_session.add_all([segment, action_item])
    db_session.commit()

    # Delete participant
    db_session.delete(participant)
    db_session.commit()

    # Refresh objects from DB
    db_session.refresh(segment)
    db_session.refresh(action_item)

    assert segment.participant_id is None
    assert action_item.participant_id is None


def test_meeting_deletion_cascades(db_session):
    """Deleting a meeting must CASCADE delete all dependent participants, transcripts, summaries, action items, and chapters."""
    meeting = Meeting(
        title="Meeting Cascade Test", recorded_at=datetime.now(timezone.utc)
    )
    db_session.add(meeting)
    db_session.commit()

    participant = Participant(meeting_id=meeting.id, display_name="Dave")
    db_session.add(participant)
    db_session.commit()

    segment = TranscriptSegment(
        meeting_id=meeting.id,
        participant_id=participant.id,
        sequence_number=1,
        start_time_ms=0,
        end_time_ms=1000,
        text="Testing cascade",
    )
    action_item = ActionItem(
        meeting_id=meeting.id,
        participant_id=participant.id,
        description="Cascade test task",
    )
    summary = Summary(meeting_id=meeting.id, overview="Cascade test summary overview")
    chapter = Chapter(
        meeting_id=meeting.id,
        sequence_number=1,
        title="Cascade test chapter",
        start_time_ms=0,
    )
    db_session.add_all([segment, action_item, summary, chapter])
    db_session.commit()

    meeting_id = meeting.id
    participant_id = participant.id
    segment_id = segment.id
    action_item_id = action_item.id
    summary_id = summary.id
    chapter_id = chapter.id

    # Delete meeting
    db_session.delete(meeting)
    db_session.commit()

    # Verify all dependent records are deleted from database
    assert db_session.query(Meeting).filter(Meeting.id == meeting_id).count() == 0
    assert (
        db_session.query(Participant).filter(Participant.id == participant_id).count()
        == 0
    )
    assert (
        db_session.query(TranscriptSegment)
        .filter(TranscriptSegment.id == segment_id)
        .count()
        == 0
    )
    assert (
        db_session.query(ActionItem).filter(ActionItem.id == action_item_id).count()
        == 0
    )
    assert db_session.query(Summary).filter(Summary.id == summary_id).count() == 0
    assert db_session.query(Chapter).filter(Chapter.id == chapter_id).count() == 0
