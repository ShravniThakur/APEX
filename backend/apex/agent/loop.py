"""Analyser-mode loop — one coherent outreach per CUSTOMER (specs APEX_README §3, §6-7).

    python -m apex.agent.loop                 # process all customers with Analyser signals
    python -m apex.agent.loop --limit 6       # only the first 6 customers (saves LLM calls)
    python -m apex.agent.loop --limit 3 --send  # also deliver acted messages via Resend

For each customer with ≥1 Analyser signal: gather context → `guardrails.decide_customer`
(the deterministic gate: ethical pre-empt + safe-set builder + act/wait/escalate) → if it says
ACT, the LLM picks the single best fit from the vetted safe set and writes the message
(`llm.select_and_compose`) → write DECISIONS (+ ACTIONS when acting) → mark the customer's
signals processed.

"LLM proposes the relevance pick + wording; code disposes the decision and the safe set." The
LLM can never reach a product code didn't allow, raise the authority level, or act when code said
wait/escalate. Guide-mode signals (application_dropoff) are skipped — that's a conversational stage.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import DEMO_EMAIL
from ..database.db import SessionLocal
from ..database.models import (
    Account, Action, Customer, Decision, Holding, Outcome, Product, Score, Signal,
)
from . import guardrails, llm, mailer
from .routing import ANALYSER_SIGNALS

NOW = datetime.now()
COOLDOWN_DAYS = 30   # don't re-recommend the same product to the same customer within this window


@dataclass
class AgentContext:
    cust: object
    accounts: list = field(default_factory=list)
    holdings: list = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    products: dict = field(default_factory=dict)
    history: dict = field(default_factory=dict)        # {product_category: dismissal_count}
    active_signals: set = field(default_factory=set)   # all of this customer's detected signal *types*
    signals: list = field(default_factory=list)        # [(signal_type, source_ref, signal_id)]
    recent_products: set = field(default_factory=set)  # product_ids recommended within the cooldown


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


def _fallback_message(cust) -> str:
    """Used only if the LLM is unavailable — keeps the loop functional and on-philosophy:
    calm, product-free wording, no link, nothing sensitive named."""
    first = cust.name.split()[0]
    return (f"Hi {first}, it's APEX from SBI. Looking at your recent account activity, there may be "
            f"a simple way to make your money work a little better for you. There's nothing urgent — "
            f"we can walk you through it whenever suits you.")


def run(limit: int | None = None, send: bool = False, customer_id: str | None = None,
        reset: bool = True):
    with SessionLocal() as session:
        products = _load_products(session)
        # reset=True: wipe & reprocess fresh (repeatable demo). reset=False: incremental — keep the
        # decision/action/outcome history so dismissal back-off + the cooldown can read it.
        if reset:
            for model in (Outcome, Action, Decision):
                q = session.query(model)
                if customer_id:
                    q = q.filter(model.customer_id == customer_id)
                q.delete()
            session.flush()

        all_signals = session.query(Signal).all()
        # Group Analyser signals per customer; also keep every customer's full set of signal TYPES
        # (the vulnerability check reads the whole set, e.g. an active life_event).
        sigs_by_cust: dict = defaultdict(list)
        active_by_cust: dict = defaultdict(set)
        for s in all_signals:
            active_by_cust[s.customer_id].add(s.signal_type)
            if s.signal_type in ANALYSER_SIGNALS and (customer_id is None or str(s.customer_id) == customer_id):
                sigs_by_cust[s.customer_id].append(s)

        # Per-customer data, gathered once.
        accts, holds, scores = defaultdict(list), defaultdict(list), defaultdict(dict)
        for a in session.query(Account).all():
            accts[a.customer_id].append(a)
        for h in session.query(Holding).all():
            holds[h.customer_id].append(h)
        for sc in session.query(Score).all():
            scores[sc.customer_id][sc.score_type] = sc.value
        customers = {c.customer_id: c for c in session.query(Customer).all()}

        # The persisted "memory" (empty after a full reset; populated in incremental mode):
        #   • dismissals — per customer+category rejection counts (DECISIONS→ACTIONS→OUTCOMES)
        #   • recent     — products recommended within COOLDOWN_DAYS (re-spam suppression)
        dismissals: dict = defaultdict(lambda: defaultdict(int))
        recent: dict = defaultdict(set)
        acts_by_id = {a.action_id: a for a in session.query(Action).all()}
        decs_by_id = {d.decision_id: d for d in session.query(Decision).all()}
        for o in session.query(Outcome).filter(Outcome.response_type == "dismissed").all():
            act = acts_by_id.get(o.action_id)
            dec = decs_by_id.get(act.decision_id) if act else None
            cat = products.get(dec.product_id, {}).get("category") if (dec and dec.product_id) else None
            if cat:
                dismissals[o.customer_id][cat] += 1
        cutoff = NOW - timedelta(days=COOLDOWN_DAYS)
        for d in decs_by_id.values():
            if d.product_id and d.created_at and d.created_at >= cutoff:
                recent[d.customer_id].add(d.product_id)

        # Order customers by their earliest signal; --limit picks the first N customers.
        ordered = sorted(sigs_by_cust.keys(),
                         key=lambda cid: min((s.detected_at or NOW) for s in sigs_by_cust[cid]))
        if limit:
            ordered = ordered[:limit]

        counts = defaultdict(int)
        email_sent = email_fail = 0
        for cid in ordered:
            cust = customers[cid]
            sig_list = sigs_by_cust[cid]
            ctx = AgentContext(
                cust=cust, accounts=accts[cid], holdings=holds[cid], scores=scores[cid],
                products=products, history=dict(dismissals.get(cid, {})),
                active_signals=active_by_cust.get(cid, set()),
                signals=[(s.signal_type, s.source_ref, s.signal_id) for s in sig_list],
                recent_products=recent.get(cid, set()),
            )

            decision = guardrails.decide_customer(ctx)          # THE deterministic gate
            chosen_signal, chosen_sid = decision.primary_signal, decision.primary_signal_id
            product = None
            authority = None
            message_text = ""
            hypothesis = ""

            if decision.outcome == "act":
                # The LLM picks the single best fit from the vetted safe set + writes the message.
                cands = [{
                    "product_id": e["product_id"], "name": products.get(e["product_id"], {}).get("name"),
                    "description": products.get(e["product_id"], {}).get("description", ""),
                    "key_facts": products.get(e["product_id"], {}).get("key_facts", {}),
                    "category": e["category"], "moment": e["signal_type"].replace("_", " "),
                } for e in decision.safe_set]
                payload = {
                    "customer": {"first_name": cust.name.split()[0], "age": cust.age,
                                 "occupation": cust.occupation, "city_tier": cust.city_tier,
                                 "language_pref": cust.language_pref},
                    "candidates": cands,
                    "stress": (scores[cid].get("stress") or {}).get("score"),
                }
                result = llm.select_and_compose(payload)
                # Validate the LLM's pick against the safe set; fall back to the top-ranked option.
                ids = {e["product_id"] for e in decision.safe_set}
                pid = result.get("product_id") if result.get("product_id") in ids else decision.safe_set[0]["product_id"]
                entry = next(e for e in decision.safe_set if e["product_id"] == pid)
                chosen_signal, chosen_sid = entry["signal_type"], entry["signal_id"]
                product = products.get(pid)
                authority = guardrails.authority_for(chosen_signal, pid)
                message_text = result.get("message") or _fallback_message(cust)
                hypothesis = result.get("reason") or (
                    f"Selected {product.get('name')} from {len(decision.safe_set)} eligible "
                    f"option(s) for '{chosen_signal}'.")

            confidence = guardrails.confidence(chosen_signal or "", ctx)
            dec = Decision(
                customer_id=cid, mode="analyser",
                trigger_ref=f"{chosen_signal}:{chosen_sid}" if chosen_signal else "analyser:none",
                hypothesis=hypothesis, critique_result=f"[gate] {decision.reason}",
                confidence=confidence, outcome=decision.outcome,
                product_id=(product["product_id"] if product else None), created_at=NOW,
            )
            session.add(dec)
            session.flush()

            if decision.outcome == "act" and message_text:
                action = Action(
                    decision_id=dec.decision_id, customer_id=cid, authority_level=authority,
                    channel="email", message_text=message_text,
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
                        if email_fail == 1:
                            print(f"  email error: {result.get('error')}")

            for s in sig_list:
                s.status = "processed"
            counts[decision.outcome] += 1

        session.commit()

    sink = f" (email sink: {DEMO_EMAIL})" if DEMO_EMAIL else ""
    mode = "incremental" if not reset else "full reset"
    print(f"Processed {len(ordered)} customers{sink} [{mode}]")
    print(f"  act={counts['act']}  wait={counts['wait']}  escalate={counts['escalate']}")
    if send:
        print(f"  emails sent={email_sent}  failed={email_fail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process the first N customers")
    ap.add_argument("--send", action="store_true", help="actually deliver acted messages via Resend")
    ap.add_argument("--incremental", action="store_true",
                    help="keep history so dismissal back-off + the 30-day cooldown suppress repeats "
                         "(production-style); default wipes and reprocesses for a repeatable demo")
    args = ap.parse_args()
    run(limit=args.limit, send=args.send, reset=not args.incremental)


if __name__ == "__main__":
    main()
