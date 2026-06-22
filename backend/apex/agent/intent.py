"""Conversational signal extraction — Concierge chat becomes a signal source.

A customer's STATED intent is the strongest life-moment signal there is: "I want to start
investing" is a present, voluntary need, where behavioural signals are only ever inferred *after*
the fact. After a Concierge turn we run one extraction pass over the conversation and write each
explicit product interest as a `stated_intent` signal — which then flows through the SAME routing
+ eligibility + ethical gate (guardrails) as any other signal, so the vulnerability restraint and
dismissal back-off apply automatically.

The ethical split is the whole point:
- An **explicit, customer-pulled intent** → an actionable `stated_intent` signal (the ideal: the
  customer pulled the product forward themselves).
- A disclosed **vulnerability** (a medical crisis, job loss, money fear) → we create NOTHING, and
  we *withdraw* any pending stated intents for that customer. Never turn distress someone confided
  into a sales trigger.
"""
from __future__ import annotations

import json

from ..config import GROQ_API_KEY, GROQ_MODEL
from ..database.db import SessionLocal
from ..database.models import Signal
from ._shared import get_client

# Categories an intent can map to (must match PRODUCTS.category so routing can serve it).
CATEGORIES = {"accounts", "deposits", "investments", "loans", "insurance", "payments"}

_SYSTEM = (
    "You analyse a customer's chat with their bank's assistant and output STRICT JSON only — no "
    "prose, no markdown. Schema:\n"
    '{"intents": [{"category": "<accounts|deposits|investments|loans|insurance|payments>", '
    '"summary": "<short phrase>"}], "vulnerable": <true|false>}\n'
    "Rules:\n"
    "- Add an intent ONLY if the customer EXPLICITLY expressed wanting, needing, or asking to get "
    "that kind of product — not idle curiosity, and not something the assistant raised first. Map "
    "it to the closest category. If there is none, return an empty list.\n"
    "- Set vulnerable=true if the customer revealed a sensitive or distressing situation (a medical "
    "emergency, job loss, debt trouble, bereavement, or fear about money). Otherwise false.\n"
    "- Output nothing but the JSON object."
)


def _extract(messages: list[dict]) -> dict:
    """One best-effort LLM pass → {"intents": [...], "vulnerable": bool}. {} on any failure."""
    if not GROQ_API_KEY:
        return {}
    convo = "\n".join(f"{m['role']}: {m['content']}"
                      for m in messages if m.get("role") in ("user", "assistant"))
    if not convo.strip():
        return {}
    try:
        resp = get_client().chat.completions.create(
            model=GROQ_MODEL, temperature=0.1,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": convo}],
        )
        text = (resp.choices[0].message.content or "").strip()
        return json.loads(text)
    except Exception:  # noqa: BLE001 — extraction is best-effort; never break the chat
        return {}


def extract_and_store(customer_id: str, messages: list[dict]) -> list[str]:
    """Mine the conversation and persist `stated_intent` signals. Returns the categories created.
    Runs as a background task after the Concierge reply, so it never delays the chat."""
    data = _extract(messages)
    if not data:
        return []

    with SessionLocal() as session:
        # Vulnerability disclosed → restraint: create nothing, and withdraw any pending intents.
        if data.get("vulnerable"):
            pending = session.query(Signal).filter(
                Signal.customer_id == customer_id,
                Signal.signal_type == "stated_intent",
                Signal.status == "new",
            ).all()
            for sig in pending:
                sig.status = "expired"   # they just disclosed distress — don't sell into it
            session.commit()
            return []

        # Explicit intents → actionable signals (de-duped per category against still-open ones).
        existing = {
            sig.source_ref for sig in session.query(Signal).filter(
                Signal.customer_id == customer_id,
                Signal.signal_type == "stated_intent",
                Signal.status == "new",
            )
        }
        created: list[str] = []
        for item in data.get("intents", []):
            cat = (item or {}).get("category")
            if cat in CATEGORIES and cat not in existing:
                session.add(Signal(customer_id=customer_id, signal_type="stated_intent",
                                   source_ref=cat, status="new"))
                existing.add(cat)
                created.append(cat)
        session.commit()
    return created
