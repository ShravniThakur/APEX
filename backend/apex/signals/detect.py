"""Run the 17 detectors over every customer and write SIGNALS (specs/signals.md).

    python -m apex.signals.detect

A SIGNALS row is the cheap gate that decides whether the (future) agentic loop runs
for a customer this cycle. Signals are recomputed fresh each run at demo scale: the
table is cleared, then re-detected.
"""
from collections import defaultdict
from datetime import datetime

from ..database.db import SessionLocal
from ..database.models import (
    Account, AppSession, Application, Customer, Holding, Product, Score, Signal,
    Transaction,
)
from .detectors import DETECTORS, Context


def _gather(session):
    """Pull everything once and group per customer (fine at demo scale)."""
    customers = session.query(Customer).all()
    accts, txns, sess, holds = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for a in session.query(Account).all():
        accts[a.customer_id].append(a)
    for t in session.query(Transaction).all():
        txns[t.customer_id].append(t)
    for s in session.query(AppSession).all():
        sess[s.customer_id].append(s.login_time)
    for h in session.query(Holding).all():
        holds[h.customer_id].append(h)

    scores = defaultdict(dict)
    for sc in session.query(Score).all():
        scores[sc.customer_id][sc.score_type] = sc.value

    apps_by_ref = {a.customer_ref: a for a in session.query(Application).all()}

    tax_saving = {p.product_id for p in session.query(Product).filter(Product.tax_saving.is_(True))}
    insurance = {p.product_id for p in session.query(Product).filter(Product.category == "insurance")}

    return customers, accts, txns, sess, holds, scores, apps_by_ref, tax_saving, insurance


def detect_all(now: datetime | None = None):
    now = now or datetime.now()
    with SessionLocal() as session:
        session.query(Signal).delete()       # derived gate — recompute fresh each run
        (customers, accts, txns, sess, holds, scores,
         apps_by_ref, tax_saving, insurance) = _gather(session)

        rows, per_signal = [], defaultdict(int)
        for cust in customers:
            ctx = Context(
                cust=cust, accounts=accts[cust.customer_id], txns=txns[cust.customer_id],
                sessions=sess[cust.customer_id], holdings=holds[cust.customer_id],
                application=apps_by_ref.get(str(cust.customer_id)),
                scores=scores[cust.customer_id], now=now,
                tax_saving_products=tax_saving, insurance_products=insurance,
            )
            for signal_type, fn in DETECTORS:
                source_ref = fn(ctx)
                if source_ref:
                    rows.append(Signal(customer_id=cust.customer_id, signal_type=signal_type,
                                       source_ref=source_ref, detected_at=now))
                    per_signal[signal_type] += 1

        session.add_all(rows)
        session.commit()

    print(f"Detected {len(rows)} signals across {len(customers)} customers (asof {now:%Y-%m-%d}).")
    for sig, _ in DETECTORS:
        print(f"  {sig:26} {per_signal.get(sig, 0)}")


if __name__ == "__main__":
    detect_all()
