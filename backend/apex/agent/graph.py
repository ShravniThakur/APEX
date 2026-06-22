"""The Analyser reasoning loop as a LangGraph flow.

    route → hypothesise (LLM) → critique (LLM) → decide (CODE GATE) → [compose (LLM) if act] → END

The LLM reasons (hypothesise, critique) and writes (compose), but it never decides whether to
act. `decide` is the deterministic safety gate (guardrails.evaluate) — bright-line ethics
(e.g. life_event → wait) are guaranteed in code, not requested in a prompt. This is the
"LLM proposes, code disposes" hybrid: flexible reasoning, guaranteed restraint.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from . import guardrails, llm, routing


class AnalyserState(TypedDict, total=False):
    # inputs
    signal_type: str
    source_ref: str
    ctx: Any                 # AgentContext (cust, accounts, holdings, scores, products)
    # filled by nodes
    candidates: list
    product_id: str | None
    product: dict | None
    hypothesis: str
    passes: int              # how many hypothesise passes have run (caps the critique loop-back)
    critique: str
    critique_flag: bool      # True when self-critique raised a HOLD concern
    outcome: str
    authority_level: int | None
    confidence: float
    reason: str              # the gate's reason (auditable)
    message_text: str


def _payload(state: AnalyserState) -> dict:
    ctx = state["ctx"]
    c = ctx.cust
    p = state.get("product")
    return {
        "customer": {
            "first_name": c.name.split()[0], "age": c.age, "occupation": c.occupation,
            "city_tier": c.city_tier, "language_pref": c.language_pref,
        },
        "signal_type": state["signal_type"], "source_ref": state.get("source_ref"),
        "hypothesis": state.get("hypothesis"),
        "product": ({"name": p["name"], "description": p.get("description", ""),
                     "key_facts": p.get("key_facts", {})} if p else None),
        # Evidence the self-critique weighs (so its judgement is grounded, not decorative):
        "product_category": (p or {}).get("category") if p else None,
        "dismissals": getattr(ctx, "history", {}) or {},
        "stress": (ctx.scores.get("stress") or {}).get("score"),
    }


# --- nodes --- #
def node_route(state: AnalyserState) -> dict:
    """Mechanical hypothesise: deterministic product routing + eligibility.
    source_ref carries the target category for `stated_intent` signals (ignored by others)."""
    chosen, candidates = routing.select(state["signal_type"], state["ctx"], state.get("source_ref"))
    product = state["ctx"].products.get(chosen) if chosen else None
    return {"product_id": chosen, "candidates": candidates, "product": product}


def node_hypothesise(state: AnalyserState) -> dict:
    return {"hypothesis": llm.hypothesise(_payload(state)), "passes": state.get("passes", 0) + 1}


def node_critique(state: AnalyserState) -> dict:
    text = llm.critique(_payload(state))
    # The critique is asked to begin with PROCEED or HOLD; a HOLD is a real concern that the
    # deterministic gate will honour (it can only make the decision more cautious, never act).
    flag = text.strip().upper().startswith("HOLD")
    return {"critique": text, "critique_flag": flag}


def node_decide(state: AnalyserState) -> dict:
    """THE CODE GATE. Deterministic act/wait/escalate — overrides anything the LLM implied.
    The self-critique can VETO toward caution (act → wait), but can never upgrade to act."""
    out = guardrails.evaluate(state["signal_type"], state["ctx"], state.get("source_ref"))
    outcome, reason = out.outcome, out.reason
    if state.get("critique_flag") and outcome == "act":
        outcome = "wait"
        reason = f"{reason} | self-critique flagged a concern — holding rather than acting."
    product = state["ctx"].products.get(out.product_id) if out.product_id else None
    return {
        "outcome": outcome, "authority_level": out.authority_level,
        "confidence": out.confidence, "reason": reason,
        "product_id": out.product_id, "product": product,
    }


def node_compose(state: AnalyserState) -> dict:
    return {"message_text": llm.compose(_payload(state))}


def _after_critique(state: AnalyserState) -> str:
    # If the critique raised a concern, loop back to re-reason ONCE (a real reflect-and-revise
    # loop), capped at 2 hypothesise passes so it can't spin. Otherwise go to the gate.
    if state.get("critique_flag") and state.get("passes", 0) < 2:
        return "hypothesise"
    return "decide"


def _after_decide(state: AnalyserState) -> str:
    # Only compose a customer message when the gate said ACT.
    return "compose" if state.get("outcome") == "act" else "end"


def _build():
    g = StateGraph(AnalyserState)
    g.add_node("route", node_route)
    g.add_node("hypothesise", node_hypothesise)
    g.add_node("critique", node_critique)
    g.add_node("decide", node_decide)
    g.add_node("compose", node_compose)

    g.set_entry_point("route")
    g.add_edge("route", "hypothesise")
    g.add_edge("hypothesise", "critique")
    g.add_conditional_edges("critique", _after_critique, {"hypothesise": "hypothesise", "decide": "decide"})
    g.add_conditional_edges("decide", _after_decide, {"compose": "compose", "end": END})
    g.add_edge("compose", END)
    return g.compile()


analyser_app = _build()
