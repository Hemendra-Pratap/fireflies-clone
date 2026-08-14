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
        self.model_name = model_name or settings.gemini_model or "gemini-3-flash-preview"

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

INSTRUCTIONS & CONSTRAINTS:
1. Grounding: Rely strictly on facts directly mentioned in the transcript. Do NOT hallucinate information, speakers, decisions, or commitments that are absent.
2. Executive Summary:
   - Provide a concise overview summarizing the main purpose and outcome of the meeting.
   - List 3-6 distinct key discussion points or major decisions.
3. Action Items:
   - Extract only explicit tasks, action items, or commitments assigned or agreed to during the meeting.
   - Set 'speaker_label' to the exact speaker who was assigned or took ownership, or null if unassigned.
   - Set 'due_date' ONLY if explicitly mentioned (format: YYYY-MM-DD or ISO string), or null if no deadline was stated.
   - Set 'priority' to 'high', 'medium', or 'low' based on context urgency.
4. Topic Chapters:
   - Divide the meeting into 2-6 logical sequential topic chapters.
   - Assign 1-indexed 'sequence_number' starting at 1.
   - Provide a clear, professional 'title' and a brief 1-2 sentence 'summary' for each chapter.
   - Use 'start_time_ms' and 'end_time_ms' corresponding to timestamps from the transcript segments.
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
