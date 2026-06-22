"""Guide mode — conversational onboarding for a NEW / prospective customer.

Uses **context injection**: the product catalogue (grouped by life-need) is stuffed into the system
prompt, so Guide reasons about the whole landscape and can surface relevant adjacent areas. Reactive
(the customer starts the chat); behavioral philosophy applies (plain language, no jargon, calm,
the customer's language). Concierge lives in concierge.py; voice STT in voice.py.
"""
from __future__ import annotations

from collections import defaultdict

from ..config import GROQ_API_KEY, GROQ_MODEL
from ..database.models import Product
from ._shared import get_client

GUIDE_SYSTEM = """You are APEX, an AI onboarding guide inside SBI, talking with a NEW or \
prospective customer. Help them choose the right account or product and understand what \
documents they need, in plain language. You do NOT have their banking data yet — ask simple \
questions to understand their need first. When you recommend something, you may share its \
official SBI link from the list below. Be calm, on the customer's side, never pushy, no jargon. \
Reply in the customer's language; if you don't know it yet, mirror the language they write in.

A new customer doesn't know what they don't know, so don't leave them with a partial picture — \
but never dump a product list. After you've helped with their immediate need, gently surface ONE \
or TWO *other* areas below that genuinely fit their situation, framed as life outcomes, not product \
names (say "a low-cost way to protect your family", not "PMJJBY"). Then offer to explain more or \
mention they can browse everything SBI offers. One or two relevant mentions at a time — let them \
choose what to go deeper on."""

# Product categories grouped by the life-need they serve (so Guide reasons about the
# landscape, not a flat list, and can surface relevant *adjacent* areas).
LIFE_NEEDS = [
    ("Save", ("accounts", "deposits")),
    ("Grow your money", ("investments",)),
    ("Borrow", ("loans",)),
    ("Protect your family", ("insurance",)),
    ("Pay & spend", ("payments", "cards")),
]


def build_guide_context(db) -> str:
    by_cat = defaultdict(list)
    for p in db.query(Product).filter(Product.depth == "full"):
        by_cat[p.category].append(p)
    lines = ["SBI products you can guide toward, grouped by what they're for:"]
    for label, cats in LIFE_NEEDS:
        items = [p for c in cats for p in by_cat.get(c, [])]
        if not items:
            continue
        lines.append(f"\n{label}:")
        for p in items:
            lines.append(f"  - {p.name}: {p.primary_use or ''} Link: {p.landing_url}")
    return "\n".join(lines)


def reply(messages: list[dict], db) -> str:
    if not GROQ_API_KEY:
        return "The assistant isn't configured yet (missing GROQ_API_KEY)."
    system = GUIDE_SYSTEM + "\n\n" + build_guide_context(db)
    convo = [{"role": "system", "content": system}]
    convo += [{"role": m["role"], "content": m["content"]}
              for m in messages if m.get("role") in ("user", "assistant")]
    try:
        resp = get_client().chat.completions.create(model=GROQ_MODEL, temperature=0.4, messages=convo)
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        if type(exc).__name__ == "RateLimitError":
            return "I'm handling a lot of requests right now — give me a few seconds and ask again."
        return f"(assistant error: {type(exc).__name__})"
