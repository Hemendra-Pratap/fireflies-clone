from abc import ABC, abstractmethod
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)



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

        filename = audio_file_path.name
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
                    text="Thanks for having me.",
                    speaker_label="Speaker 2",
                ),
                TranscriptionSegmentData(
                    sequence_number=3,
                    start_time_ms=12200,
                    end_time_ms=20000,
                    text="Alex will take ownership of the backend API implementation.",
                    speaker_label="Speaker 1",
                ),
            ]
        else:
            segments = [
                TranscriptionSegmentData(
                    sequence_number=1,
                    start_time_ms=0,
                    end_time_ms=6000,
                    text="Sequential spoken content from recorded audio file.",
                    speaker_label=None,
                ),
                TranscriptionSegmentData(
                    sequence_number=2,
                    start_time_ms=6200,
                    end_time_ms=15000,
                    text="Discussion continues on project milestones and next steps.",
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

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or settings.gemini_model or "gemini-3-flash-preview"

    async def transcribe(self, audio_file_path: Path) -> TranscriptionResult:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured for Gemini speech-to-text transcription.")

        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        size_bytes = audio_file_path.stat().st_size
        if size_bytes == 0:
            raise ValueError(f"Audio file is empty (0 bytes): {audio_file_path}")

        # Extract audio metadata for logging
        ext = audio_file_path.suffix.lower()
        mime_type = {
            ".mp3": "audio/mp3",
            ".wav": "audio/wav",
            ".m4a": "audio/m4a",
            ".ogg": "audio/ogg",
            ".webm": "audio/webm",
            ".mp4": "audio/mp4",
            ".aac": "audio/aac",
            ".flac": "audio/flac",
        }.get(ext, "audio/mpeg")

        duration_sec = "unknown"
        channels = "unknown"
        sample_rate = "unknown"

        if ext == ".wav":
            try:
                import wave
                with wave.open(str(audio_file_path), "rb") as wf:
                    ch = wf.getnchannels()
                    sr = wf.getframerate()
                    frames = wf.getnframes()
                    dur = frames / float(sr) if sr > 0 else 0
                    channels = str(ch)
                    sample_rate = str(sr)
                    duration_sec = f"{dur:.2f}"
            except Exception:
                pass

        logger.info(f"[TRANSCRIPTION] file: {audio_file_path.name}")
        logger.info(f"[TRANSCRIPTION] provider: GeminiTranscriptionProvider")
        logger.info(f"[TRANSCRIPTION] model: {self.model_name}")
        logger.info(
            f"[TRANSCRIPTION] audio metadata: duration={duration_sec}s, channels={channels}, "
            f"sample_rate={sample_rate}Hz, format={ext.lstrip('.')}, size={size_bytes}bytes"
        )
        logger.info(f"[TRANSCRIPTION] request started: {audio_file_path.name}")

        import time
        from google import genai
        client = genai.Client(api_key=self.api_key)

        # Pass explicit mime_type to prevent fallback to generic octet-stream
        uploaded_audio = client.files.upload(
            file=str(audio_file_path),
            config={"mime_type": mime_type},
        )

        # Poll file processing status until ACTIVE or FAILED
        while hasattr(uploaded_audio, "state") and uploaded_audio.state and getattr(uploaded_audio.state, "name", "") == "PROCESSING":
            time.sleep(1.5)
            uploaded_audio = client.files.get(name=uploaded_audio.name)

        if hasattr(uploaded_audio, "state") and uploaded_audio.state and getattr(uploaded_audio.state, "name", "") == "FAILED":
            raise RuntimeError(f"Audio file processing failed on Gemini API: {getattr(uploaded_audio, 'error', 'Unknown error')}")

        prompt = (
            "You are a professional, high-accuracy verbatim speech-to-text transcription engine.\n"
            "Your objective is to produce an EXACT, 100% VERBATIM word-for-word transcript of the provided audio recording.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. VERBATIM ACCURACY: Transcribe every single spoken word exactly as uttered in the audio. Do NOT paraphrase, summarize, omit words, fix grammar, or clean up filler words.\n"
            "2. CHRONOLOGICAL SEGMENTS: Divide the audio into chronological, sequential transcript segments starting at sequence_number=1.\n"
            "3. TIMESTAMPS: Calculate precise start_time_ms and end_time_ms for every segment in milliseconds relative to the start of the audio file (0ms).\n"
            "4. SPEAKER DIARIZATION: Identify distinct speakers as 'Speaker 1', 'Speaker 2', etc. Whenever the speaker changes, start a new segment with the appropriate speaker_label.\n"
            "5. NO HALLUCINATION: Transcribe ONLY content actually spoken in the audio file. Never fabricate, invent, or reconstruct dialogue not present in the recording.\n"
            "6. COMPLETENESS: Transcribe the complete audio recording from start to finish without omitting any spoken sentence.\n"
            "7. OUTPUT FORMAT: Return JSON adhering strictly to the TranscriptionResult schema."
        )

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[uploaded_audio, prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": TranscriptionResult,
                },
            )
        finally:
            try:
                client.files.delete(name=uploaded_audio.name)
            except Exception:
                pass

        if not response.text:
            raise RuntimeError("Empty response received from Gemini Speech-to-Text API.")

        logger.info(f"[TRANSCRIPTION] request completed: {audio_file_path.name}")
        logger.info(f"[TRANSCRIPTION] raw response received: length={len(response.text)} chars")

        result = TranscriptionResult.model_validate_json(response.text)

        if result.segments:
            sorted_segs = sorted(result.segments, key=lambda s: (s.start_time_ms, s.sequence_number))
            for idx, seg in enumerate(sorted_segs, start=1):
                seg.sequence_number = idx
            result.segments = sorted_segs
            if not result.duration_ms and sorted_segs:
                result.duration_ms = sorted_segs[-1].end_time_ms

        logger.info(f"[TRANSCRIPTION] segment count: {len(result.segments)}")
        logger.info(f"[TRANSCRIPTION] transcript character count: {sum(len(s.text) for s in result.segments)}")

        return result


def get_transcription_provider(
    provider_name: str | None = None,
    mock_raise_error: bool = False,
    mock_include_speakers: bool = True,
) -> TranscriptionProvider:
    """Factory returning configured transcription provider."""
    raw_name = (provider_name or settings.transcription_provider or os.getenv("TRANSCRIPTION_PROVIDER", "")).lower()
    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")

    if raw_name == "gemini" or (api_key and raw_name != "mock"):
        if not api_key:
            raise ValueError("TRANSCRIPTION_PROVIDER is set to 'gemini' but GEMINI_API_KEY is missing or unconfigured.")
        return GeminiTranscriptionProvider(api_key=api_key)

    return MockTranscriptionProvider(
        include_speakers=mock_include_speakers,
        raise_error=mock_raise_error,
    )
