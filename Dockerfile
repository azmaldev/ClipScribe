FROM python:3.12-slim

# Install system-level dependencies required by yt-dlp for audio
# extraction and conversion (ffmpeg).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Pin yt-dlp to a known-working version.
# ═══ UPGRADE NOTE ═══════════════════════════════════════════════
# Update this version periodically (check pypi.org/project/yt-dlp)
# as platforms like YouTube/TikTok change their extraction methods.
# Outdated yt-dlp will fail on otherwise-valid URLs.
ARG YTDLP_VERSION=2026.6.9
RUN pip install --no-cache-dir "yt-dlp==${YTDLP_VERSION}"

WORKDIR /app

# Install project dependencies (uses pyproject.toml).
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code.
COPY app/ ./app/

# Create a non-root user for security; own the application tree.
RUN useradd --create-home --shell /bin/bash clipscribe && \
    chown -R clipscribe:clipscribe /app

USER clipscribe

# Railway sets PORT dynamically via environment variable.
ENV PORT=8000
EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
