"""Self-critique + Decide (specs APEX_README §6 ethical guardrail, §7 graduated authority).

Deterministic on purpose: whether to act on a vulnerability signal, and at what authority,
must never depend on an LLM's mood. The LLM explains these decisions; it does not make them.

evaluate() returns an Outcome describing what the agent will do for one signal.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import routing

# Default graduated-authority level per signal (1 insight · 2 one-tap · 3 standing rule).
AUTHORITY = {
    "dormancy": 1,
    "idle_balance": 2,                  # 3 if the chosen product is the auto-sweep standing rule
    "fiscal_year_end_window": 2,
    "sip_graduation": 2,
    "life_event": 1,                    # insight only (and gated to WAIT below)
    "large_asset_purchase": 1,
    "manual_recurring_payment": 2,
    "login_decay": 1,
    "sustained_rent_payment": 2,
    "tuition_payment": 2,
    "cash_flow_stress": 2,
    "gold_loan_liquidity_gap": 2,
    "salary_credit_upgrade": 2,
    "protection_gap": 2,
    "preapproved_card_offer": 2,
    "stated_intent": 2,                 # the customer asked → a one-tap handoff is appropriate
}

SEVERE_STRESS = 0.92                    # at/above this stress score, treat as a vulnerable moment
DISMISS_BACKOFF = 2                     # this many prior dismissals of a category → back off (wait)
VULNERABILITY_SIGNALS = {"life_event"}  # active signals that mark a vulnerable moment
# Unsecured debt — exploitable if mistimed. Secured lending (loan-against-FD, home, gold, auto) is
# deliberately NOT here: it's collateralised and far lower-risk, so it isn't suppressed.
UNSECURED_DEBT = {"loan_personal", "loan_pre_approved_personal", "card_credit"}


@dataclass
class Outcome:
    outcome: str                       # act | wait | escalate
    product_id: str | None
    candidates: list
    authority_level: int | None
    confidence: float
    reason: str                        # the critique result (why act/wait/escalate)


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def confidence(signal_type: str, ctx) -> float:
    """Derived from the margin of the driving score past its decision boundary; pure-rule
    signals are deterministic, so they get a high fixed confidence."""
    s = ctx.scores
    if signal_type == "cash_flow_stress":
        v = (s.get("stress") or {}).get("score", 0.0)
        return round(_clip((v - 0.80) / 0.20), 4)
    if signal_type == "gold_loan_liquidity_gap":
        v = (s.get("stress") or {}).get("score", 0.0)
        return round(_clip(0.6 + v * 0.3), 4)          # dip-pattern driven; moderate-high
    if signal_type == "login_decay":
        v = (s.get("engagement_decay") or {}).get("score", 0.0)
        return round(_clip((v - 0.30) / 0.70), 4)
    if signal_type in ("life_event", "large_asset_purchase"):
        mag = (s.get("anomaly") or {}).get("max_magnitude", 0.0)
        return round(_clip((mag - 3.5) / 6.5), 4)
    if signal_type == "churn_risk":
        v = (s.get("attrition") or {}).get("score", 0.0)
        return round(_clip((v - 0.80) / 0.20), 4)
    return 0.90                                          # deterministic rule signal


def _vulnerable(ctx) -> tuple[bool, str]:
    """Is the customer in a vulnerable moment? Either an active vulnerability signal (a recent
    medical event) or severe financial stress. Used to hold back the most exploitable categories
    (insurance, unsecured debt) no matter which signal is being processed."""
    active = getattr(ctx, "active_signals", set()) or set()
    if active & VULNERABILITY_SIGNALS:
        return True, "active life_event"
    stress = (ctx.scores.get("stress") or {}).get("score", 0.0)
    if stress >= SEVERE_STRESS:
        return True, f"severe financial stress ({stress:.2f})"
    return False, ""


def evaluate(signal_type: str, ctx, target: str | None = None) -> Outcome:
    conf = confidence(signal_type, ctx)
    chosen, candidates = routing.select(signal_type, ctx, target)
    authority = AUTHORITY.get(signal_type, 1)
    if signal_type == "idle_balance" and chosen == "dep_mod_autosweep":
        authority = 3                                   # auto-sweep is a set-once standing rule

    # --- ethical restraint: a vulnerability signal is never an immediate product push --- #
    if signal_type == "life_event":
        return Outcome("wait", chosen, candidates, 1, conf,
                       "vulnerability signal (medical) — acknowledge and wait; no immediate "
                       "product push. Offer insight only if the customer re-engages.")

    # --- churn risk: the trained attrition model says this customer is likely to leave. Don't
    #     auto-push products at someone heading for the door — escalate to a human RM for retention. --- #
    if signal_type == "churn_risk":
        return Outcome("escalate", None, candidates, None, conf,
                       "trained churn model flags high attrition risk — escalate to a human "
                       "relationship manager for retention rather than auto-pushing a product.")

    # --- nothing eligible to offer -> hand to a human / bank dashboard --- #
    if chosen is None:
        return Outcome("escalate", None, candidates, None, conf,
                       "no eligible product for this signal — route to bank-ops review.")

    vulnerable, why = _vulnerable(ctx)

    # --- a severely stressed customer whose own cash_flow_stress signal routes to UNSECURED debt is
    #     sent to a HUMAN (escalate), not silently held — they may have a real, urgent cash need that
    #     deserves judgement rather than an auto-offer of debt. (Runs before the holistic hold below
    #     so escalate wins for this specific case.) --- #
    if signal_type == "cash_flow_stress" and chosen in UNSECURED_DEBT:
        stress = (ctx.scores.get("stress") or {}).get("score", 0.0)
        if stress >= SEVERE_STRESS:
            return Outcome("escalate", chosen, candidates, None, conf,
                           f"severe stress ({stress:.2f}) with only unsecured debt available — "
                           "escalate for human judgement rather than auto-offering debt.")

    # --- holistic vulnerability restraint: if the customer is in a vulnerable moment (an active
    #     life_event OR severe financial stress), never let a DIFFERENT signal push the two most
    #     exploitable-if-mistimed categories — insurance (e.g. via protection_gap) or unsecured debt
    #     (e.g. a pre-approved loan / credit card via preapproved_card_offer). The restraint follows
    #     the customer, not the trigger; secured lending is left alone. --- #
    if vulnerable and signal_type not in VULNERABILITY_SIGNALS:
        chosen_cat = (ctx.products.get(chosen, {}) or {}).get("category")
        if chosen_cat == "insurance" or chosen in UNSECURED_DEBT:
            kind = "insurance" if chosen_cat == "insurance" else "unsecured debt"
            return Outcome("wait", chosen, candidates, authority, conf,
                           f"customer is in a vulnerable moment ({why}) — holding back {kind} "
                           "outreach regardless of other signals, to avoid exploiting the moment.")

    # --- redundancy: already holds the product (except dormancy, whose whole purpose is
    #     to re-engage an account the customer already holds) --- #
    held = {a.account_type for a in ctx.accounts} | {h.product_id for h in ctx.holdings}
    if signal_type != "dormancy" and chosen in held:
        return Outcome("wait", chosen, candidates, authority, conf,
                       "customer already holds this product — no action needed.")

    # --- dismissal-aware back-off: the customer has repeatedly rejected this category, so
    #     re-pushing it now is just nagging. The "memory" made causal and deterministic, read
    #     from the persisted outcome log via ctx.history (see loop.py). --- #
    category = (ctx.products.get(chosen, {}) or {}).get("category")
    dismiss_n = (getattr(ctx, "history", {}) or {}).get(category, 0)
    if dismiss_n >= DISMISS_BACKOFF:
        return Outcome("wait", chosen, candidates, authority, conf,
                       f"customer has dismissed '{category}' {dismiss_n}× before — backing off "
                       "rather than re-pushing the same category.")

    return Outcome("act", chosen, candidates, authority, conf,
                   f"eligible and unheld; offer {chosen} at authority level {authority}.")
