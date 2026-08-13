from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class SummaryResult(BaseModel):
    overview: str = Field(..., min_length=1, description="High-level executive summary of the meeting")
    key_points: list[str] = Field(default_factory=list, description="List of key discussion points")


class ActionItemResult(BaseModel):
    description: str = Field(..., min_length=1, description="Action item task description")
    speaker_label: str | None = Field(None, description="Assigned participant name or speaker label")
    due_date: str | None = Field(None, description="Inferred due date (e.g. ISO string or textual date)")
    priority: str | None = Field(None, description="Priority level (e.g. high, medium, low)")


class ChapterResult(BaseModel):
    sequence_number: int = Field(..., ge=1, description="1-indexed chapter sequence number")
    title: str = Field(..., min_length=1, description="Topic chapter title")
    summary: str | None = Field(None, description="Chapter topic summary")
    start_time_ms: int = Field(..., ge=0, description="Chapter start offset in milliseconds")
    end_time_ms: int | None = Field(None, ge=0, description="Chapter end offset in milliseconds")


class MeetingIntelligenceResult(BaseModel):
    summary: SummaryResult
    action_items: list[ActionItemResult] = Field(default_factory=list)
    chapters: list[ChapterResult] = Field(default_factory=list)


class MeetingIntelligenceProvider(ABC):
    """Abstract Base Class for AI Meeting Intelligence Providers."""

    @abstractmethod
    async def analyze(
        self,
        transcript_text: str,
        meeting_title: str | None = None,
    ) -> MeetingIntelligenceResult:
        """Process formatted meeting transcript and return structured intelligence."""
        pass
