"""Shared feature extraction + serve-mappers (specs/ml.md).

The SAME functions run at training time (on synthetic/CSV data) and at serve
time (on our Postgres customers) — this is what prevents train/serve skew.
"""
import math
import statistics
from datetime import date

# --- Stress ---------------------------------------------------------------- #
STRESS_FEATURES = [
    "spending_velocity", "balance_slope", "emi_to_income",
    "withdrawal_irregularity", "medical_recency",
]


def _drop_outlier_debits(debits, k=3.5):
    """Exclude one-off anomalous debits so a single large purchase (vehicle, tuition)
    doesn't read as chronic stress — the anomaly detector handles those separately as
    life_event / large_asset_purchase. Applied in BOTH training and serving (shared)."""
    if len(debits) < 4:
        return debits
    amts = [t["amount"] for t in debits]
    med = statistics.median(amts)
    mad = statistics.median([abs(a - med) for a in amts]) or 1.0
    scale = 1.4826 * mad
    return [t for t in debits if (t["amount"] - med) / scale <= k]


def compute_stress_features(record: dict) -> dict:
    """record = {monthly_income, current_balance, txns:[{amount, direction,
    merchant_category, days_ago}]}. Used for both training and serving."""
    income = float(record.get("monthly_income") or 1.0)
    balance = float(record.get("current_balance") or 0.0)
    txns = record["txns"]
    credits = [t for t in txns if t["direction"] == "credit"]
    debits = _drop_outlier_debits([t for t in txns if t["direction"] == "debit"])

    recent = sum(t["amount"] for t in debits if t["days_ago"] <= 30)
    prior = sum(t["amount"] for t in debits if 30 < t["days_ago"] <= 60)
    spending_velocity = recent / (prior + 1.0)

    net_flow = sum(t["amount"] for t in credits) - sum(t["amount"] for t in debits)
    mean_balance = balance + abs(net_flow) / 2 + 1.0
    balance_slope = net_flow / mean_balance  # negative = declining

    total_out = sum(t["amount"] for t in debits)
    emi_to_income = total_out / (3 * income + 1.0)

    if len(debits) >= 2:
        amts = [t["amount"] for t in debits]
        m = sum(amts) / len(amts)
        sd = (sum((a - m) ** 2 for a in amts) / len(amts)) ** 0.5
        withdrawal_irregularity = sd / (m + 1.0)
    else:
        withdrawal_irregularity = 0.0

    medical_recency = sum(
        math.exp(-t["days_ago"] / 30) for t in debits if t["merchant_category"] == "medical"
    )

    return {
        "spending_velocity": spending_velocity,
        "balance_slope": balance_slope,
        "emi_to_income": emi_to_income,
        "withdrawal_irregularity": withdrawal_irregularity,
        "medical_recency": medical_recency,
    }


# --- Engagement decay (heuristic, feeds login_decay; no model, no dataset) - #
def compute_engagement_decay(login_days_ago: list, split: int = 45, window: int = 90) -> float:
    """Per-customer login-frequency trend from APP_SESSIONS. High when logins thin out
    toward the present (declining engagement). A transparent calculation — not a trained
    model. Distinct from attrition (Kaggle) and hard dormancy (90-day rule)."""
    older = [d for d in login_days_ago if split < d <= window]
    recent = [d for d in login_days_ago if 0 <= d <= split]
    if not older and not recent:
        return 0.0  # fully dead -> handled by the dormancy rule, not login_decay
    o, r = len(older), len(recent)
    return round(max(0.0, (o - r) / (o + 1)), 3)


# --- Churn / attrition (serve-mapper to Churn_Modelling schema) ------------ #
def map_customer_to_churn(c: dict) -> dict:
    tenure = 0
    if c.get("account_opened_date"):
        tenure = min(10, max(0, (date.today() - c["account_opened_date"]).days // 365))
    return {
        "Age": c["age"],
        "Tenure": tenure,
        "Balance": float(c.get("balance", 0.0)),
        "NumOfProducts": int(c.get("num_products", 1)),
        "IsActiveMember": 1 if c.get("active") else 0,
        "EstimatedSalary": float(c.get("monthly_income") or 0) * 12,
    }


# --- Propensity (synthetic latent-driver, all categories) ------------------ #
# Cold-start prior, NOT learned from real uptake (OUTCOMES is empty at launch).
# Same shared train+serve builder; swap the trainset for OUTCOMES later, untouched.
PROPENSITY_CATEGORIES = ["deposits", "investments", "insurance", "payments", "loans"]

PROPENSITY_FEATURES = [
    "age", "monthly_income", "balance", "num_products", "tenure_years",
    "dependents", "owns_property", "owns_gold", "occupation", "city_tier",
]

# Fixed vocabularies so an encoded value means the same thing at train and serve
# time (no skew). Unknown / missing values -> -1.
OCCUPATION_VOCAB = ["salaried", "self_employed", "student", "retired"]
CITY_TIER_VOCAB = ["metro", "tier_2", "tier_3", "rural"]


def _encode(value, vocab):
    return vocab.index(value) if value in vocab else -1


def compute_propensity_features(record: dict) -> dict:
    """Shared train+serve feature builder for propensity. `record` carries APEX-native
    customer fields; returns the numeric PROPENSITY_FEATURES dict. Used identically on
    synthetic training rows and on real Postgres customers — this is the skew defense."""
    return {
        "age": float(record.get("age") or 0),
        "monthly_income": float(record.get("monthly_income") or 0),
        "balance": float(record.get("balance") or 0),
        "num_products": int(record.get("num_products") or 0),
        "tenure_years": float(record.get("tenure_years") or 0),
        "dependents": int(record.get("dependents") or 0),
        "owns_property": 1 if record.get("owns_property") else 0,
        "owns_gold": 1 if record.get("owns_gold") else 0,
        "occupation": _encode(record.get("occupation"), OCCUPATION_VOCAB),
        "city_tier": _encode(record.get("city_tier"), CITY_TIER_VOCAB),
    }
