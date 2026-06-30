"""'Simulate 3 months of activity' demo mechanic.

Seeds ONE customer's three months of synthetic activity — the seam where SBI's internal
data would start flowing — then scores, detects, and reasons for just that customer. This
is the Guide→Analyser transition on demand: a customer who had no data suddenly has it, and
the agent springs into action.

Batch insert, not Kafka (correct for a one-time finite seed; streaming is the *production*
answer for periodic syncs at scale). Each scenario keeps a single demo customer, refreshed
on every run (identified by the demo email domain), so repeated clicks don't accumulate.
"""
from __future__ import annotations

from .database.db import SessionLocal
from .generator.generate import build_persona
from .generator.personas import t
from .database.models import (
    Account, Action, AppSession, Customer, Decision, Holding, Outcome, Score, Signal,
    Transaction,
)

DEMO_DOMAIN = "demo.apex"

# Scenario specs (PERSONAS-style) — each demonstrates a different signal/transition.
SCENARIOS = {
    "idle_balance": {
        "label": "Idle balance → savings nudge",
        "key": "demo_idle", "name": "Aarav Khanna", "age": 35, "gender": "M",
        "city_tier": "metro", "language_pref": "en", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 95000,
        "accounts": [{"type": "acc_insta_plus", "balance": 300000}],
        "holdings": [{"product_id": "ins_eshield_insta", "current_value": 3000000}],
        "traits": [t("salary", amount=95000), t("baseline"), t("idle"), t("sessions", mode="healthy")],
    },
    "manual_bill": {
        "label": "Manual recurring bill → autopay",
        "key": "demo_bill", "name": "Neha Joshi", "age": 40, "gender": "F",
        "city_tier": "tier_2", "language_pref": "hi", "occupation": "self_employed",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 72000,
        "accounts": [{"type": "acc_insta_plus", "balance": 65000}],
        "holdings": [{"product_id": "ins_eshield_insta", "current_value": 2000000}],
        "traits": [t("baseline"), t("manual_bill", payee="BESCOM_POWER", amount=2400, count=6),
                   t("sessions", mode="healthy")],
    },
    "life_event": {
        "label": "Medical event → restraint (wait)",
        "key": "demo_life", "name": "Sunita Rao", "age": 39, "gender": "F",
        "city_tier": "metro", "language_pref": "en", "occupation": "salaried",
        "customer_type": "existing", "kyc_status": "complete", "monthly_income": 115000,
        "accounts": [{"type": "acc_insta_plus", "balance": 160000}],
        "holdings": [],
        "traits": [t("salary", amount=115000), t("baseline"), t("medical_anomaly", amount=95000),
                   t("sessions", mode="healthy")],
    },
}


def _empty_bucket() -> dict:
    return {"customers": [], "accounts": [], "holdings": [], "txns": [],
            "sessions": [], "applications": [], "manifest": {}}


def _reset_demo(session, email: str):
    """Delete the prior demo customer for this scenario + all their rows (FK-safe order)."""
    ids = [c.customer_id for c in session.query(Customer).filter(Customer.email == email)]
    if not ids:
        return
    for model in (Outcome, Action, Decision, Signal, Score, Transaction, AppSession,
                  Holding, Account):
        session.query(model).filter(model.customer_id.in_(ids)).delete(synchronize_session=False)
    session.query(Customer).filter(Customer.customer_id.in_(ids)).delete(synchronize_session=False)


def simulate(scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise KeyError(scenario)
    spec = dict(SCENARIOS[scenario])
    spec["email"] = f"{spec['key']}@{DEMO_DOMAIN}"

    with SessionLocal() as session:
        _reset_demo(session, spec["email"])
        bucket = _empty_bucket()
        build_persona(spec, bucket)
        customer_id = str(bucket["customers"][0].customer_id)
        for key in ("customers", "accounts", "holdings", "txns", "sessions", "applications"):
            session.add_all(bucket[key])
            session.flush()
        session.commit()

    # Detection runs immediately (demo pacing), scoped agent reasoning for this customer only.
    from .ml.score import score_all
    from .signals.detect import detect_all
    from .agent.loop import run as run_agent
    score_all()
    detect_all()
    run_agent(customer_id=customer_id)

    # Gather the customer-facing outreach (the messages APEX would send, or its restraint),
    # so the customer site can show the result without exposing the internal reasoning trace.
    with SessionLocal() as session:
        actions = {a.decision_id: a for a in
                   session.query(Action).filter(Action.customer_id == customer_id)}
        outreach = []
        for d in session.query(Decision).filter(Decision.customer_id == customer_id) \
                .order_by(Decision.created_at):
            a = actions.get(d.decision_id)
            outreach.append({
                "outcome": d.outcome,
                "product_id": d.product_id,
                "message_text": a.message_text if a else None,
                "deep_link": a.deep_link if a else None,
            })
        cust = session.get(Customer, customer_id)
        lang = cust.language_pref if cust else None

    return {"customer_id": customer_id, "scenario": scenario, "name": spec["name"],
            "language_pref": lang, "outreach": outreach}
