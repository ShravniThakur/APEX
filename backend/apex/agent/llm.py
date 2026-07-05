"""Groq LLM calls for Analyser mode.

Best-effort by design: any failure (no key, rate limit, bad JSON) returns ""/{} so the
deterministic gate and DB writes never depend on the LLM succeeding. The act/wait/escalate
decision and the safe product set are settled in code (guardrails.py) before the LLM is asked
anything — the LLM only picks the best fit from a vetted shortlist and writes the message.
"""
from __future__ import annotations

import json

from ..config import CHAT_MODEL, LLM_READY
from ._shared import get_client
from .prompts import (
    SYSTEM_PROMPT, build_explain_prompt, build_reengage_prompt, build_select_prompt,
)


def _chat(user: str, temperature: float = 0.4, json_mode: bool = False) -> str:
    if not LLM_READY:
        return ""
    try:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = get_client().chat.completions.create(
            model=CHAT_MODEL,
            temperature=temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            **kwargs,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001 — never let one bad call break the batch
        return ""


def select_and_compose(payload: dict) -> dict:
    """Pick the best-fit product from the vetted shortlist + write the message, in one call.
    Returns {"product_id", "reason", "message"} or {} on any failure (caller falls back to the
    top-ranked product + a deterministic message)."""
    raw = _chat(build_select_prompt(payload), temperature=0.4, json_mode=True)
    if not raw:
        return {}
    txt = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(txt)
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        "product_id": data.get("product_id"),
        "reason": (data.get("reason") or "").strip(),
        "message": (data.get("message") or "").strip(),
    }


def reengage(payload: dict) -> str:
    return _chat(build_reengage_prompt(payload), temperature=0.4)


def explain(payload: dict) -> str:
    return _chat(build_explain_prompt(payload), temperature=0.3)
