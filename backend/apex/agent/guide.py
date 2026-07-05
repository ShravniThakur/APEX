"""Guide mode — conversational onboarding for a NEW / prospective customer, as a LangGraph
tool-calling agent.

Like Concierge (concierge.py), the LLM *decides what it needs* and calls read-only tools — so the
facts it gives are grounded, never hallucinated. The two things a one-shot prompt can't do safely:
  • **documents** — recited from a model's memory would be unreliable; `get_required_documents`
    returns the real list.
  • **drop-off context** — whether this person has an unfinished application is *live* state in the
    `applications` table; `lookup_application` is the only way to know (the agentic core of Guide).

Deep links / pre-filled onboarding URLs are deliberately NOT built here (the pre-fill mechanism
doesn't work against SBI's real pages). Guide only ever surfaces a product's real `landing_url` — a
plain link to the official page — and never writes anything to SBI.

    agent (LLM, may emit tool calls) ⇄ tools (read-only catalogue / application lookups) → answer
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.errors import GraphRecursionError

from ..config import CHAT_MODEL, LLM_READY
from ..database.models import Application, Product
from ._shared import get_client

MAX_TOOL_ROUNDS = 4   # cap tool-call rounds, then force a final answer (prevents runaway loops)

# Product categories grouped by the life-need they serve (so `list_products` reads as a landscape,
# not a flat list, and Guide can surface relevant *adjacent* areas).
LIFE_NEEDS = [
    ("Save", ("accounts", "deposits")),
    ("Grow your money", ("investments",)),
    ("Borrow", ("loans",)),
    ("Protect your family", ("insurance",)),
    ("Pay & spend", ("payments", "cards")),
]

# Standard KYC documents, grounded in code (not recalled by the model). A base set everyone needs,
# plus per-category extras. Kept deterministic so Guide never misstates what's required.
_DOC_BASE = ["Aadhaar card", "PAN card", "a recent passport-size photo", "proof of address"]
_DOC_EXTRA = {
    "loans": ["income proof (salary slips or ITR)", "recent bank statements"],
    "cards": ["income proof (salary slips or ITR)"],
    "insurance": ["nominee details"],
}

GUIDE_SYSTEM = """You are APEX, an AI onboarding guide inside SBI, talking with a NEW or prospective \
customer. Help them choose the right account or product and understand what documents they need, in \
plain language. You do NOT have their banking data — ask simple questions to understand their need \
first. Be calm, on the customer's side, never pushy, no jargon. Reply in the customer's language; if \
you don't know it yet, mirror the language they write in.

Use your tools — never guess:
- To talk about what SBI offers, call list_products / get_product_details. Only ever share the \
official link a tool returns; NEVER invent or type a URL yourself. \
- Give the official link to the customer every time you mention a product, so they can click through to the real SBI page. \
- For "what documents do I need", call get_required_documents — never list documents from memory.
- {identity_line}

A new customer doesn't know what they don't know, so don't leave them with a partial picture — but \
NEVER dump a product list. After helping with their immediate need, gently surface ONE or TWO *other* \
areas that genuinely fit, framed as life outcomes, not product names ("a low-cost way to protect your \
family", not "PMJJBY"). One or two relevant mentions at a time — let them choose what to go deeper on."""

_IDENTITY_KNOWN = ("This person is already identified to APEX (signed in). Quietly call "
                   "lookup_application once at the start. ONLY if it returns an unfinished "
                   "application do you mention it — warmly acknowledge it, tell them what's needed "
                   "for the step they stopped at, and point them to the official page to continue. "
                   "If it returns none, say NOTHING about applications or drop-offs — just greet "
                   "them and help as a brand-new customer. Never tell anyone they 'don't have an "
                   "unfinished application'.")
_IDENTITY_ANON = ("This is an anonymous, brand-new visitor. Do NOT call lookup_application and do "
                  "NOT mention past, existing, or unfinished applications at all — only if the "
                  "customer themselves says they already started one should you ask for a reference "
                  "and look it up. Otherwise just help them open the right account from scratch.")

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "list_products",
        "description": "Browse the SBI catalogue grouped by life-need (Save / Grow / Borrow / "
                       "Protect / Pay), optionally filtered to one category "
                       "(accounts, deposits, investments, loans, insurance, payments, cards).",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string", "description": "optional category filter"}}}}},
    {"type": "function", "function": {
        "name": "get_product_details",
        "description": "Plain-language details for one product: what it's for, key facts, and its "
                       "official SBI link. Use this before recommending or linking anything.",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}}, "required": ["product_id"]}},
    },
    {"type": "function", "function": {
        "name": "get_required_documents",
        "description": "The real list of documents needed to open/apply for a given product.",
        "parameters": {"type": "object", "properties": {
            "product_id": {"type": "string"}}, "required": ["product_id"]}},
    },
    {"type": "function", "function": {
        "name": "lookup_application",
        "description": "Check whether this customer has an unfinished SBI application (and where they "
                       "stopped). Pass their reference if they gave one; otherwise it uses the "
                       "signed-in identity. Returns the product + the step they left off at, or none.",
        "parameters": {"type": "object", "properties": {
            "customer_ref": {"type": "string", "description": "optional phone/PAN/id the customer gave"}}}},
    },
]


# --- tool implementations (read-only; share the turn's DB session) --- #
def _products_by_cat(db):
    by_cat = defaultdict(list)
    for p in db.query(Product).filter(Product.depth == "full"):
        by_cat[p.category].append(p)
    return by_cat


def _list_products(db, identity, category=None, **_):
    by_cat = _products_by_cat(db)
    out = {}
    for label, cats in LIFE_NEEDS:
        items = [p for c in cats for p in by_cat.get(c, []) if (not category or p.category == category)]
        if items:
            out[label] = [{"product_id": p.product_id, "name": p.name,
                           "primary_use": p.primary_use or ""} for p in items]
    return {"by_life_need": out}


def _get_product_details(db, identity, product_id=None, **_):
    p = db.get(Product, product_id)
    if p is None:
        return {"error": f"no such product {product_id}"}
    return {"product_id": p.product_id, "name": p.name, "category": p.category,
            "primary_use": p.primary_use or "", "description": p.description or "",
            "key_facts": p.key_facts or {}, "link": p.landing_url}


def _get_required_documents(db, identity, product_id=None, **_):
    p = db.get(Product, product_id)
    if p is None:
        return {"error": f"no such product {product_id}"}
    docs = list(_DOC_BASE) + _DOC_EXTRA.get(p.category, [])
    return {"product": p.name, "documents": docs,
            "note": "Standard KYC; the exact list can vary slightly by branch."}


def _lookup_application(db, identity, customer_ref=None, **_):
    # Applications are keyed by str(customer_id) in customer_ref (see signals/detect.py). Prefer an
    # explicit ref the customer gave; else fall back to the signed-in identity.
    _silent = ("No unfinished application. Do NOT mention this to the customer — just continue "
               "normal onboarding as if for a new customer. (Only if they explicitly asked about "
               "an existing application may you say you couldn't find one.)")
    ref = customer_ref or identity
    if not ref:
        return {"found": False, "note": _silent}
    app = (db.query(Application)
             .filter(Application.customer_ref == str(ref),
                     Application.status.in_(("in_progress", "abandoned")))
             .order_by(Application.last_updated_at.desc()).first())
    if app is None:
        return {"found": False, "note": _silent}
    prod = db.get(Product, app.product_id) if app.product_id else None
    return {"found": True, "product": prod.name if prod else app.product_id,
            "product_id": app.product_id, "current_step": app.current_step,
            "status": app.status,
            "link": prod.landing_url if prod else None}


TOOL_FUNCS = {
    "list_products": _list_products, "get_product_details": _get_product_details,
    "get_required_documents": _get_required_documents, "lookup_application": _lookup_application,
}


class GState(TypedDict, total=False):
    messages: list[Any]
    db: Any                 # the turn's DB session, shared by every tool call
    identity: str | None    # signed-in customer_id, if any (else anonymous Tier-1 stranger)
    tool_rounds: int


def node_agent(state: GState) -> dict:
    force_answer = state.get("tool_rounds", 0) >= MAX_TOOL_ROUNDS
    resp = get_client().chat.completions.create(
        model=CHAT_MODEL, temperature=0.4,
        tool_choice="none" if force_answer else "auto",
        tools=TOOLS_SCHEMA, messages=state["messages"],
    )
    msg = resp.choices[0].message
    out = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls and not force_answer:
        out["tool_calls"] = [{"id": tc.id, "type": "function",
                              "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                             for tc in msg.tool_calls]
    return {"messages": state["messages"] + [out]}


def node_tools(state: GState) -> dict:
    results = []
    for tc in state["messages"][-1].get("tool_calls", []):
        name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"]["arguments"] or "{}")
            fn = TOOL_FUNCS.get(name)
            result = fn(state["db"], state.get("identity"), **args) if fn else {"error": f"unknown tool {name}"}
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"{type(exc).__name__}: {exc}"}
        results.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, default=str)})
    return {"messages": state["messages"] + results, "tool_rounds": state.get("tool_rounds", 0) + 1}


def _route(state: GState) -> str:
    return "tools" if state["messages"][-1].get("tool_calls") else "end"


def _build():
    g = StateGraph(GState)
    g.add_node("agent", node_agent)
    g.add_node("tools", node_tools)
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", _route, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")
    return g.compile()


guide_app = _build()


def reply(messages: list[dict], db, identity: str | None = None) -> str:
    if not LLM_READY:
        return "The assistant isn't configured yet (set LLM_PROVIDER=ollama, or add GROQ_API_KEY)."
    system = GUIDE_SYSTEM.format(identity_line=_IDENTITY_KNOWN if identity else _IDENTITY_ANON)
    convo = [{"role": "system", "content": system}]
    convo += [{"role": m["role"], "content": m["content"]}
              for m in messages if m.get("role") in ("user", "assistant")]
    try:
        final = guide_app.invoke(
            {"messages": convo, "db": db, "identity": identity, "tool_rounds": 0},
            {"recursion_limit": 25},
        )
    except GraphRecursionError:
        return "I couldn't work that out just now — could you rephrase or ask something simpler?"
    except Exception as exc:  # noqa: BLE001
        if type(exc).__name__ == "RateLimitError":
            return "I'm handling a lot of requests right now — give me a few seconds and ask again."
        return f"(assistant error: {type(exc).__name__})"
    for m in reversed(final["messages"]):
        if m.get("role") == "assistant" and m.get("content") and not m.get("tool_calls"):
            return m["content"]
    return ""