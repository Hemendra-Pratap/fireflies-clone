import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.action_item import ActionItem
from app.models.chapter import Chapter
from app.models.meeting import Meeting, MeetingStatus
from app.models.summary import Summary
from app.models.transcript_segment import TranscriptSegment
from app.services.ai.meeting_intelligence import meeting_intelligence_service
from app.services.ai.providers import (
    MockMeetingIntelligenceProvider,
    get_ai_provider,
)
from app.services.transcription_provider import MockTranscriptionProvider
from app.services.transcription_service import transcription_service


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def create_transcribed_meeting(client: TestClient, db_session: Session) -> dict:
    """Helper creating a meeting with uploaded audio and transcribed segments."""
    # 1. Create meeting
    payload = {
        "title": "AI Intelligence Test Meeting",
        "source_name": "Zoom",
        "recorded_at": "2026-08-13T10:00:00Z",
        "duration_ms": 30000,
        "status": MeetingStatus.CREATED,
    }
    m_res = client.post("/api/v1/meetings", json=payload)
    assert m_res.status_code == 201
    meeting = m_res.json()
    meeting_id = meeting["id"]

    # 2. Upload audio
    dummy_audio = b"ID3\x04\x00\x00\x00\x00\x00\x00Sample MP3 Data For AI Intelligence Test"
    files = {"file": ("test_ai.mp3", dummy_audio, "audio/mpeg")}
    upload_res = client.post(f"/api/v1/meetings/{meeting_id}/audio", files=files)
    assert upload_res.status_code == 200

    # 3. Transcribe meeting using MockTranscriptionProvider
    trans_provider = MockTranscriptionProvider(include_speakers=True)
    await transcription_service.transcribe_meeting(db_session, meeting_id, provider=trans_provider)

    # Verify status is TRANSCRIBED
    db_m = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
    assert db_m.status == MeetingStatus.TRANSCRIBED

    return upload_res.json()


def test_ai_provider_factory_default() -> None:
    provider = get_ai_provider("mock")
    assert isinstance(provider, MockMeetingIntelligenceProvider)


@pytest.mark.anyio
async def test_assemble_transcript_text(db_session: Session, client: TestClient) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    text = meeting_intelligence_service.assemble_transcript_text(db_session, meeting_id)
    assert "Speaker 1: Welcome everyone to today's meeting." in text
    assert "Speaker 2: Thanks for having me." in text
    assert "[00:00 - 00:05]" in text


@pytest.mark.anyio
async def test_analyze_meeting_success(db_session: Session, client: TestClient) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    provider = MockMeetingIntelligenceProvider()
    updated_m = await meeting_intelligence_service.analyze_meeting(
        db_session, meeting_id, provider=provider
    )

    assert updated_m.status == MeetingStatus.COMPLETED
    assert updated_m.error_message is None

    # Verify Summary persistence
    summary = db_session.query(Summary).filter(Summary.meeting_id == meeting_id).first()
    assert summary is not None
    assert "Executive summary" in summary.overview
    assert "FastAPI" in summary.key_points

    # Verify Action Items persistence
    action_items = db_session.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    assert len(action_items) == 2
    assert action_items[0].description == "Finalize the engineering action items before Friday."
    assert action_items[0].participant_id is not None

    # Verify Chapters persistence
    chapters = db_session.query(Chapter).filter(Chapter.meeting_id == meeting_id).all()
    assert len(chapters) == 2
    assert chapters[0].title == "Introduction & Roadmap Review"
    assert chapters[0].sequence_number == 1


@pytest.mark.anyio
async def test_analyze_meeting_failure(db_session: Session, client: TestClient) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    provider = MockMeetingIntelligenceProvider(raise_error=True)

    with pytest.raises(RuntimeError):
        await meeting_intelligence_service.analyze_meeting(db_session, meeting_id, provider=provider)

    db_m = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
    assert db_m.status == MeetingStatus.FAILED
    assert db_m.error_message is not None
    assert "Simulated Gemini AI provider analysis error" in db_m.error_message


@pytest.mark.anyio
async def test_retry_analysis_replaces_records_without_duplication(
    db_session: Session, client: TestClient
) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    provider = MockMeetingIntelligenceProvider()
    # First analysis run
    await meeting_intelligence_service.analyze_meeting(db_session, meeting_id, provider=provider)

    # Second analysis run (retry)
    await meeting_intelligence_service.analyze_meeting(db_session, meeting_id, provider=provider)

    summaries = db_session.query(Summary).filter(Summary.meeting_id == meeting_id).all()
    assert len(summaries) == 1

    action_items = db_session.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    assert len(action_items) == 2

    chapters = db_session.query(Chapter).filter(Chapter.meeting_id == meeting_id).all()
    assert len(chapters) == 2


@pytest.mark.anyio
async def test_trigger_ai_analysis_endpoint(client: TestClient, db_session: Session) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    res = client.post(f"/api/v1/meetings/{meeting_id}/analyze")
    assert res.status_code == 202
    data = res.json()
    assert data["id"] == meeting_id
    assert data["status"] == MeetingStatus.ANALYZING


def test_trigger_ai_analysis_invalid_status(client: TestClient) -> None:
    # Create meeting without transcribing
    payload = {
        "title": "Untranscribed Meeting",
        "recorded_at": "2026-08-13T10:00:00Z",
        "status": MeetingStatus.CREATED,
    }
    m_res = client.post("/api/v1/meetings", json=payload)
    m_id = m_res.json()["id"]

    res = client.post(f"/api/v1/meetings/{m_id}/analyze")
    assert res.status_code == 400
    assert "Must be transcribed before running AI analysis" in res.json()["detail"]


@pytest.mark.anyio
async def test_get_summary_endpoint(client: TestClient, db_session: Session) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    provider = MockMeetingIntelligenceProvider()
    await meeting_intelligence_service.analyze_meeting(db_session, meeting_id, provider=provider)

    res = client.get(f"/api/v1/meetings/{meeting_id}/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["meeting_id"] == meeting_id
    assert "Executive summary" in data["overview"]
    assert isinstance(data["key_points"], list)
    assert len(data["key_points"]) == 3


@pytest.mark.anyio
async def test_get_action_items_endpoint(client: TestClient, db_session: Session) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    provider = MockMeetingIntelligenceProvider()
    await meeting_intelligence_service.analyze_meeting(db_session, meeting_id, provider=provider)

    res = client.get(f"/api/v1/meetings/{meeting_id}/action-items")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["description"] == "Finalize the engineering action items before Friday."


@pytest.mark.anyio
async def test_get_chapters_endpoint(client: TestClient, db_session: Session) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    provider = MockMeetingIntelligenceProvider()
    await meeting_intelligence_service.analyze_meeting(db_session, meeting_id, provider=provider)

    res = client.get(f"/api/v1/meetings/{meeting_id}/chapters")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["title"] == "Introduction & Roadmap Review"


@pytest.mark.anyio
async def test_get_transcript_endpoint(client: TestClient, db_session: Session) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    res = client.get(f"/api/v1/meetings/{meeting_id}/transcript")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert data[0]["text"] == "Welcome everyone to today's meeting."


@pytest.mark.anyio
async def test_get_intelligence_aggregated_endpoint(client: TestClient, db_session: Session) -> None:
    meeting = await create_transcribed_meeting(client, db_session)
    meeting_id = meeting["id"]

    provider = MockMeetingIntelligenceProvider()
    await meeting_intelligence_service.analyze_meeting(db_session, meeting_id, provider=provider)

    res = client.get(f"/api/v1/meetings/{meeting_id}/intelligence")
    assert res.status_code == 200
    data = res.json()

    assert data["meeting"]["id"] == meeting_id
    assert data["meeting"]["status"] == MeetingStatus.COMPLETED
    assert data["summary"] is not None
    assert len(data["action_items"]) == 2
    assert len(data["chapters"]) == 2
    assert len(data["participants"]) == 2
    assert len(data["transcript_segments"]) == 3


def test_intelligence_endpoints_404(client: TestClient) -> None:
    assert client.get("/api/v1/meetings/99999/summary").status_code == 404
    assert client.get("/api/v1/meetings/99999/action-items").status_code == 404
    assert client.get("/api/v1/meetings/99999/chapters").status_code == 404
    assert client.get("/api/v1/meetings/99999/transcript").status_code == 404
    assert client.get("/api/v1/meetings/99999/intelligence").status_code == 404


def test_parse_due_date_helper() -> None:
    from app.services.ai.meeting_intelligence import parse_due_date

    assert parse_due_date(None) is None
    assert parse_due_date("") is None
    assert parse_due_date("invalid date string") is None

    # Test YYYY-MM-DD
    dt1 = parse_due_date("2026-08-20")
    assert dt1 is not None
    assert dt1.year == 2026 and dt1.month == 8 and dt1.day == 20

    # Test ISO format
    dt2 = parse_due_date("2026-08-20T14:30:00Z")
    assert dt2 is not None
    assert dt2.year == 2026 and dt2.hour == 14
