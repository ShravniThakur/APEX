"""Synthetic latent-driver training sets — STRESS and PROPENSITY (specs/ml.md).

Stress: each customer gets a hidden stress_level that shapes their history via the
SHARED `shape_financial_history` (same function the demo generator uses → no
train/serve skew). The label is a *separately* noisy function of that level (~12%
flips), so the model learns a real boundary rather than memorising the generator.

Propensity: cold-start prior. OUTCOMES is empty at launch, so there is no real
uptake to learn from. Each synthetic customer has hidden affinity drivers that
observable fields only partly reveal; per-category labels derive from those latents
+ interactions, with noise. This is a placeholder with the right SHAPE — when real
click-tracked OUTCOMES exist, only this generator is swapped for an OUTCOMES loader;
features.compute_propensity_features, the model, and score.py stay unchanged.

Churn (attrition) uses a real CSV instead (see loaders.py).
"""
import random
import statistics

from ..shaping import shape_financial_history
from .features import CITY_TIER_VOCAB, OCCUPATION_VOCAB, PROPENSITY_CATEGORIES


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


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


def generate_propensity_trainset(n: int = 4000, seed: int = 42):
    """Returns (records, labels). records match compute_propensity_features' contract;
    labels = list of {category: 0|1} (one binary label per propensity category).

    Hidden drivers in [0,1] — risk appetite, savviness, protection-seeking, liquidity
    need, digital orientation — are partly tied to observable fields, then per-category
    affinity is a function of those latents + interactions. Labels threshold the affinity
    at each category's OWN median (balanced classes; "high propensity" is relative, which
    is how the score is consumed — to rank products), with ~12% noise flips so the model
    learns a boundary, not the generator's arithmetic.
    """
    rng = random.Random(seed + 1)   # offset so it doesn't mirror the stress stream
    records, affinities = [], []

    for _ in range(n):
        age = rng.randint(21, 65)
        income = rng.randint(15000, 200000)
        balance = max(0.0, rng.gauss(income * rng.uniform(0.5, 6.0), income))
        dependents = rng.choice([0, 0, 1, 2, 3])
        owns_property = rng.random() < 0.4
        owns_gold = rng.random() < 0.3
        occupation = rng.choice(OCCUPATION_VOCAB)
        city_tier = rng.choice(CITY_TIER_VOCAB)
        tenure = rng.uniform(0.0, 12.0)
        num_products = rng.randint(1, 5)

        # latent drivers (observable-correlated + noise) ----------------------
        young = (65 - age) / 44
        well_off = min(1.0, income / 150000)
        cushion = min(1.0, balance / (income * 3 + 1.0))
        risk_appetite = _clip(0.5 * young + 0.4 * well_off + rng.gauss(0, 0.2))
        savviness = _clip(0.4 * well_off + 0.3 * (num_products / 5) + 0.3 * (tenure / 12) + rng.gauss(0, 0.2))
        protection = _clip(0.5 * (dependents / 3) + 0.3 * (1 if owns_property else 0) + rng.gauss(0, 0.2))
        liquidity_need = _clip(0.6 * (1 - cushion) + 0.3 * (dependents / 3) + rng.gauss(0, 0.2))
        digital = _clip(0.6 * young + 0.3 * (num_products / 5) + rng.gauss(0, 0.2))

        # per-category affinity = latents + interactions ---------------------
        aff = {
            "deposits":    0.6 * savviness + 0.4 * cushion + 0.2 * (age / 65),
            "investments": 0.7 * risk_appetite + 0.3 * well_off,
            "insurance":   0.7 * protection + 0.2 * well_off + 0.1 * (age / 65),
            "payments":    0.7 * digital + 0.3 * (num_products / 5),
            "loans":       0.7 * liquidity_need + 0.3 * (1 if owns_property else 0) * (dependents / 3 + 0.3),
        }

        records.append({
            "age": age, "monthly_income": income, "balance": round(balance, 2),
            "num_products": num_products, "tenure_years": round(tenure, 2),
            "dependents": dependents, "owns_property": owns_property,
            "owns_gold": owns_gold, "occupation": occupation, "city_tier": city_tier,
        })
        affinities.append({cat: _clip(aff[cat]) for cat in PROPENSITY_CATEGORIES})

    # Second pass: label each category against its own median (balanced, relative) + noise.
    medians = {cat: statistics.median(a[cat] for a in affinities) for cat in PROPENSITY_CATEGORIES}
    labels = []
    for a in affinities:
        lab = {}
        for cat in PROPENSITY_CATEGORIES:
            y = 1 if a[cat] > medians[cat] else 0
            if rng.random() < 0.12:
                y = 1 - y
            lab[cat] = y
        labels.append(lab)

    return records, labels
