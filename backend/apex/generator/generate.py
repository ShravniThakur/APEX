"""Synthetic data generator engine.

Builds signal-personas (personas.py) + a noise population that trips nothing,
writes them to Postgres, and emits a manifest of expected signals per customer
for the future validation harness.

Usage:
    python -m apex.generator.generate            # append
    python -m apex.generator.generate --reset    # wipe synthetic data first
"""
from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import date, datetime, timedelta

from faker import Faker

from ..config import BACKEND_DIR, RANDOM_SEED
from ..database.db import SessionLocal
from ..shaping import shape_financial_history
from ..database.models import (
    Account, Application, AppSession, Customer, Holding, Transaction,
    Action, Decision, Outcome, Score, Signal,
)
from .personas import PERSONAS

NOW = datetime.now()
WINDOW_DAYS = 90
NOISE_COUNT = 30

rng = random.Random(RANDOM_SEED)
faker = Faker("en_IN")
Faker.seed(RANDOM_SEED)

SPEND_CATEGORIES = ["retail", "utility", "transfer", "retail", "retail"]
SPEND_CHANNELS = ["upi", "card", "upi", "upi"]


def _days_ago(n: float) -> datetime:
    return NOW - timedelta(days=n)


def _txn(bucket, acct, cust, amount, direction, category, channel, when, payee=None, manual=False):
    bucket["txns"].append(Transaction(
        account_id=acct.account_id, customer_id=cust.customer_id,
        amount=round(float(amount), 2), direction=direction, merchant_category=category,
        channel=channel, txn_time=when, payee_id=payee, is_manual_recurring=manual,
    ))


def _session(bucket, cust, when, duration, features, device="mobile"):
    bucket["sessions"].append(AppSession(
        customer_id=cust.customer_id, login_time=when,
        duration_seconds=duration, features_used=features, device_type=device,
    ))


# --------------------------------------------------------------------------- #
# Trait emitters
# --------------------------------------------------------------------------- #
def emit_salary(bucket, acct, cust, amount):
    for m in range(3):
        _txn(bucket, acct, cust, amount, "credit", "salary", "neft",
             _days_ago(m * 30 + 1), payee=f"EMPLOYER_{cust.customer_id.hex[:6]}")


def emit_baseline(bucket, acct, cust):
    for _ in range(rng.randint(15, 25)):
        _txn(bucket, acct, cust, rng.randint(150, 4000), "debit",
             rng.choice(SPEND_CATEGORIES), rng.choice(SPEND_CHANNELS),
             _days_ago(rng.uniform(0, WINDOW_DAYS)))


def emit_idle(bucket, acct, cust):
    pass  # idle = absence of a large outflow; baseline stays small, balance high


def emit_manual_bill(bucket, acct, cust, payee, amount, count):
    for i in range(count):
        _txn(bucket, acct, cust, amount + rng.randint(-200, 300), "debit", "utility",
             "upi", _days_ago(i * 30 + 3), payee=payee, manual=True)


def emit_rent(bucket, acct, cust, amount, months):
    for i in range(months):
        _txn(bucket, acct, cust, amount, "debit", "rent", "neft",
             _days_ago(i * 30 + 2), payee=f"LANDLORD_{cust.customer_id.hex[:6]}", manual=True)


def emit_tuition(bucket, acct, cust, amount):
    for i in range(2):  # seasonal lump sums
        _txn(bucket, acct, cust, amount, "debit", "education", "neft",
             _days_ago(i * 45 + 10), payee=f"SCHOOL_{cust.customer_id.hex[:6]}")


def emit_medical_anomaly(bucket, acct, cust, amount):
    _txn(bucket, acct, cust, amount, "debit", "medical", "card", _days_ago(18))


def emit_vehicle_anomaly(bucket, acct, cust, amount):
    _txn(bucket, acct, cust, amount, "debit", "vehicle", "neft", _days_ago(12))


def emit_stress(bucket, acct, cust):
    # Use the SAME shaping function the stress trainset uses (apex.shaping) at a high
    # stress level, so demo stress personas land in the model's learned "stressed" region.
    hist = shape_financial_history(cust.monthly_income, 0.85, rng)
    for t in hist["txns"]:
        channel = "neft" if t["direction"] == "credit" else rng.choice(SPEND_CHANNELS)
        _txn(bucket, acct, cust, t["amount"], t["direction"], t["merchant_category"],
             channel, _days_ago(t["days_ago"]))


def emit_gold_dips(bucket, acct, cust):
    for i in range(12):  # frequent small cash withdrawals, clustered recently
        _txn(bucket, acct, cust, rng.randint(800, 2500), "debit", "transfer", "cash",
             _days_ago(rng.uniform(0, 40)))


def emit_dormant_history(bucket, acct, cust):
    # one old transaction well outside the 90-day window; nothing recent
    _txn(bucket, acct, cust, 5000, "debit", "retail", "card", _days_ago(135))


def emit_sessions(bucket, cust, kind):
    feats = [["balance_check"], ["balance_check", "bill_pay"], ["fund_transfer"], ["balance_check", "invest"]]
    if kind == "none":
        return
    if kind == "healthy":
        for d in range(0, WINDOW_DAYS, rng.randint(2, 4)):
            _session(bucket, cust, _days_ago(d), rng.randint(40, 300), rng.choice(feats))
    elif kind == "decay":
        # frequent early in the window, sparse recently
        for d in range(45, WINDOW_DAYS, 3):      # older half: active
            _session(bucket, cust, _days_ago(d), rng.randint(60, 300), rng.choice(feats))
        for d in range(0, 45, 12):               # recent half: rare + shallow
            _session(bucket, cust, _days_ago(d), rng.randint(20, 60), ["balance_check"])


EMITTERS = {
    "salary": lambda b, a, c, p: emit_salary(b, a, c, p["amount"]),
    "baseline": lambda b, a, c, p: emit_baseline(b, a, c),
    "idle": lambda b, a, c, p: emit_idle(b, a, c),
    "manual_bill": lambda b, a, c, p: emit_manual_bill(b, a, c, p["payee"], p["amount"], p["count"]),
    "rent": lambda b, a, c, p: emit_rent(b, a, c, p["amount"], p["months"]),
    "tuition": lambda b, a, c, p: emit_tuition(b, a, c, p["amount"]),
    "medical_anomaly": lambda b, a, c, p: emit_medical_anomaly(b, a, c, p["amount"]),
    "vehicle_anomaly": lambda b, a, c, p: emit_vehicle_anomaly(b, a, c, p["amount"]),
    "stress": lambda b, a, c, p: emit_stress(b, a, c),
    "gold_dips": lambda b, a, c, p: emit_gold_dips(b, a, c),
    "dormant_history": lambda b, a, c, p: emit_dormant_history(b, a, c),
}


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _new_customer(spec) -> Customer:
    cid = uuid.uuid4()
    return Customer(
        customer_id=cid, name=spec["name"], age=spec["age"], gender=spec.get("gender"),
        city_tier=spec.get("city_tier"), language_pref=spec.get("language_pref"),
        occupation=spec.get("occupation"), kyc_status=spec.get("kyc_status"),
        customer_type=spec.get("customer_type", "existing"),
        email=spec.get("email") or spec["name"].lower().replace(" ", ".") + "@example.com",
        account_opened_date=None if spec.get("no_account") else date.today() - timedelta(days=rng.randint(200, 1500)),
        monthly_income=spec.get("monthly_income"),
        owns_property=spec.get("owns_property", False), dependents=spec.get("dependents", 0),
        owns_gold=spec.get("owns_gold", False), has_papl_offer=spec.get("has_papl_offer", False),
        has_card_offer=spec.get("has_card_offer", False),
    )


def build_persona(spec, bucket):
    cust = _new_customer(spec)
    bucket["customers"].append(cust)

    accounts = []
    for a in spec.get("accounts", []):
        acct = Account(
            account_id=uuid.uuid4(), customer_id=cust.customer_id, account_type=a["type"],
            balance=a.get("balance", 0), status=a.get("status", "active"),
            opened_date=date.today() - timedelta(days=a.get("opened_days_ago", rng.randint(200, 1500))),
        )
        accounts.append(acct)
        bucket["accounts"].append(acct)

    for h in spec.get("holdings", []):
        bucket["holdings"].append(Holding(
            holding_id=uuid.uuid4(), customer_id=cust.customer_id, product_id=h["product_id"],
            units=h.get("units", 1), current_value=h.get("current_value"),
            acquired_date=date.today() - timedelta(days=rng.randint(100, 1000)),
        ))

    primary = accounts[0] if accounts else None
    for trait in spec.get("traits", []):
        kind = trait["kind"]
        if kind == "sessions":
            emit_sessions(bucket, cust, trait.get("mode", "healthy"))
            continue
        if kind in EMITTERS and primary is not None:
            EMITTERS[kind](bucket, primary, cust, trait)

    app = spec.get("application")
    if app:
        # Link the application to this customer so application_dropoff is attributable.
        # customer_ref holds the customer_id here (spec allows phone/PAN/no-customer).
        bucket["applications"].append(Application(
            application_id=uuid.uuid4(), customer_ref=str(cust.customer_id),
            product_id=app["product_id"], started_at=_days_ago(app["stalled_hours"] / 24 + 1),
            last_updated_at=_days_ago(app["stalled_hours"] / 24), current_step=app["current_step"],
            steps_completed=app["steps_completed"], status=app["status"],
        ))

    bucket["manifest"][str(cust.customer_id)] = {
        "name": spec["name"], "persona": spec["key"],
        "expected_signals": spec.get("expected_signals", []),
        "expected_recommendation": spec.get("expected_recommendation"),
    }


def build_noise(bucket, n):
    """Self-employed customers with irregular income, insurance already held,
    moderate balances, healthy logins — engineered to trip NO signal."""
    for _ in range(n):
        cid = uuid.uuid4()
        cust = Customer(
            customer_id=cid, name=faker.name(), age=rng.randint(24, 60), gender=rng.choice(["M", "F"]),
            city_tier=rng.choice(["metro", "tier_2", "tier_3", "rural"]),
            language_pref=rng.choice(["en", "hi", "ta", "te", "bn"]), occupation="self_employed",
            kyc_status="complete", customer_type="existing", email=faker.email(),
            account_opened_date=date.today() - timedelta(days=rng.randint(300, 2000)),
            monthly_income=rng.randint(30000, 90000), owns_property=rng.choice([True, False]),
            dependents=rng.randint(0, 2), owns_gold=False, has_papl_offer=False, has_card_offer=False,
        )
        bucket["customers"].append(cust)
        acct = Account(account_id=uuid.uuid4(), customer_id=cid, account_type="acc_insta_plus",
                       balance=rng.randint(8000, 45000), status="active",
                       opened_date=date.today() - timedelta(days=rng.randint(300, 2000)))
        bucket["accounts"].append(acct)
        # already insured -> protection_gap stays quiet
        bucket["holdings"].append(Holding(holding_id=uuid.uuid4(), customer_id=cid,
                                          product_id="ins_eshield_insta", units=1, current_value=2000000,
                                          acquired_date=date.today() - timedelta(days=rng.randint(100, 800))))
        # irregular income (not a clean monthly salary) + normal spend
        for _ in range(rng.randint(4, 7)):
            _txn(bucket, acct, cust, rng.randint(8000, 30000), "credit", "transfer", "upi",
                 _days_ago(rng.uniform(0, WINDOW_DAYS)))
        emit_baseline(bucket, acct, cust)
        emit_sessions(bucket, cust, "healthy")
        bucket["manifest"][str(cid)] = {"name": cust.name, "persona": "noise", "expected_signals": []}


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def reset(session):
    for model in (Outcome, Action, Decision, Signal, Score, Transaction, AppSession,
                  Holding, Account, Application, Customer):
        session.query(model).delete()
    session.commit()


def generate(do_reset: bool = False, noise: int = NOISE_COUNT):
    bucket = {"customers": [], "accounts": [], "holdings": [], "txns": [],
              "sessions": [], "applications": [], "manifest": {}}

    for spec in PERSONAS:
        build_persona(spec, bucket)
    build_noise(bucket, noise)

    with SessionLocal() as session:
        if do_reset:
            reset(session)
        # Insert in FK-dependency order, flushing each group so parents exist
        # before children (no ORM relationships, so the UoW won't infer this).
        for key in ("customers", "accounts", "holdings", "txns", "sessions", "applications"):
            session.add_all(bucket[key])
            session.flush()
        session.commit()

    manifest_path = BACKEND_DIR / "generated_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(bucket["manifest"], fh, indent=2, ensure_ascii=False)

    print(f"Personas: {len(PERSONAS)} | noise: {noise} | "
          f"customers: {len(bucket['customers'])} | accounts: {len(bucket['accounts'])} | "
          f"txns: {len(bucket['txns'])} | sessions: {len(bucket['sessions'])} | "
          f"holdings: {len(bucket['holdings'])} | applications: {len(bucket['applications'])}")
    print(f"Manifest written to {manifest_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="wipe synthetic data first (keeps products)")
    ap.add_argument("--noise", type=int, default=NOISE_COUNT)
    args = ap.parse_args()
    generate(do_reset=args.reset, noise=args.noise)


if __name__ == "__main__":
    main()
