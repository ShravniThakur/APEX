"""Shared LLM helpers used across the agent modules (the single client + language names).

The client is provider-agnostic: both the Groq SDK and the OpenAI SDK expose the same
`chat.completions.create` surface, and Ollama serves an OpenAI-compatible endpoint — so every
agent call site works unchanged whichever provider config.LLM_PROVIDER selects.
"""
from __future__ import annotations

from ..config import GROQ_API_KEY, LLM_PROVIDER, OLLAMA_BASE_URL

LANG_NAMES = {"en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali"}

_client = None


def get_client():
    """Lazily-created, shared LLM client — hosted Groq or local Ollama, per LLM_PROVIDER.

    Ollama (LLM_PROVIDER=ollama): a local OpenAI-compatible server — no API key, no rate limits.
    Groq: max_retries honors the 429 Retry-After header and backs off, so a brief free-tier
    rate-limit spike (e.g. right after a full pipeline run) is retried instead of failing.
    """
    global _client
    if _client is None:
        if LLM_PROVIDER == "ollama":
            from openai import OpenAI
            # api_key is required non-empty by the SDK but ignored by Ollama.
            _client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", max_retries=2)
        else:
            from groq import Groq
            _client = Groq(api_key=GROQ_API_KEY, max_retries=4)
    return _client
