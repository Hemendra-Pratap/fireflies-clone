import os

from app.core.config import settings
from app.services.ai.providers.base import (
    ActionItemResult,
    ChapterResult,
    MeetingIntelligenceProvider,
    MeetingIntelligenceResult,
    SummaryResult,
)
from app.services.ai.providers.gemini import GeminiMeetingIntelligenceProvider
from app.services.ai.providers.mock import MockMeetingIntelligenceProvider


def get_ai_provider(
    provider_name: str | None = None,
    mock_raise_error: bool = False,
) -> MeetingIntelligenceProvider:
    """Factory returning configured AI Meeting Intelligence Provider."""
    name = (provider_name or os.getenv("AI_PROVIDER", "mock")).lower()
    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")

    if name == "gemini" and api_key:
        return GeminiMeetingIntelligenceProvider(api_key=api_key)

    return MockMeetingIntelligenceProvider(raise_error=mock_raise_error)


__all__ = [
    "ActionItemResult",
    "ChapterResult",
    "GeminiMeetingIntelligenceProvider",
    "MeetingIntelligenceProvider",
    "MeetingIntelligenceResult",
    "MockMeetingIntelligenceProvider",
    "SummaryResult",
    "get_ai_provider",
]
