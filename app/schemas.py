from pydantic import BaseModel, HttpUrl


class TranscribeRequest(BaseModel):
    """Request to transcribe a video.

    The caller provides a video URL. We validate it is a well-formed HTTP(S)
    URL before any processing begins, so extraction failures from malformed
    input are caught early at the API layer.
    """

    url: HttpUrl


class TranscriptSegment(BaseModel):
    """A single timed segment of the transcript.

    Segments are returned alongside the full transcript so that callers who
    need timestamp-anchored text (e.g. caption overlays, chapter markers,
    search-indexing) can use them directly without re-parsing.
    """

    start: float
    end: float
    text: str


class TranscribeResponse(BaseModel):
    """Successful transcription result.

    `transcript` is the full joined text for callers that only want plain
    output. `segments` provides the same content split into timed chunks for
    callers that need per-word or per-phrase timing.
    """

    transcript: str
    segments: list[TranscriptSegment]
    duration_seconds: float
    platform: str


class TranscribeErrorResponse(BaseModel):
    """Error returned when transcription fails.

    `error` is a short machine-readable key (e.g. "extraction_failed") and
    `detail` is a human-readable explanation. Together they let callers
    handle failures programmatically while still showing useful messages.
    """

    error: str
    detail: str
