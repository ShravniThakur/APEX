"""Shared Groq helpers used across the agent modules (the single client + language names)."""
from __future__ import annotations

from ..config import GROQ_API_KEY

LANG_NAMES = {"en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali"}

_client = None


def get_client():
    """Lazily-created Groq client, shared by every agent module.

    max_retries: the SDK honors Groq's 429 Retry-After header and backs off, so a brief
    free-tier rate-limit spike (e.g. right after a full pipeline run) is retried transparently
    instead of failing the first request.
    """
    global _client
    if _client is None:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY, max_retries=4)
    return _client
