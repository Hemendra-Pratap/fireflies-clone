import json
from datetime import datetime
from pydantic import Field, field_validator

from app.schemas.base import ORMModel
from app.schemas.meeting import MeetingRead


class ParticipantRead(ORMModel):
    id: int
    meeting_id: int
    display_name: str
    speaker_label: str | None = None
    email: str | None = None
    is_host: bool = False


class TranscriptSegmentRead(ORMModel):
    id: int
    meeting_id: int
    participant_id: int | None = None
    sequence_number: int
    start_time_ms: int
    end_time_ms: int
    text: str


class SummaryRead(ORMModel):
    id: int
    meeting_id: int
    overview: str
    key_points: list[str] = Field(default_factory=list)

    @field_validator("key_points", mode="before")
    @classmethod
    def parse_key_points(cls, v: str | list[str] | None) -> list[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except Exception:
                return [v]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return []


class ActionItemRead(ORMModel):
    id: int
    meeting_id: int
    participant_id: int | None = None
    description: str
    is_completed: bool = False
    completed_at: datetime | None = None
    due_at: datetime | None = None


class ActionItemUpdate(ORMModel):
    is_completed: bool | None = None
    description: str | None = None
    due_at: datetime | None = None
    participant_id: int | None = None


class ChapterRead(ORMModel):
    id: int
    meeting_id: int
    sequence_number: int
    title: str
    summary: str | None = None
    start_time_ms: int
    end_time_ms: int | None = None


class MeetingIntelligenceRead(ORMModel):
    meeting: MeetingRead
    summary: SummaryRead | None = None
    action_items: list[ActionItemRead] = Field(default_factory=list)
    chapters: list[ChapterRead] = Field(default_factory=list)
    participants: list[ParticipantRead] = Field(default_factory=list)
    transcript_segments: list[TranscriptSegmentRead] = Field(default_factory=list)
