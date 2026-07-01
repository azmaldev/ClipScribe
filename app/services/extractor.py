import asyncio
import os
import tempfile
import uuid
from dataclasses import dataclass


class ExtractionError(Exception):
    """Raised when audio extraction from a video URL fails for any reason."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass
class ExtractionResult:
    """Result of a successful audio extraction.

    Attributes:
        audio_path: Absolute path to the downloaded audio file (mp3, 16 kHz mono).
        platform:  Name of the detected platform/extractor (e.g. "youtube", "twitter").
        duration_seconds: Total duration of the video in seconds.
    """

    audio_path: str
    platform: str
    duration_seconds: float


async def extract_audio(url: str) -> ExtractionResult:
    """Download audio from a video URL, returning the local path, platform, and duration.

    Uses yt-dlp via async subprocess to avoid blocking the event loop.
    Audio is extracted as 16 kHz mono mp3, sufficient for transcription quality.
    Raises ExtractionError if yt-dlp fails, times out, or produces no output file.
    """
    tmpdir = tempfile.gettempdir()
    file_id = uuid.uuid4().hex
    output_template = os.path.join(tmpdir, f"clipscribe_{file_id}.%(ext)s")

    expected_path = os.path.join(tmpdir, f"clipscribe_{file_id}.mp3")

    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--postprocessor-args",
        "ffmpeg:-ar 16000 -ac 1",
        "-o",
        output_template,
        "--print",
        "after_move:duration",
        "--print",
        "after_move:extractor",
        "--no-progress",
        url,
    ]

    success = False
    try:
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise ExtractionError(
                "yt-dlp executable not found. Ensure yt-dlp is installed and on PATH."
            )
        except OSError as e:
            raise ExtractionError(f"System error running yt-dlp: {e}")

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=60.0
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise ExtractionError(
                f"yt-dlp timed out after 60 seconds for URL: {url}"
            )

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            raise ExtractionError(
                f"yt-dlp failed (exit code {process.returncode}): {error_msg}"
            )

        output_lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
        if len(output_lines) < 2:
            raise ExtractionError(
                f"Could not parse yt-dlp output for URL: {url}"
            )

        try:
            duration_seconds = float(output_lines[0].strip())
        except ValueError:
            raise ExtractionError(
                f"Could not parse duration from yt-dlp output for URL: {url}"
            )
        platform = output_lines[1].strip()

        if not os.path.isfile(expected_path) or os.path.getsize(expected_path) == 0:
            raise ExtractionError(
                f"yt-dlp completed but no audio file was produced at: {expected_path}"
            )

        result = ExtractionResult(
            audio_path=expected_path,
            platform=platform,
            duration_seconds=duration_seconds,
        )
        success = True
        return result
    finally:
        if not success and os.path.isfile(expected_path):
            os.remove(expected_path)
