import os
from dataclasses import dataclass
from typing import Any

from groq import (
    APIConnectionError,
    AsyncGroq,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)
from groq import (
    APIError as GroqAPIError,
)

from app.config import settings
from app.schemas import TranscriptSegment


class TranscriptionError(Exception):
    """Raised when transcription via the Groq API fails for any reason."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass
class TranscriptionResult:
    """Result of a successful transcription.

    Attributes:
        transcript: Full joined transcript text from the audio.
        segments:   Timestamped segments with start, end, and text.
    """

    transcript: str
    segments: list[TranscriptSegment]


async def transcribe_audio(file_path: str) -> TranscriptionResult:
    """Transcribe a local audio file using the Groq Whisper API.

    Sends the audio to Groq's ``whisper-large-v3-turbo`` model with
    ``verbose_json`` output to obtain per-segment timestamps. Maps the
    raw API response into our own schema types rather than leaking the
    SDK's shape.

    Raises TranscriptionError on any API or response-parsing failure.
    """
    client = AsyncGroq(
        api_key=settings.groq_api_key,
        timeout=120.0,
    )

    try:
        with open(file_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                file=(os.path.basename(file_path), f),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
            )
    except AuthenticationError:
        raise TranscriptionError(
            "Groq API authentication failed. Check your GROQ_API_KEY."
        )
    except RateLimitError:
        raise TranscriptionError(
            "Groq API rate limit exceeded. Try again later."
        )
    except BadRequestError as e:
        raise TranscriptionError(
            f"Invalid request to Groq API: {e.message}"
        )
    except APIConnectionError:
        raise TranscriptionError(
            "Failed to connect to the Groq API. Check your network."
        )
    except GroqAPIError as e:
        raise TranscriptionError(f"Groq API error: {e}")
    except OSError as e:
        raise TranscriptionError(f"Failed to read audio file: {e}")

    response_data: dict[str, Any] = response.to_dict()
    transcript_text = str(response_data.get("text", "")) or ""
    segments_raw = response_data.get("segments", []) or []

    segments = [
        TranscriptSegment(
            start=float(s["start"]),
            end=float(s["end"]),
            text=str(s["text"]),
        )
        for s in segments_raw
    ]

    return TranscriptionResult(
        transcript=transcript_text,
        segments=segments,
    )
