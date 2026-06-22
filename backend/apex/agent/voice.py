"""Voice — speech-to-text via Groq Whisper (mode-agnostic; used by Guide and Concierge).

Reuses the project's Groq key — no separate voice provider. Text-to-speech is done browser-side
in the frontend.
"""
from __future__ import annotations

from ..config import GROQ_API_KEY, GROQ_WHISPER_MODEL
from ._shared import get_client


def transcribe(filename: str, data: bytes) -> str:
    """Speech-to-text. Returns '' on any failure (no key, API error)."""
    if not GROQ_API_KEY:
        return ""
    try:
        r = get_client().audio.transcriptions.create(file=(filename, data), model=GROQ_WHISPER_MODEL)
        return (getattr(r, "text", "") or "").strip()
    except Exception:  # noqa: BLE001
        return ""
