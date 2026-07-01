import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.schemas import (
    TranscribeErrorResponse,
    TranscribeRequest,
    TranscribeResponse,
)
from app.services.extractor import ExtractionError, extract_audio
from app.services.transcriber import TranscriptionError, transcribe_audio

MAX_DURATION_SECONDS = 1200.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(title="Clipscribe", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(body: TranscribeRequest) -> JSONResponse:
    audio_path: str | None = None
    url = str(body.url)

    logger.info("request_received  url=%s", url)

    try:
        logger.info("extracting_audio  url=%s", url)
        extraction = await extract_audio(url)
        audio_path = extraction.audio_path
        logger.info(
            "extraction_succeeded  path=%s  platform=%s  duration=%.1fs",
            audio_path,
            extraction.platform,
            extraction.duration_seconds,
        )

        if extraction.duration_seconds > MAX_DURATION_SECONDS:
            logger.warning(
                "duration_exceeded  duration=%.1fs  max=%.0fs",
                extraction.duration_seconds,
                MAX_DURATION_SECONDS,
            )
            return JSONResponse(
                content=TranscribeErrorResponse(
                    error="duration_exceeded",
                    detail=(
                        f"Video duration ({extraction.duration_seconds:.0f}s) exceeds the "
                        f"maximum allowed duration of {MAX_DURATION_SECONDS:.0f}s."
                    ),
                ).model_dump(mode="json"),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        logger.info("transcribing_audio  path=%s", audio_path)
        transcription = await transcribe_audio(audio_path)
        logger.info(
            "transcription_succeeded  segments=%d  transcript_length=%d",
            len(transcription.segments),
            len(transcription.transcript),
        )

        response = TranscribeResponse(
            transcript=transcription.transcript,
            segments=transcription.segments,
            duration_seconds=extraction.duration_seconds,
            platform=extraction.platform,
        )
        return JSONResponse(
            content=response.model_dump(mode="json"),
            status_code=status.HTTP_200_OK,
        )

    except ExtractionError as e:
        logger.warning("extraction_failed  reason=%s", e.message)

        if "Unsupported URL" in e.message:
            error_key = "platform_unsupported"
        else:
            error_key = "extraction_failed"

        error_response = TranscribeErrorResponse(
            error=error_key,
            detail=e.message,
        )
        if "yt-dlp executable not found" in e.message or "System error" in e.message:
            http_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif "timed out" in e.message:
            http_code = status.HTTP_504_GATEWAY_TIMEOUT
        else:
            http_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return JSONResponse(
            content=error_response.model_dump(mode="json"),
            status_code=http_code,
        )

    except TranscriptionError as e:
        logger.error("transcription_failed  reason=%s", e.message)
        error_response = TranscribeErrorResponse(
            error="transcription_failed",
            detail=e.message,
        )
        if "authentication failed" in e.message:
            http_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            http_code = status.HTTP_502_BAD_GATEWAY
        return JSONResponse(
            content=error_response.model_dump(mode="json"),
            status_code=http_code,
        )

    finally:
        if audio_path and os.path.isfile(audio_path):
            os.remove(audio_path)
            logger.info("temp_file_cleaned_up  path=%s", audio_path)
