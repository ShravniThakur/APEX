"""Groq LLM calls for the Analyser graph nodes.

Three plain-text calls — hypothesise / critique / compose. Each is best-effort: any failure
(no key, rate limit) returns "" so the graph still completes (the deterministic gate and DB
writes never depend on the LLM succeeding).
"""
from __future__ import annotations

from ..config import GROQ_API_KEY, GROQ_MODEL
from ._shared import get_client
from .prompts import (
    SYSTEM_PROMPT, build_compose_prompt, build_critique_prompt, build_explain_prompt,
    build_hypothesise_prompt, build_reengage_prompt,
)


def _chat(user: str, temperature: float = 0.4) -> str:
    if not GROQ_API_KEY:
        return ""
    try:
        resp = get_client().chat.completions.create(
            model=GROQ_MODEL,
            temperature=temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001 — never let one bad call break the batch
        return ""


def hypothesise(payload: dict) -> str:
    return _chat(build_hypothesise_prompt(payload), temperature=0.4)


def critique(payload: dict) -> str:
    return _chat(build_critique_prompt(payload), temperature=0.3)


def compose(payload: dict) -> str:
    return _chat(build_compose_prompt(payload), temperature=0.4)


def reengage(payload: dict) -> str:
    return _chat(build_reengage_prompt(payload), temperature=0.4)


def explain(payload: dict) -> str:
    return _chat(build_explain_prompt(payload), temperature=0.3)
