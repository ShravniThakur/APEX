"""Shared financial-history shaping (specs/ml.md).

ONE function used by *both* the ML stress trainset (apex.ml.trainset) and the demo
data generator (apex.generator.generate), so the stress model trains and serves on
the SAME feature distribution. Pure functions, no DB.
"""
import random


def shape_financial_history(income: float, stress_level: float, rng: random.Random) -> dict:
    """A 90-day history (salary + debits + medical) whose extracted stress features
    scale with `stress_level` in [0,1]. Returns {txns, current_balance};
    txns = [{amount, direction, merchant_category, days_ago}].

    Low stress -> outflow below income, no acceleration, no medical (calm).
    High stress -> outflow exceeds income, recent-biased, medical uptick (declining).
    """
    s = max(0.0, min(1.0, stress_level))
    income = float(income or 40000)
    txns = []

    # salary credits (3 months)
    for m in range(3):
        txns.append({"amount": income, "direction": "credit",
                     "merchant_category": "salary", "days_ago": m * 30 + 1})

    # debits: total outflow and recency-acceleration scale with stress
    out_multiple = 0.8 + s * 0.9               # 0.8x .. 1.7x of 3-month income
    target_out = income * 3 * out_multiple
    n = 24
    for i in range(n):
        days = (i / n) * 90                    # i=0 newest
        recent_boost = (1.6 - days / 90) if s > 0.4 else 1.0
        amt = max(150.0, (target_out / n) * recent_boost * rng.uniform(0.7, 1.3))
        txns.append({"amount": round(amt, 2), "direction": "debit",
                     "merchant_category": rng.choice(["retail", "transfer", "utility"]),
                     "days_ago": days})

    # medical frequency rises with stress
    for _ in range(int(round(s * 2))):
        txns.append({"amount": round(rng.uniform(2000, 6000), 2), "direction": "debit",
                     "merchant_category": "medical", "days_ago": rng.uniform(0, 40)})

    balance = max(500.0, rng.gauss(income * (1.0 - 0.7 * s), income * 0.3))
    return {"txns": txns, "current_balance": balance}
