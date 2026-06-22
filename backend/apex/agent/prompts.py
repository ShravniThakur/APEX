"""Prompt construction for the LangGraph Analyser nodes (APEX_README §2 philosophy).

Three separate LLM steps: hypothesise (read the moment), critique (reflect on whether to
reach out), and compose (write the customer message). The LLM never *decides* act/wait/
escalate — that's the deterministic code gate (guardrails.py). Hypothesise/critique are
internal reasoning notes; only compose is customer-facing.
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


def _product_line(payload: dict) -> str:
    p = payload.get("product")
    if not p:
        return "No specific product is being considered."
    return (f"Product under consideration (for your understanding — describe its life benefit, "
            f"never name it as a product): {p['name']} — {p.get('description', '')} "
            f"Key facts: {json.dumps(p.get('key_facts', {}), ensure_ascii=False)}")


def build_hypothesise_prompt(payload: dict) -> str:
    return (
        f"{_customer_line(payload)}\n"
        f"Detected signal: {payload['signal_type']} ({payload.get('source_ref')}).\n"
        f"{_product_line(payload)}\n\n"
        "Internal note (not shown to the customer): in one or two sentences, what real moment in "
        "this person's financial life does this signal most likely reflect? Reason about their "
        "situation, not the product."
    )


def build_critique_prompt(payload: dict) -> str:
    cat = payload.get("product_category")
    dismiss_n = (payload.get("dismissals") or {}).get(cat, 0) if cat else 0
    stress = payload.get("stress")
    bits = []
    if dismiss_n:
        bits.append(f"the customer has dismissed '{cat}' suggestions {dismiss_n} time(s) before")
    if stress is not None:
        bits.append(f"current financial-stress score is {stress:.2f} (0-1, higher = more strain)")
    evidence = "; ".join(bits) if bits else "no prior dismissals on record, stress not elevated"
    return (
        f"{_customer_line(payload)}\n"
        f"Detected signal: {payload['signal_type']} ({payload.get('source_ref')}).\n"
        f"Your reading of the moment: {payload.get('hypothesis')}\n"
        f"{_product_line(payload)}\n"
        f"Evidence to weigh: {evidence}.\n\n"
        "Internal note (not shown to the customer): decide whether reaching out right now is "
        "appropriate and restrained. Repeated past dismissals of this category, or a vulnerable / "
        "high-stress moment, are strong reasons to hold back — be the voice of caution on the "
        "customer's side. Begin your reply with exactly 'PROCEED' or 'HOLD', then one sentence of why."
    )


def build_reengage_prompt(payload: dict) -> str:
    """The follow-up after a deliberate WAIT (APEX_README §6). A while ago APEX detected a
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


def build_compose_prompt(payload: dict) -> str:
    c = payload["customer"]
    lang = LANG_NAMES.get(c.get("language_pref"), "English")
    return (
        f"{_customer_line(payload)}\n"
        f"Detected signal: {payload['signal_type']} ({payload.get('source_ref')}).\n"
        f"Your reading: {payload.get('hypothesis')}\n"
        f"{_product_line(payload)}\n\n"
        f"Write a {lang} message to the customer following every rule above (2-4 sentences, no "
        f"jargon, calm, no links, no pressure). Output only the message text — no preamble."
    )
