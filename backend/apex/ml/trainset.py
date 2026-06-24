"""Synthetic latent-driver training set — STRESS (specs/ml.md).

Stress: each customer gets a hidden stress_level that shapes their history via the
SHARED `shape_financial_history` (same function the demo generator uses → no
train/serve skew). The label is a *separately* noisy function of that level (~12%
flips), so the model learns a real boundary rather than memorising the generator.

Churn (attrition) uses a real CSV instead (see loaders.py).
"""
import random

from ..shaping import shape_financial_history


def generate_stress_trainset(n: int = 3000, seed: int = 42):
    """Returns (records, labels). records match compute_stress_features' contract."""
    rng = random.Random(seed)
    records, labels = [], []

    for _ in range(n):
        s = rng.random()  # latent stress level in [0,1]
        income = rng.randint(20000, 150000)
        rec = shape_financial_history(income, s, rng)
        rec["monthly_income"] = income
        records.append(rec)

        label = 1 if s > 0.6 else 0
        if rng.random() < 0.12:               # noise: features don't perfectly determine label
            label = 1 - label
        labels.append(label)

    return records, labels
