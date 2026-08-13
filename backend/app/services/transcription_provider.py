from abc import ABC, abstractmethod
import os
from pathlib import Path

from pydantic import BaseModel, Field


class TranscriptionSegmentData(BaseModel):
    sequence_number: int = Field(..., ge=1, description="1-indexed sequence number")
    start_time_ms: int = Field(..., ge=0, description="Start offset in milliseconds")
    end_time_ms: int = Field(..., ge=0, description="End offset in milliseconds")
    text: str = Field(..., min_length=1, description="Transcribed spoken text")
    speaker_label: str | None = Field(None, description="Speaker identifier (e.g. Speaker 1)")


class TranscriptionResult(BaseModel):
    segments: list[TranscriptionSegmentData] = Field(default_factory=list)
    language: str | None = Field("en", description="Detected or specified audio language")
    duration_ms: int | None = Field(None, ge=0, description="Total audio duration in milliseconds")


class TranscriptionProvider(ABC):
    """Abstract base class for speech-to-text transcription providers."""

    @abstractmethod
    async def transcribe(self, audio_file_path: Path) -> TranscriptionResult:
        """Transcribe an audio file and return normalized transcription data."""
        pass


class MockTranscriptionProvider(TranscriptionProvider):
    """Deterministic mock transcription provider for testing and development."""

    def __init__(self, include_speakers: bool = True, raise_error: bool = False):
        self.include_speakers = include_speakers
        self.raise_error = raise_error

    async def transcribe(self, audio_file_path: Path) -> TranscriptionResult:
        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        if self.raise_error:
            raise RuntimeError("Mock transcription provider failure simulated.")

        if self.include_speakers:
            segments = [
                TranscriptionSegmentData(
                    sequence_number=1,
                    start_time_ms=0,
                    end_time_ms=5000,
                    text="Welcome everyone to today's meeting.",
                    speaker_label="Speaker 1",
                ),
                TranscriptionSegmentData(
                    sequence_number=2,
                    start_time_ms=5200,
                    end_time_ms=12000,
                    text="Thanks for having me. Let's review our quarterly roadmap.",
                    speaker_label="Speaker 2",
                ),
                TranscriptionSegmentData(
                    sequence_number=3,
                    start_time_ms=12500,
                    end_time_ms=20000,
                    text="Great. We need to finalize the engineering action items before Friday.",
                    speaker_label="Speaker 1",
                ),
            ]
        else:
            segments = [
                TranscriptionSegmentData(
                    sequence_number=1,
                    start_time_ms=0,
                    end_time_ms=6000,
                    text="This is a recording without speaker identification.",
                    speaker_label=None,
                ),
                TranscriptionSegmentData(
                    sequence_number=2,
                    start_time_ms=6500,
                    end_time_ms=15000,
                    text="All spoken content is captured sequentially in time.",
                    speaker_label=None,
                ),
            ]

        return TranscriptionResult(
            segments=segments,
            language="en",
            duration_ms=segments[-1].end_time_ms,
        )


class GeminiTranscriptionProvider(TranscriptionProvider):
    """Transcription provider using the official Google GenAI SDK."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    async def transcribe(self, audio_file_path: Path) -> TranscriptionResult:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        from google import genai
        client = genai.Client(api_key=self.api_key)

        uploaded_audio = client.files.upload(file=audio_file_path)

        prompt = (
            "Listen to this audio recording and transcribe it into structured segments. "
            "Return JSON matching TranscriptionResult schema."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[uploaded_audio, prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": TranscriptionResult,
            },
        )

        if not response.text:
            raise RuntimeError("Empty response received from Gemini API.")

        return TranscriptionResult.model_validate_json(response.text)


def get_transcription_provider(
    provider_name: str | None = None,
    mock_raise_error: bool = False,
    mock_include_speakers: bool = True,
) -> TranscriptionProvider:
    """Factory returning configured transcription provider."""
    name = (provider_name or os.getenv("TRANSCRIPTION_PROVIDER", "mock")).lower()
    api_key = os.getenv("GEMINI_API_KEY")

    if name == "gemini" and api_key:
        return GeminiTranscriptionProvider(api_key=api_key)

    return MockTranscriptionProvider(
        include_speakers=mock_include_speakers,
        raise_error=mock_raise_error,
    )
