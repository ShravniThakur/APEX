"""Prompt construction for Analyser-mode LLM calls (behavioral philosophy).

The Analyser's act/wait/escalate decision, the eligibility checks, and the ethical restraint are
all deterministic code (guardrails.py). The LLM's *only* job is, given a pre-vetted shortlist of
safe products (eligible, unheld, ethically cleared): pick the single best fit for this specific
person right now, and write the customer message. "Code disposes the decision and the safe set;
the LLM proposes the relevance pick and the wording" — it can never reach an unsafe option.

Also holds the reengage + explain prompts (used by the wait-follow-up and the "why?" endpoint).
"""
import json

from ._shared import LANG_NAMES

SYSTEM_PROMPT = """You are APEX, an AI financial concierge deployed inside SBI (State Bank of India), \
operating in Analyser mode. You watch a customer's own banking data and reach out only at real \
moments in their financial life. You are on the customer's side, not the bank's.

When you write anything customer-facing:
- Write in the customer's preferred language. Keep it short: 2-4 sentences.
- NEVER use financial jargon (no "SIP", "CAGR", "NAV", instrument names). Speak in concrete life \
outcomes — e.g. "this could grow to about X over five years", not product mechanics.
- Calm, institutional tone. Never promotional. No urgency, no exclamation marks, no hype. Real SBI \
alerts get phished constantly, so avoid any shape that pattern-matches to a scam: no "click now", \
no links in the text, no pressure.
- Do not invent URLs, numbers, or offers. A secure link is attached separately by the system."""


def _customer_line(payload: dict) -> str:
    c = payload["customer"]
    lang = LANG_NAMES.get(c.get("language_pref"), "English")
    return (f"Customer: {c['first_name']}, age {c.get('age')}, {c.get('occupation')}, "
            f"city tier {c.get('city_tier')}. Preferred language: {lang}.")


def build_select_prompt(payload: dict) -> str:
    """Pick-the-best-fit + compose, in one call. The candidate list is already vetted by code
    (eligible, unheld, ethically cleared) — the LLM only chooses which one suits this person and
    writes the message. It returns strict JSON so code can validate the chosen id."""
    c = payload["customer"]
    lang = LANG_NAMES.get(c.get("language_pref"), "English")
    lines = []
    for i, p in enumerate(payload["candidates"], 1):
        lines.append(
            f'{i}. id="{p["product_id"]}" — {p.get("name")}: {p.get("description", "")} '
            f'Key facts: {json.dumps(p.get("key_facts", {}), ensure_ascii=False)}. '
            f'(noticed because: {p.get("moment")})'
        )
    catalogue = "\n".join(lines)
    ctx_bits = []
    stress = payload.get("stress")
    if stress is not None:
        ctx_bits.append(f"financial-stress score {stress:.2f} (0-1, higher = more strain)")
    context = "; ".join(ctx_bits) or "nothing unusual noted"
    return (
        f"{_customer_line(payload)}\n"
        f"Context to weigh: {context}.\n\n"
        f"APEX has already vetted these products as eligible, not already held, and ethically "
        f"appropriate for this customer right now:\n{catalogue}\n\n"
        f"Choose the SINGLE product that best fits THIS specific person at this moment — weigh their "
        f"situation, don't just take the first option — then write the outreach for it.\n"
        f"Reply with ONLY a JSON object, no prose:\n"
        f'{{"product_id": "<exactly one id from the list above>", '
        f'"reason": "<one short internal sentence: why this product fits this person now>", '
        f'"message": "<the {lang} message to the customer>"}}\n'
        f"The message must follow every rule above: 2-4 sentences, in {lang}, no jargon, calm, no "
        f"links, no pressure — describe the life benefit, never name the product."
    )


def build_reengage_prompt(payload: dict) -> str:
    """The follow-up after a deliberate WAIT. A while ago APEX detected a
    sensitive moment and chose NOT to reach out. Now the acute window has passed, so it offers a
    single warm, product-free check-in — never naming the sensitive event, never pushing anything."""
    c = payload["customer"]
    lang = LANG_NAMES.get(c.get("language_pref"), "English")
    return (
        f"{_customer_line(payload)}\n"
        f"A while ago APEX noticed a sensitive moment in this person's finances "
        f"(internal signal: {payload['signal_type']}) and deliberately chose NOT to reach out, to "
        f"avoid intruding. About {payload.get('days_since')} day(s) have passed and the acute moment "
        f"appears to have settled.\n\n"
        f"Write a {lang} message: a brief, warm check-in. Do NOT mention anything specific or private "
        f"(no medical bills, debts, large expenses, or the reason you noticed). Offer no product and "
        f"no link — only let them know APEX is here if they'd like to talk anything through about "
        f"their money. 2-3 sentences, calm, no jargon, no pressure. Output only the message text."
    )


def build_explain_prompt(payload: dict) -> str:
    """Customer-facing "why am I seeing this?" — a constrained explanation built ONLY from a fact the
    customer can already see in their own account. The sensitive/vulnerability case never reaches this
    prompt (the endpoint declines before calling the LLM), so here we can always name the visible
    reason plainly."""
    c = payload["customer"]
    lang = LANG_NAMES.get(c.get("language_pref"), "English")
    fact = payload.get("source_ref") or payload["signal_type"].replace("_", " ")
    p = payload.get("product")
    prod_line = (f"It points toward this kind of help (describe the life benefit, never name a "
                 f"product): {p['name']} — {p.get('description', '')}." if p else "")
    return (
        f"The customer ({c.get('first_name')}) asked: \"Why am I seeing this?\"\n"
        f"APEX reached out because of something visible in their OWN account: {fact}.\n"
        f"{prod_line}\n\n"
        f"Explain in {lang}, in 1-2 calm sentences, why they are seeing this — using ONLY that fact "
        f"about their own account. Do NOT mention internal scores, models, predictions, or anything "
        f"inferred or sensitive. No jargon, no pressure, no links. Output only the explanation."
    )
