"""Score customers with the trained models + anomaly + priors; write SCORES (specs/ml.md).

    python -m apex.ml.score            # batch: score every customer

Score types written (matching schema): stress, attrition (churn), engagement_decay, anomaly.
Confidence is derived at decision time (not stored here); similarity is query-time.
"""
from collections import defaultdict
from datetime import datetime

import joblib
import pandas as pd

from ..config import BACKEND_DIR
from ..database.db import SessionLocal
from .anomaly import score_anomalies
from .features import (
    compute_engagement_decay, compute_stress_features, map_customer_to_churn,
)
from ..database.models import Account, AppSession, Customer, Holding, Score, Transaction

ARTIFACTS = BACKEND_DIR / "apex" / "ml" / "artifacts"
NOW = datetime.now()


def _load_artifacts():
    return {
        "stress": joblib.load(ARTIFACTS / "stress.joblib"),
        "churn": joblib.load(ARTIFACTS / "churn.joblib"),
    }


def _gather(session):
    """Pull everything once and group per customer (fine at demo scale)."""
    customers = session.query(Customer).all()
    accts, holds, txns, sess = defaultdict(list), defaultdict(int), defaultdict(list), defaultdict(list)
    for a in session.query(Account).all():
        accts[a.customer_id].append(a)
    for h in session.query(Holding).all():
        holds[h.customer_id] += 1
    for t in session.query(Transaction).all():
        txns[t.customer_id].append(t)
    for s in session.query(AppSession).all():
        sess[s.customer_id].append(s.login_time)
    return customers, accts, holds, txns, sess


def _txn_dicts(rows):
    return [{
        "amount": float(t.amount), "direction": t.direction,
        "merchant_category": t.merchant_category,
        "days_ago": max(0.0, (NOW - t.txn_time).total_seconds() / 86400),
    } for t in rows]


def score_all():
    art = _load_artifacts()
    written = 0
    with SessionLocal() as session:
        session.query(Score).delete()  # derived table — recompute fresh each run
        customers, accts, holds, txns_by, sess_by = _gather(session)

        for cust in customers:
            c_txns = _txn_dicts(txns_by[cust.customer_id])
            balance = sum(float(a.balance) for a in accts[cust.customer_id])
            num_products = len(accts[cust.customer_id]) + holds[cust.customer_id]
            last_login = max(sess_by[cust.customer_id], default=None)
            active = bool(last_login and (NOW - last_login).days <= 30)
            income = float(cust.monthly_income) if cust.monthly_income is not None else None

            # --- stress ---
            rec = {"monthly_income": income, "current_balance": balance, "txns": c_txns}
            sf = pd.DataFrame([compute_stress_features(rec)])[art["stress"]["features"]]
            stress = float(art["stress"]["model"].predict_proba(sf)[:, 1][0])

            # --- attrition (Kaggle churn model: will the customer leave the bank) ---
            cf = map_customer_to_churn({
                "age": cust.age, "account_opened_date": cust.account_opened_date,
                "balance": balance, "num_products": num_products, "active": active,
                "monthly_income": income,
            })
            cf_df = pd.DataFrame([cf])[art["churn"]["features"]]
            attrition = float(art["churn"]["model"].predict_proba(cf_df)[:, 1][0])

            # --- engagement decay (heuristic from sessions; feeds login_decay) ---
            login_days = [max(0.0, (NOW - lt).days) for lt in sess_by[cust.customer_id]]
            decay = compute_engagement_decay(login_days)

            # --- anomaly (unsupervised) ---
            anomaly = score_anomalies(c_txns)

            for stype, val in [("stress", {"score": round(stress, 4)}),
                               ("attrition", {"score": round(attrition, 4)}),
                               ("engagement_decay", {"score": decay}),
                               ("anomaly", anomaly)]:
                session.add(Score(customer_id=cust.customer_id, score_type=stype, value=val))
                written += 1
        session.commit()
    print(f"Wrote {written} score rows for {len(customers)} customers.")


if __name__ == "__main__":
    score_all()
