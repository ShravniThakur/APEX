"""The 17 signal detectors (specs/signals.md).

Each detector is a pure function of a per-customer `Context` and returns a short
`source_ref` string when the signal fires, or `None` when it doesn't. No DB access —
`detect.py` builds the context and persists the SIGNALS rows.

Pure-rule signals read raw data only; five read a SCORES value produced by the ML layer:
cash_flow_stress←stress, life_event/large_asset_purchase←anomaly, login_decay←engagement_decay,
churn_risk←attrition. (gold_loan_liquidity_gap is a pure raw rule despite being a liquidity signal.)
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from . import thresholds as T


@dataclass
class Context:
    cust: object
    accounts: list = field(default_factory=list)
    txns: list = field(default_factory=list)
    sessions: list = field(default_factory=list)        # list[datetime] of login times
    holdings: list = field(default_factory=list)
    application: object | None = None
    scores: dict = field(default_factory=dict)          # {score_type: value_dict}
    now: datetime = field(default_factory=datetime.now)
    tax_saving_products: set = field(default_factory=set)
    insurance_products: set = field(default_factory=set)


def _days(now: datetime, dt: datetime) -> float:
    return (now - dt).total_seconds() / 86400.0


def _held_product_ids(ctx: Context) -> set:
    return {a.account_type for a in ctx.accounts} | {h.product_id for h in ctx.holdings}


def _group_debits_by_payee(ctx: Context) -> dict:
    g = defaultdict(list)
    for t in ctx.txns:
        if t.direction == "debit" and t.payee_id:
            g[t.payee_id].append(t)
    return g


# --------------------------------------------------------------------------- #
# Pure-rule detectors
# --------------------------------------------------------------------------- #
def dormancy(ctx: Context):
    if not ctx.accounts:               # no account -> not a dormancy case (e.g. new applicant)
        return None
    last_txn = max((t.txn_time for t in ctx.txns), default=None)
    last_login = max(ctx.sessions, default=None)
    txn_idle = last_txn is None or _days(ctx.now, last_txn) >= T.DORMANCY_DAYS
    login_idle = last_login is None or _days(ctx.now, last_login) >= T.DORMANCY_DAYS
    if txn_idle and login_idle:
        return "no txn/login >= 90d"
    return None


def application_dropoff(ctx: Context):
    a = ctx.application
    if not a or a.status != "in_progress" or not a.last_updated_at:
        return None
    stalled_h = _days(ctx.now, a.last_updated_at) * 24
    if stalled_h >= T.APPLICATION_STALL_HOURS and a.current_step in T.APPLICATION_DROPOFF_STEPS:
        return f"stalled {int(stalled_h)}h at {a.current_step}"
    return None


def idle_balance(ctx: Context):
    max_bal = max((float(a.balance) for a in ctx.accounts), default=0.0)
    if max_bal <= T.IDLE_BALANCE_MIN:
        return None
    large_outflow = any(
        t.direction == "debit" and float(t.amount) >= T.LARGE_OUTFLOW_MIN
        and _days(ctx.now, t.txn_time) <= T.IDLE_WINDOW_DAYS
        for t in ctx.txns
    )
    if large_outflow:
        return None
    return f"balance {int(max_bal)} idle, no large outflow"


def fiscal_year_end_window(ctx: Context):
    if ctx.now.month not in T.FISCAL_YEAR_END_MONTHS:
        return None
    if idle_balance(ctx) is None:                          # needs idle balance
        return None
    if _held_product_ids(ctx) & ctx.tax_saving_products:   # already holds a tax-saving product
        return None
    return "Jan-Mar + idle + no tax-saving product"


def sip_graduation(ctx: Context):
    for a in ctx.accounts:
        if a.account_type == T.SIP_PRODUCT_ID and a.opened_date:
            age = (ctx.now.date() - a.opened_date).days
            if age > T.SIP_GRADUATION_MIN_AGE_DAYS and float(a.balance) > 0:
                return f"SIP age {age}d, balance growing"
    return None


def manual_recurring_payment(ctx: Context):
    for payee, ts in _group_debits_by_payee(ctx).items():
        recurring = [
            t for t in ts
            if (t.channel or "") != "autopay"
            and t.merchant_category not in T.MANUAL_RECURRING_EXCLUDE_CATEGORIES
            and _days(ctx.now, t.txn_time) <= T.MANUAL_RECURRING_WINDOW_DAYS
        ]
        if len(recurring) >= T.MANUAL_RECURRING_MIN_COUNT:
            return f"{len(recurring)}x manual to {payee}"
    return None


def sustained_rent_payment(ctx: Context):
    if ctx.cust.owns_property:
        return None
    for payee, ts in _group_debits_by_payee(ctx).items():
        rent = [t for t in ts if t.merchant_category == "rent"]
        if len(rent) >= T.RENT_MIN_MONTHS:
            return f"{len(rent)} rent payments to {payee}"
    return None


def tuition_payment(ctx: Context):
    if (ctx.cust.dependents or 0) <= 0:
        return None
    for payee, ts in _group_debits_by_payee(ctx).items():
        edu = [t for t in ts if t.merchant_category == "education"]
        if len(edu) >= T.TUITION_MIN_COUNT:
            return f"{len(edu)} education payments to {payee}"
    return None


def salary_credit_upgrade(ctx: Context):
    has_salary = any(t.merchant_category == "salary" and t.direction == "credit" for t in ctx.txns)
    if not has_salary:
        return None
    if any(a.account_type in T.SALARY_UPGRADE_ACCOUNT_TYPES for a in ctx.accounts):
        return "salary landing in plain regular savings"
    return None


def protection_gap(ctx: Context):
    if not (T.PROTECTION_GAP_MIN_AGE <= (ctx.cust.age or 0) <= T.PROTECTION_GAP_MAX_AGE):
        return None
    has_income = (ctx.cust.monthly_income or 0) > 0 or any(
        t.merchant_category == "salary" for t in ctx.txns
    )
    if not has_income:
        return None
    if _held_product_ids(ctx) & ctx.insurance_products:
        return None
    return "income, no insurance held"


def preapproved_card_offer(ctx: Context):
    if not ctx.cust.has_card_offer:
        return None
    if any(t.direction == "debit" for t in ctx.txns):
        return "card offer + active spend"
    return None


# --------------------------------------------------------------------------- #
# Score-consuming detectors
# --------------------------------------------------------------------------- #
def cash_flow_stress(ctx: Context):
    score = (ctx.scores.get("stress") or {}).get("score")
    if score is not None and score >= T.STRESS_THRESHOLD:
        return f"stress={score}"
    return None


def gold_loan_liquidity_gap(ctx: Context):
    if not ctx.cust.owns_gold:
        return None
    dips = [
        t for t in ctx.txns
        if t.direction == "debit" and float(t.amount) <= T.GOLD_DIP_MAX_AMOUNT
        and _days(ctx.now, t.txn_time) <= T.GOLD_DIP_WINDOW_DAYS
    ]
    if len(dips) >= T.GOLD_DIP_MIN_COUNT:
        return f"{len(dips)} small dips, owns gold"
    return None


def life_event(ctx: Context):
    flagged = (ctx.scores.get("anomaly") or {}).get("flagged", [])
    medical = [f for f in flagged if f.get("category") == T.ANOMALY_MEDICAL_CATEGORY]
    if medical:
        return f"medical anomaly mag={medical[0]['magnitude']}"
    return None


def large_asset_purchase(ctx: Context):
    flagged = (ctx.scores.get("anomaly") or {}).get("flagged", [])
    asset = [f for f in flagged if f.get("category") in T.LARGE_ASSET_CATEGORIES]
    if asset:
        return f"{asset[0]['category']} anomaly mag={asset[0]['magnitude']}"
    return None


def login_decay(ctx: Context):
    score = (ctx.scores.get("engagement_decay") or {}).get("score")
    if score is not None and score >= T.LOGIN_DECAY_THRESHOLD:
        return f"engagement_decay={score}"
    return None


def churn_risk(ctx: Context):
    # The trained attrition model predicts this customer is likely to leave — an early warning
    # caught BEFORE the hard dormancy line (dormancy owns the already-gone case), so skip anyone
    # already dormant. This is the signal that makes the churn model do real work.
    if dormancy(ctx) is not None:
        return None
    score = (ctx.scores.get("attrition") or {}).get("score")
    if score is not None and score >= T.CHURN_RISK_THRESHOLD:
        return f"attrition={score}"
    return None


# Registry in spec order; names MUST match manifest expected_signals exactly.
DETECTORS = [
    ("dormancy", dormancy),
    ("application_dropoff", application_dropoff),
    ("idle_balance", idle_balance),
    ("fiscal_year_end_window", fiscal_year_end_window),
    ("sip_graduation", sip_graduation),
    ("life_event", life_event),
    ("large_asset_purchase", large_asset_purchase),
    ("manual_recurring_payment", manual_recurring_payment),
    ("login_decay", login_decay),
    ("sustained_rent_payment", sustained_rent_payment),
    ("tuition_payment", tuition_payment),
    ("cash_flow_stress", cash_flow_stress),
    ("gold_loan_liquidity_gap", gold_loan_liquidity_gap),
    ("salary_credit_upgrade", salary_credit_upgrade),
    ("protection_gap", protection_gap),
    ("preapproved_card_offer", preapproved_card_offer),
    ("churn_risk", churn_risk),
]
