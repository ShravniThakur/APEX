"""Unsupervised per-customer anomaly detection (specs/ml.md).

No training. Compares each debit to the customer's OWN distribution (median + MAD).
"""
import statistics


def score_anomalies(txns: list, k: float = 3.5) -> dict:
    """txns: [{amount, direction, merchant_category, days_ago}]. Flags debits that
    deviate sharply above the customer's own typical amount."""
    debits = [t for t in txns if t["direction"] == "debit"]
    if len(debits) < 4:
        return {"flagged": [], "max_magnitude": 0.0}

    amts = [t["amount"] for t in debits]
    med = statistics.median(amts)
    mad = statistics.median([abs(a - med) for a in amts]) or 1.0
    scale = 1.4826 * mad  # MAD -> std-equivalent for normal data

    flagged = []
    for t in debits:
        mag = (t["amount"] - med) / scale
        if mag > k:  # unusually large for this customer
            flagged.append({
                "amount": t["amount"], "category": t["merchant_category"],
                "magnitude": round(mag, 2), "days_ago": round(t["days_ago"], 1),
            })
    flagged.sort(key=lambda f: -f["magnitude"])
    return {
        "flagged": flagged,
        "max_magnitude": round(max((f["magnitude"] for f in flagged), default=0.0), 2),
    }
