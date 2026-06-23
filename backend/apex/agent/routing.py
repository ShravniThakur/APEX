"""Deterministic signal -> product candidates + eligibility (specs/signals.md routing branches).

A signal proposes an ordered (best-first) candidate list, branched by what the customer
holds/qualifies for; `is_eligible` then filters it. The result is the *relevance-ranked,
eligible* set — code decides what's APPROPRIATE and ALLOWED, which is what keeps the ethical
guardrails trustworthy. Within that vetted set the Analyser LLM picks the single best fit for
the person (guardrails.decide_customer + loop.py); it can never reach a product not listed here.

Each signal maps to a `route(ctx) -> list[product_id]` ordered best-first. application_dropoff
is Guide-mode (conversational onboarding resume) and is intentionally NOT handled here.
"""
from __future__ import annotations

# Analyser-mode signals (everything except the Guide-mode application_dropoff).
ANALYSER_SIGNALS = {
    "dormancy", "idle_balance", "fiscal_year_end_window", "sip_graduation", "life_event",
    "large_asset_purchase", "manual_recurring_payment", "login_decay", "sustained_rent_payment",
    "tuition_payment", "cash_flow_stress", "gold_loan_liquidity_gap", "salary_credit_upgrade",
    "protection_gap", "preapproved_card_offer",
    "stated_intent",   # conversational: a product interest the customer voiced in Concierge chat
    "churn_risk",      # trained attrition model → escalate to a human RM (no product push)
}

GUIDE_SIGNALS = {"application_dropoff"}


def _holds(ctx, *product_ids) -> bool:
    held = {a.account_type for a in ctx.accounts} | {h.product_id for h in ctx.holdings}
    return any(p in held for p in product_ids)


def _holds_category(ctx, category: str) -> bool:
    """True if the customer holds any product in `category` (uses the products lookup)."""
    held = {a.account_type for a in ctx.accounts} | {h.product_id for h in ctx.holdings}
    return any(ctx.products.get(p, {}).get("category") == category for p in held)


# --------------------------------------------------------------------------- #
# Per-signal routing (ordered best-first; eligibility filtering happens after)
# --------------------------------------------------------------------------- #
def route(signal_type: str, ctx, target: str | None = None) -> list[str]:
    cust = ctx.cust
    if signal_type == "stated_intent":
        # `target` = the product category the customer explicitly asked about in conversation.
        # Offer the full-depth products in that category; eligibility + the ethical gate run after.
        return [pid for pid, p in ctx.products.items()
                if p.get("category") == target and p.get("depth") == "full"]
    if signal_type == "churn_risk":
        return []          # no product push — the gate escalates to a human RM for retention
    if signal_type == "dormancy":
        return ["acc_insta_plus"]                       # reactivation nudge (insight)
    if signal_type == "idle_balance":
        # standing-rule sweep first (Level 3), then growth / conservative options
        return ["dep_mod_autosweep", "inv_jannivesh_sip", "dep_fd_regular", "dep_rd"]
    if signal_type == "fiscal_year_end_window":
        # NPS only once 80C is already covered (holds a tax-saving product)
        if _holds_tax_saving(ctx):
            return ["inv_nps"]
        return ["dep_tax_saver_fd", "inv_ppf"]
    if signal_type == "sip_graduation":
        return ["inv_sbi_mutual_fund"]
    if signal_type == "life_event":
        return ["ins_eshield_insta"]                    # routed, but guardrail forces WAIT
    if signal_type == "large_asset_purchase":
        return ["loan_auto", "ins_general"]
    if signal_type == "manual_recurring_payment":
        return ["pay_epay_autopay"]
    if signal_type == "login_decay":
        return ["pay_yono_cash"]
    if signal_type == "sustained_rent_payment":
        return ["loan_home"]
    if signal_type == "tuition_payment":
        return ["loan_education"]
    if signal_type == "cash_flow_stress":
        # priority by least-cost collateral / offer
        if cust.has_papl_offer:
            return ["loan_pre_approved_personal"]
        if _holds(ctx, "dep_fd_regular", "dep_tax_saver_fd"):
            return ["loan_against_fd"]
        if _holds_category(ctx, "investments"):
            return ["loan_against_mf"]
        return ["loan_personal"]
    if signal_type == "gold_loan_liquidity_gap":
        return ["loan_gold"]
    if signal_type == "salary_credit_upgrade":
        return ["acc_salary_package"]
    if signal_type == "protection_gap":
        return ["ins_pmjjby", "ins_pmsby"]              # ultra-low-cost life + accident
    if signal_type == "preapproved_card_offer":
        return ["card_credit"]
    return []


def _holds_tax_saving(ctx) -> bool:
    held = {a.account_type for a in ctx.accounts} | {h.product_id for h in ctx.holdings}
    return any(ctx.products.get(p, {}).get("tax_saving") for p in held)


# --------------------------------------------------------------------------- #
# Eligibility — check the rules we can actually evaluate for our customers.
# Unknown rule keys pass through (we never fabricate a check we can't honor).
# --------------------------------------------------------------------------- #
def is_eligible(product_id: str, ctx, signal_type: str | None = None) -> bool:
    cust = ctx.cust
    rules = (ctx.products.get(product_id, {}) or {}).get("eligibility_rules") or {}
    income = float(cust.monthly_income or 0)

    if "min_age" in rules and (cust.age or 0) < rules["min_age"]:
        return False
    if "max_age" in rules and (cust.age or 0) > rules["max_age"]:
        return False
    if rules.get("requires_income") and income <= 0:
        return False
    if "min_monthly_income" in rules and income < rules["min_monthly_income"]:
        return False
    if rules.get("requires_papl_offer") and not cust.has_papl_offer:
        return False
    if rules.get("requires_card_offer") and not cust.has_card_offer:
        return False
    if (rules.get("requires_owns_gold") or rules.get("requires_gold_collateral")) and not cust.owns_gold:
        return False
    if rules.get("requires_dependents") and (cust.dependents or 0) <= 0:
        return False
    if rules.get("requires_existing_fd") and not _holds(ctx, "dep_fd_regular", "dep_tax_saver_fd"):
        return False
    if rules.get("requires_mf_holdings") and not _holds_category(ctx, "investments"):
        return False
    if rules.get("requires_existing_account") and not ctx.accounts:
        return False
    if rules.get("requires_new_to_bank") and ctx.accounts and signal_type != "dormancy":
        # dormancy 'reactivation' names Insta Plus but the customer is existing — treat as
        # a reactivation insight, not a fresh open: don't disqualify on new-to-bank.
        return False
    return True


def select(signal_type: str, ctx, target: str | None = None) -> tuple[str | None, list[str]]:
    """Return (chosen_product_id, all_eligible_candidates). chosen = first eligible.
    `target` is only used by `stated_intent` (the category the customer asked about)."""
    candidates = [p for p in route(signal_type, ctx, target) if is_eligible(p, ctx, signal_type)]
    return (candidates[0] if candidates else None), candidates
