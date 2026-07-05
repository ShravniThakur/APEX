"""Voice — speech-to-text (mode-agnostic; used by Guide and Concierge).

Two backends, chosen by config.USE_LOCAL_WHISPER (which tracks LLM_PROVIDER):
  • local  → in-process faster-whisper. No network, no key, no rate limits. The model is
             downloaded once on first use and cached in-process for the life of the server.
  • hosted → Groq Whisper (reuses the project's Groq key).
Text-to-speech is done browser-side in the frontend.
"""
from __future__ import annotations

import io

from ..config import (
    GROQ_API_KEY, GROQ_WHISPER_MODEL, LOCAL_WHISPER_MODEL, USE_LOCAL_WHISPER,
)
from ._shared import get_client

_whisper = None


def _local_model():
    """Lazily load + cache the faster-whisper model (heavy: load once, reuse forever)."""
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        # int8 on CPU keeps memory/latency reasonable on a laptop; swap to "cuda" if available.
        _whisper = WhisperModel(LOCAL_WHISPER_MODEL, device="cpu", compute_type="int8")
    return _whisper


def transcribe(filename: str, data: bytes) -> str:
    """Speech-to-text. Returns '' on any failure (no backend, decode/API error)."""
    if USE_LOCAL_WHISPER:
        try:
            segments, _ = _local_model().transcribe(io.BytesIO(data))
            return "".join(s.text for s in segments).strip()
        except Exception:  # noqa: BLE001
            return ""
    if not GROQ_API_KEY:
        return ""
    try:
        r = get_client().audio.transcriptions.create(file=(filename, data), model=GROQ_WHISPER_MODEL)
        return (getattr(r, "text", "") or "").strip()
    except Exception:  # noqa: BLE001
        return ""
