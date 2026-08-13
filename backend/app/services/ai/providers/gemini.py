import os
from app.core.config import settings
from app.services.ai.providers.base import (
    MeetingIntelligenceProvider,
    MeetingIntelligenceResult,
)


class GeminiMeetingIntelligenceProvider(MeetingIntelligenceProvider):
    """Real AI provider utilizing the official Google GenAI SDK with structured output."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or settings.gemini_model or "gemini-2.0-flash"

    async def analyze(
        self,
        transcript_text: str,
        meeting_title: str | None = None,
    ) -> MeetingIntelligenceResult:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        if not transcript_text or not transcript_text.strip():
            raise ValueError("Transcript text is empty; cannot run AI analysis.")

        from google import genai

        client = genai.Client(api_key=self.api_key)

        prompt = f"""
You are an expert AI meeting assistant. Analyze the following meeting transcript and generate structured meeting intelligence.

Meeting Title: {meeting_title or 'Untitled Meeting'}

TRANSCRIPT:
{transcript_text}

INSTRUCTIONS:
1. Provide a clear high-level executive summary overview and a list of key points.
2. Extract all concrete action items, identifying speaker labels, due dates, and priorities where inferable.
3. Divide the meeting into logical sequential topic chapters with titles, summaries, and start/end millisecond timestamps.
"""

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": MeetingIntelligenceResult,
            },
        )

        if not response.text:
            raise RuntimeError("Empty response received from Gemini API.")

        return MeetingIntelligenceResult.model_validate_json(response.text)
