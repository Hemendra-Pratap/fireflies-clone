from app.services.ai.providers.base import (
    ActionItemResult,
    ChapterResult,
    MeetingIntelligenceProvider,
    MeetingIntelligenceResult,
    SummaryResult,
)


class MockMeetingIntelligenceProvider(MeetingIntelligenceProvider):
    """Deterministic mock AI provider for testing and development fallback."""

    def __init__(self, raise_error: bool = False):
        self.raise_error = raise_error

    async def analyze(
        self,
        transcript_text: str,
        meeting_title: str | None = None,
    ) -> MeetingIntelligenceResult:
        if self.raise_error:
            raise RuntimeError("Simulated Gemini AI provider analysis error.")

        if not transcript_text or not transcript_text.strip():
            return MeetingIntelligenceResult(
                summary=SummaryResult(
                    overview="No transcript content was available for analysis.",
                    key_points=["Empty transcript"],
                ),
                action_items=[],
                chapters=[],
            )

        title = meeting_title or "Meeting"

        return MeetingIntelligenceResult(
            summary=SummaryResult(
                overview=f"Executive summary for '{title}'. The team reviewed architecture, backend setup, and action items.",
                key_points=[
                    "Reviewed project architecture and backend roadmap.",
                    "Confirmed adoption of FastAPI and SQLAlchemy 2.0 ORM.",
                    "Agreed on key action items for the upcoming iteration.",
                ],
            ),
            action_items=[
                ActionItemResult(
                    description="Finalize the engineering action items before Friday.",
                    speaker_label="Speaker 1",
                    due_date="2026-08-17",
                    priority="high",
                ),
                ActionItemResult(
                    description="Review quarterly backend performance metrics.",
                    speaker_label="Speaker 2",
                    due_date="2026-08-20",
                    priority="medium",
                ),
            ],
            chapters=[
                ChapterResult(
                    sequence_number=1,
                    title="Introduction & Roadmap Review",
                    summary="Welcome notes and roadmap overview.",
                    start_time_ms=0,
                    end_time_ms=12000,
                ),
                ChapterResult(
                    sequence_number=2,
                    title="Action Items & Finalization",
                    summary="Discussion on engineering action items.",
                    start_time_ms=12500,
                    end_time_ms=20000,
                ),
            ],
        )
