"""Analyser-mode agentic loop (specs APEX_README §3 Analyser; §6-7 restraint + authority).

    python -m apex.agent.loop                 # process all Analyser signals
    python -m apex.agent.loop --limit 6       # only the first 6 (saves LLM calls while testing)

For each Analyser SIGNALS row: gather context -> run the LangGraph reasoning flow
(route -> hypothesise -> critique -> decide [code gate] -> compose) -> write DECISIONS
(+ ACTIONS when acting) -> mark the signal processed.

Guide-mode signals (application_dropoff) are skipped — that's a later, conversational stage.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from ..config import DEMO_EMAIL
from ..database.db import SessionLocal
from ..database.models import (
    Account, Action, Customer, Decision, Holding, Outcome, Product, Score, Signal, Transaction,
)
from . import mailer
from .graph import analyser_app
from .routing import ANALYSER_SIGNALS

NOW = datetime.now()
COOLDOWN_DAYS = 30   # don't re-nudge the same customer about the same signal type within this window


def _suppressed(session, customer_id, signal_type, now) -> tuple[bool, str]:
    """Should we skip this signal because the customer was already handled for it?
    Reads persisted DECISIONS/ACTIONS/OUTCOMES history (decisions are tagged 'type:id')."""
    prior = session.query(Decision).filter(
        Decision.customer_id == customer_id,
        Decision.trigger_ref.like(f"{signal_type}:%"),
    ).all()
    for d in prior:
        action = session.query(Action).filter(Action.decision_id == d.decision_id).first()
        oc = session.query(Outcome).filter(Outcome.action_id == action.action_id).first() if action else None
        if oc and oc.response_type in ("dismissed", "completed"):
            return True, f"customer already {oc.response_type} this"
        if d.created_at and (now - d.created_at).days < COOLDOWN_DAYS:
            return True, f"contacted {(now - d.created_at).days}d ago (cooldown {COOLDOWN_DAYS}d)"
    return False, ""


@dataclass
class AgentContext:
    cust: object
    accounts: list = field(default_factory=list)
    holdings: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    products: dict = field(default_factory=dict)
    history: dict = field(default_factory=dict)   # {product_category: dismissal_count} — the "memory"
    active_signals: set = field(default_factory=set)  # all of this customer's currently-detected signals


def _load_products(session) -> dict:
    """Catalogue from the PRODUCTS table — the single runtime source of truth (seeded once from
    product_catalogue.json by init_db, never re-read from disk at runtime)."""
    return {
        p.product_id: {
            "product_id": p.product_id, "name": p.name, "category": p.category,
            "depth": p.depth, "description": p.description,
            "eligibility_rules": p.eligibility_rules or {}, "key_facts": p.key_facts or {},
            "landing_url": p.landing_url, "tax_saving": bool(p.tax_saving),
        }
        for p in session.query(Product).all()
    }


def _deep_link(product: dict, cust) -> str | None:
    url = product.get("landing_url")
    if url and cust.language_pref:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}lang={cust.language_pref}"
    return url


def run(limit: int | None = None, send: bool = False, customer_id: str | None = None,
        reset: bool = True):
    with SessionLocal() as session:
        products = _load_products(session)
        # reset=True: wipe & reprocess fresh (repeatable demo). reset=False: incremental —
        # keep the decision/action/outcome history so suppression can read it.
        # (FK order: outcome -> action -> decision; scoped to one customer when given.)
        if reset:
            for model in (Outcome, Action, Decision):
                q = session.query(model)
                if customer_id:
                    q = q.filter(model.customer_id == customer_id)
                q.delete()

        all_signals = session.query(Signal).all()
        # Every customer's full set of currently-detected signals (for holistic vulnerability checks).
        active_by_cust: dict = defaultdict(set)
        for s in all_signals:
            active_by_cust[s.customer_id].add(s.signal_type)

        signals = [s for s in all_signals
                   if s.signal_type in ANALYSER_SIGNALS
                   and (customer_id is None or str(s.customer_id) == customer_id)]
        signals.sort(key=lambda s: s.detected_at or NOW)
        if limit:
            signals = signals[:limit]

        # Per-customer data, gathered once.
        accts, holds, scores = defaultdict(list), defaultdict(list), defaultdict(dict)
        for a in session.query(Account).all():
            accts[a.customer_id].append(a)
        for h in session.query(Holding).all():
            holds[h.customer_id].append(h)
        for sc in session.query(Score).all():
            scores[sc.customer_id][sc.score_type] = sc.value
        customers = {c.customer_id: c for c in session.query(Customer).all()}

        # Dismissal history per customer+category — the real "memory" the self-critique and the
        # gate weigh (a category the customer has rejected before). Read from the persisted
        # DECISIONS→ACTIONS→OUTCOMES chain: empty in full-reset mode (history was wiped above),
        # populated in incremental mode where prior outcomes survive.
        dismissals: dict = defaultdict(lambda: defaultdict(int))
        acts_by_id = {a.action_id: a for a in session.query(Action).all()}
        decs_by_id = {d.decision_id: d for d in session.query(Decision).all()}
        for o in session.query(Outcome).filter(Outcome.response_type == "dismissed").all():
            act = acts_by_id.get(o.action_id)
            dec = decs_by_id.get(act.decision_id) if act else None
            cat = products.get(dec.product_id, {}).get("category") if (dec and dec.product_id) else None
            if cat:
                dismissals[o.customer_id][cat] += 1

        counts = defaultdict(int)
        email_sent = email_fail = 0
        for sig in signals:
            cust = customers[sig.customer_id]

            # Incremental mode: skip signals the customer was already handled for (the
            # feedback loop — don't re-nudge dismissed/adopted/recently-contacted customers).
            if not reset:
                supp, why = _suppressed(session, sig.customer_id, sig.signal_type, NOW)
                if supp:
                    counts["suppressed"] += 1
                    sig.status = "processed"
                    continue

            ctx = AgentContext(cust=cust, accounts=accts[sig.customer_id],
                               holdings=holds[sig.customer_id],
                               scores=scores[sig.customer_id], products=products,
                               history=dict(dismissals.get(sig.customer_id, {})),
                               active_signals=active_by_cust.get(sig.customer_id, set()))

            # Run the LangGraph reasoning flow. The 'decide' node is the deterministic gate.
            final = analyser_app.invoke({
                "signal_type": sig.signal_type, "source_ref": sig.source_ref, "ctx": ctx,
            })
            outcome = final["outcome"]
            product = products.get(final.get("product_id")) if final.get("product_id") else None
            message_text = final.get("message_text", "")
            # Keep the auditable gate reason alongside the LLM's critique.
            critique = (final.get("critique") or "").strip()
            if final.get("reason"):
                critique = f"{critique}\n\n[gate] {final['reason']}" if critique else f"[gate] {final['reason']}"

            dec = Decision(
                customer_id=cust.customer_id, mode="analyser",
                trigger_ref=f"{sig.signal_type}:{sig.signal_id}",  # self-describing for suppression
                hypothesis=final.get("hypothesis", ""), critique_result=critique,
                confidence=final.get("confidence"), outcome=outcome,
                product_id=final.get("product_id"), created_at=NOW,
            )
            session.add(dec)
            session.flush()  # need decision_id for the action

            if outcome == "act" and message_text:
                # Create the action first (deep_link = the real SBI page the tracker redirects to),
                # flush to get its id, then send the email with click-tracking links built from it.
                action = Action(
                    decision_id=dec.decision_id, customer_id=cust.customer_id,
                    authority_level=final.get("authority_level"), channel="email",
                    message_text=message_text,
                    deep_link=_deep_link(product, cust) if product else None, sent_at=None,
                )
                session.add(action)
                session.flush()
                if send:
                    result = mailer.send(message_text, action_id=str(action.action_id))
                    if result["sent"]:
                        email_sent += 1
                        action.sent_at = datetime.now()
                    else:
                        email_fail += 1
                        if email_fail == 1:           # surface the first failure cause once
                            print(f"  email error: {result.get('error')}")

            sig.status = "processed"
            counts[outcome] += 1

        session.commit()

    sink = f" (email sink: {DEMO_EMAIL})" if DEMO_EMAIL else ""
    mode = "incremental" if not reset else "full reset"
    print(f"Processed {len(signals)} Analyser signals{sink} [{mode}]")
    print(f"  act={counts['act']}  wait={counts['wait']}  escalate={counts['escalate']}", end="")
    print(f"  suppressed={counts['suppressed']}" if not reset else "")
    if send:
        print(f"  emails sent={email_sent}  failed={email_fail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process the first N signals")
    ap.add_argument("--send", action="store_true", help="actually deliver acted messages via Resend")
    ap.add_argument("--incremental", action="store_true",
                    help="keep history and suppress already-handled/dismissed signals "
                         "(production-style); default wipes and reprocesses")
    args = ap.parse_args()
    run(limit=args.limit, send=args.send, reset=not args.incremental)


if __name__ == "__main__":
    main()
