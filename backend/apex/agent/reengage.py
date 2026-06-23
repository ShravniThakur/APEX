"""Scheduled re-engagement of WAIT decisions (APEX_README §6 — ethical timing).

A `wait` is a deliberate pause, not a dead end. When APEX detects a vulnerable or sensitive
moment (a medical event, severe stress) the gate returns `wait` — it does NOT act immediately,
because contacting someone mid-crisis feels like surveillance, not care. This pass closes that
loop: it revisits waits once the acute window has passed and, if the customer is no longer in an
acute state, sends ONE gentle, product-free *insight* (authority Level 1) — "acknowledge and wait,
then offer insight without a product attached; let the customer pull the product forward."

    python -m apex.agent.reengage                  # revisit waits >= REENGAGE_AFTER_DAYS old
    python -m apex.agent.reengage --days 0 --send  # demo: revisit all waits now + deliver email

A wait is LEFT UNTOUCHED (kept waiting) when the customer is still in an acute moment — current
severe financial stress — so APEX never follows up during the hard window. Each follow-up is
tagged `trigger_ref="reengage:<original_decision_id>"`, so a wait is only ever followed up once.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta

from ..config import DEMO_EMAIL
from ..database.db import SessionLocal
from ..database.models import Account, Action, Customer, Decision, Holding, Score
from . import guardrails, llm, mailer
from .loop import AgentContext, _load_products  # reuse the loop's context + catalogue plumbing

REENGAGE_AFTER_DAYS = 3   # the deliberate wait before a gentle, product-free follow-up


def _fallback(cust) -> str:
    """Used only if the LLM is unavailable (no key / rate limit) — keeps the pass functional and
    on-philosophy: warm, product-free, no link, names nothing sensitive."""
    first = cust.name.split()[0]
    return (f"Hi {first}, it's APEX from SBI. We're just checking in — there's nothing you need to "
            f"do. If you'd ever like to talk anything through about your money, we're here to help.")


def _payload(cust, signal_type: str, days_since: int) -> dict:
    return {
        "customer": {
            "first_name": cust.name.split()[0], "age": cust.age, "occupation": cust.occupation,
            "city_tier": cust.city_tier, "language_pref": cust.language_pref,
        },
        "signal_type": signal_type, "days_since": days_since,
    }


def run(days: int = REENGAGE_AFTER_DAYS, send: bool = False,
        customer_id: str | None = None) -> dict:
    now = datetime.now()
    cutoff = now - timedelta(days=days)

    with SessionLocal() as session:
        products = _load_products(session)

        # Only revisit waits that represent a deliberate VULNERABILITY hold (a medical life_event).
        # Other waits — e.g. a cooldown/over-contact hold or an insurance-only restraint — must NOT
        # get a "we noticed a sensitive moment" check-in; that would be wrong and intrusive.
        waits_q = session.query(Decision).filter(
            Decision.mode == "analyser",
            Decision.outcome == "wait",
            Decision.trigger_ref.like("life_event:%"),
            Decision.created_at <= cutoff,
        )
        if customer_id:
            waits_q = waits_q.filter(Decision.customer_id == customer_id)
        waits = waits_q.order_by(Decision.created_at).all()

        # Waits that were already followed up — never re-engage the same wait twice.
        followed = {
            (d.trigger_ref or "").split("reengage:", 1)[1]
            for d in session.query(Decision).filter(Decision.trigger_ref.like("reengage:%")).all()
            if d.trigger_ref
        }

        # Per-customer data, gathered once (same shape the loop builds).
        accts, holds, scores = defaultdict(list), defaultdict(list), defaultdict(dict)
        for a in session.query(Account).all():
            accts[a.customer_id].append(a)
        for h in session.query(Holding).all():
            holds[h.customer_id].append(h)
        for sc in session.query(Score).all():
            scores[sc.customer_id][sc.score_type] = sc.value
        customers = {c.customer_id: c for c in session.query(Customer).all()}

        engaged = held = sent_count = email_fail = 0
        for w in waits:
            if str(w.decision_id) in followed:
                continue
            cust = customers.get(w.customer_id)
            if cust is None:
                continue

            # Still acutely vulnerable? Severe ongoing financial stress means the moment has NOT
            # passed — keep waiting rather than intrude. (A medical life_event, by contrast, eases
            # with time, which is exactly what `days` since the wait represents.)
            stress = (scores.get(w.customer_id, {}).get("stress") or {}).get("score", 0.0) or 0.0
            if stress >= guardrails.SEVERE_STRESS:
                held += 1
                continue

            signal_type = (w.trigger_ref or "").split(":", 1)[0] or "wait"
            days_since = (now - w.created_at).days if w.created_at else days
            message_text = llm.reengage(_payload(cust, signal_type, days_since)) or _fallback(cust)

            dec = Decision(
                customer_id=cust.customer_id, mode="analyser",
                trigger_ref=f"reengage:{w.decision_id}",
                hypothesis=f"Re-engagement after a deliberate wait on '{signal_type}' "
                           f"({days_since}d ago). The acute moment has passed.",
                critique_result="[gate] acute moment has passed — offering a single product-free "
                                "insight (Level 1), never a push.",
                confidence=w.confidence, outcome="act", product_id=None, created_at=now,
            )
            session.add(dec)
            session.flush()

            action = Action(
                decision_id=dec.decision_id, customer_id=cust.customer_id,
                authority_level=1, channel="email", message_text=message_text,
                deep_link=None, sent_at=None,
            )
            session.add(action)
            session.flush()

            if send:
                result = mailer.send(message_text, action_id=str(action.action_id))
                if result["sent"]:
                    sent_count += 1
                    action.sent_at = datetime.now()
                else:
                    email_fail += 1
                    if email_fail == 1:
                        print(f"  email error: {result.get('error')}")

            engaged += 1

        session.commit()

    sink = f" (email sink: {DEMO_EMAIL})" if DEMO_EMAIL else ""
    print(f"Re-engagement pass over {len(waits)} eligible wait(s){sink} [>= {days}d old]")
    print(f"  re-engaged={engaged}  still-waiting(acute)={held}", end="")
    print(f"  emails sent={sent_count}  failed={email_fail}" if send else "")
    return {"eligible": len(waits), "reengaged": engaged, "still_waiting": held,
            "emails_sent": sent_count, "days": days, "send": send}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=REENGAGE_AFTER_DAYS,
                    help="only revisit waits at least this many days old (0 = all, for the demo)")
    ap.add_argument("--send", action="store_true", help="deliver the insight emails via Resend")
    args = ap.parse_args()
    run(days=args.days, send=args.send)


if __name__ == "__main__":
    main()
