"""Concierge mode as a LangGraph tool-calling agent.

Unlike context-injection (stuff a fixed blob into the prompt), here the LLM *decides which data
it needs* and calls read-only tools to fetch it — accurate computed answers, not arithmetic on
injected text. This is the legitimate use of LangGraph: dynamic, LLM-driven control flow.

    agent (LLM, may emit tool calls) ⇄ tools (run real DB lookups) → ... → final answer

Tools are read-only and scoped to ONE customer (the customer_id in state) — Concierge can never
read another customer's data.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.errors import GraphRecursionError

from ..config import GROQ_MODEL
from ..database.db import SessionLocal
from ..database.models import Account, Customer, Holding, Product, Score, Signal, Transaction
from . import guardrails
from .loop import AgentContext, _load_products
from .routing import ANALYSER_SIGNALS
from ._shared import LANG_NAMES, get_client

MAX_TOOL_ROUNDS = 4   # cap tool-call rounds, then force a final answer (prevents runaway loops)

CONCIERGE_SYSTEM = """You are APEX, a financial concierge inside SBI, talking with {name}, an \
existing customer, about their own money. You are on their side, not the bank's. You have tools to \
look up their real balance, spending, and holdings, to check affordability, and to list SBI \
products — USE them to answer accurately. Never guess or invent numbers; if a tool gives you the \
figure, use it.

When the customer asks what they should get or what is best for them, call recommend_product and \
base your answer ONLY on what it returns — it gives the products that are eligible, not already \
held, and ethically appropriate for this customer right now. Never invent a recommendation or name \
a product it didn't return; if it returns none, tell them there's nothing they need right now \
rather than inventing something. Never recommend a product the customer already holds.

Speak in plain life terms, no jargon (no SIP/NAV/CAGR). Be calm and concise. Reply in {lang}."""

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "get_balance", "description": "The customer's total balance across accounts.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_spending",
        "description": "The customer's spending by category over the last N days (default 90).",
        "parameters": {"type": "object", "properties": {
            "period_days": {"type": "integer", "description": "window in days, default 90"}}}}},
    {"type": "function", "function": {
        "name": "check_affordability",
        "description": "Whether the customer can comfortably afford a one-off purchase of `amount` rupees.",
        "parameters": {"type": "object", "properties": {
            "amount": {"type": "number", "description": "purchase amount in rupees"}},
            "required": ["amount"]}}},
    {"type": "function", "function": {
        "name": "get_holdings", "description": "Products and accounts the customer already holds.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "list_products",
        "description": "Browse the SBI catalogue, optionally filtered by category "
                       "(accounts, deposits, investments, loans, insurance, payments, cards). "
                       "For general 'what does SBI offer' questions. Each item has an 'already_held' "
                       "flag. To actually RECOMMEND something, use recommend_product instead.",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string", "description": "optional category filter"}}}}},
    {"type": "function", "function": {
        "name": "recommend_product",
        "description": "APEX's deterministically-vetted recommendations for THIS customer right now — "
                       "eligible, not already held, and ethically cleared (a vulnerable moment yields "
                       "no push). Use this whenever the customer asks what they should get; base your "
                       "answer only on what it returns. If it returns none, recommend nothing.",
        "parameters": {"type": "object", "properties": {
            "category": {"type": "string", "description": "optional category filter"}}}}},
]


# --- tool implementations (read-only, scoped to one customer; share the turn's DB session) --- #
def _get_balance(db, customer_id, **_):
    accts = db.query(Account).filter(Account.customer_id == customer_id).all()
    return {"total_balance": round(sum(float(a.balance or 0) for a in accts)),
            "accounts": [{"type": a.account_type, "balance": round(float(a.balance or 0))} for a in accts]}


def _get_spending(db, customer_id, period_days=90, **_):
    spend = defaultdict(float)
    for t in db.query(Transaction).filter(Transaction.customer_id == customer_id):
        if t.direction == "debit":
            spend[t.merchant_category or "other"] += float(t.amount)
    ordered = sorted(spend.items(), key=lambda kv: -kv[1])
    return {"period_days": period_days, "total": round(sum(spend.values())),
            "by_category": {k: round(v) for k, v in ordered}}


def _check_affordability(db, customer_id, amount, **_):
    amount = float(amount)
    c = db.get(Customer, customer_id)
    bal = sum(float(a.balance or 0) for a in db.query(Account).filter(Account.customer_id == customer_id))
    income = float(c.monthly_income or 0) if c else 0.0
    remaining = bal - amount
    return {"amount": round(amount), "balance": round(bal), "monthly_income": round(income),
            "remaining_after": round(remaining),
            "affordable": remaining >= 0,
            "comfortable": remaining >= income}  # keeps ~a month's income as cushion


def _get_holdings(db, customer_id, **_):
    names = {p.product_id: p.name for p in db.query(Product)}
    held = [names.get(a.account_type, a.account_type)
            for a in db.query(Account).filter(Account.customer_id == customer_id)]
    held += [names.get(h.product_id, h.product_id)
             for h in db.query(Holding).filter(Holding.customer_id == customer_id)]
    return {"holdings": held}


def _list_products(db, customer_id=None, category=None, **_):
    # Catalogue from the PRODUCTS table (single runtime source of truth), not the JSON file.
    # Each item carries 'already_held' so the model never re-recommends what the customer has.
    held = set()
    if customer_id:
        held = {a.account_type for a in db.query(Account).filter(Account.customer_id == customer_id)}
        held |= {h.product_id for h in db.query(Holding).filter(Holding.customer_id == customer_id)}
    q = db.query(Product).filter(Product.depth == "full")
    if category:
        q = q.filter(Product.category == category)
    return {"products": [{"name": p.name, "category": p.category, "primary_use": p.primary_use,
                          "link": p.landing_url, "already_held": p.product_id in held} for p in q]}


def _recommend_product(db, customer_id, category=None, **_):
    # Deterministic recommendations: run the SAME routing + eligibility + ethical gate the Analyser
    # uses (guardrails.evaluate) over this customer's live signals. The LLM only phrases the answer;
    # CODE decides the product — so Concierge can't suggest something ineligible, already held, or
    # inappropriate (a vulnerability signal resolves to 'wait', i.e. no push). Mirrors the Analyser's
    # "LLM proposes, code disposes" principle.
    cust = db.get(Customer, customer_id)
    if cust is None:
        return {"recommendations": []}
    products = _load_products(db)
    customer_signals = db.query(Signal).filter(Signal.customer_id == customer_id).all()
    ctx = AgentContext(
        cust=cust,
        accounts=db.query(Account).filter(Account.customer_id == customer_id).all(),
        holdings=db.query(Holding).filter(Holding.customer_id == customer_id).all(),
        scores={s.score_type: s.value for s in db.query(Score).filter(Score.customer_id == customer_id)},
        products=products,
        active_signals={s.signal_type for s in customer_signals},
    )
    recs, seen = [], set()
    for sig in customer_signals:
        if sig.signal_type not in ANALYSER_SIGNALS:
            continue
        out = guardrails.evaluate(sig.signal_type, ctx, sig.source_ref)
        if out.outcome != "act" or not out.product_id or out.product_id in seen:
            continue
        p = products.get(out.product_id, {})
        if category and p.get("category") != category:
            continue
        seen.add(out.product_id)
        recs.append({"product": p.get("name"), "category": p.get("category"),
                     "authority_level": out.authority_level, "link": p.get("landing_url"),
                     "why": out.reason})
    return {"recommendations": recs,
            "note": "Deterministically vetted (eligible, not held, ethically cleared). "
                    "If empty, recommend nothing — there is no pressing need right now."}


TOOL_FUNCS = {
    "get_balance": _get_balance, "get_spending": _get_spending,
    "check_affordability": _check_affordability, "get_holdings": _get_holdings,
    "list_products": _list_products, "recommend_product": _recommend_product,
}


class CState(TypedDict, total=False):
    messages: list[Any]
    customer_id: str
    db: Any                 # the turn's DB session, shared by every tool call
    tool_rounds: int        # how many tool rounds have run (capped by MAX_TOOL_ROUNDS)


def node_agent(state: CState) -> dict:
    # After MAX_TOOL_ROUNDS, stop offering tools and force a text answer — this is what
    # prevents a runaway tool-calling loop (the GraphRecursionError otherwise).
    force_answer = state.get("tool_rounds", 0) >= MAX_TOOL_ROUNDS
    resp = get_client().chat.completions.create(
        model=GROQ_MODEL, temperature=0.3,
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


def node_tools(state: CState) -> dict:
    results = []
    for tc in state["messages"][-1].get("tool_calls", []):
        name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"]["arguments"] or "{}")
            fn = TOOL_FUNCS.get(name)
            result = fn(state["db"], state["customer_id"], **args) if fn else {"error": f"unknown tool {name}"}
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"{type(exc).__name__}: {exc}"}
        results.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, default=str)})
    return {"messages": state["messages"] + results, "tool_rounds": state.get("tool_rounds", 0) + 1}


def _route(state: CState) -> str:
    return "tools" if state["messages"][-1].get("tool_calls") else "end"


def _build():
    g = StateGraph(CState)
    g.add_node("agent", node_agent)
    g.add_node("tools", node_tools)
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", _route, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")
    return g.compile()


concierge_app = _build()


def answer(customer_id: str, history: list[dict]) -> str:
    # One DB session for the whole turn, shared by every tool call via state["db"].
    with SessionLocal() as s:
        c = s.get(Customer, customer_id)
        lang = LANG_NAMES.get(c.language_pref, "English") if c else "English"
        name = c.name.split()[0] if c else "there"
        system = CONCIERGE_SYSTEM.format(name=name, lang=lang)
        messages = [{"role": "system", "content": system}]
        messages += [{"role": m["role"], "content": m["content"]}
                     for m in history if m.get("role") in ("user", "assistant")]
        try:
            final = concierge_app.invoke(
                {"messages": messages, "customer_id": customer_id, "db": s, "tool_rounds": 0},
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
