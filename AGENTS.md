# Clipscribe — Agent Rules

## Role
- Production-grade, typed Python. No notebook-style scripts.
- Think like a system designer first, coder second: before writing a file, state in 2–3 lines what it does and why it's structured that way.
- Building ONE thing: an engine that takes a video URL and returns a transcript. Nothing else. No database, no auth, no user accounts, no content-research features, no frontend. If unsure whether something is in scope, it is NOT in scope — ask instead of adding it.

## Hard Rules
1. Stack is fixed, do not deviate: FastAPI (async), yt-dlp (audio-only extraction), Groq Whisper API (whisper-large-v3-turbo) for transcription, Python 3.12+, deployed via Docker to Railway.
2. No persistent storage of any kind. Downloaded audio is deleted immediately after transcription, success or failure, via `try/finally`.
3. No database, no auth, no API key system — single internal endpoint only.
4. All functions must be fully type-hinted. Use Pydantic models for request/response schemas, never raw dicts.
5. Use `ruff` for linting and `mypy` for type checking. After any code change, run both and fix all errors before declaring a task done.
6. Keep the codebase small and flat. Do not over-engineer with layers, repositories, or abstractions we don't need yet.
7. Every external call (yt-dlp subprocess, Groq API) must have explicit error handling and return a clean, typed error response — never let a raw exception or stack trace leak to the API response.
8. Do not install any package not explicitly listed in these prompts without asking first.

## Workflow
- Prompts are given one at a time. Each prompt is one unit of work.
- At the end of every prompt, after finishing the task and verifying it works (lint + type check pass), STOP and wait for the next prompt. Do not guess what comes next.
- If anything in a prompt is ambiguous, ask before proceeding.
