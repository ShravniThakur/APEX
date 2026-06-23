"""APEX HTTP API (FastAPI) — read surface for the bank-ops dashboard + pipeline triggers.

    uvicorn apex.api.app:app --reload --port 8000     # then open http://localhost:8000/docs

Read endpoints expose the reasoning trace (customer -> scores -> signals -> decisions ->
actions). Pipeline endpoints re-run scoring / detection / the agent loop on demand (the
dashboard's "refresh" + the basis for the demo's simulate mechanic).
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import PUBLIC_URL
from ..database.db import SessionLocal
from ..database.models import (
    Account, Action, Customer, Decision, Holding, Outcome, Product, Score, Signal, Transaction,
)
from . import serializers as S

app = FastAPI(title="APEX API", version="0.1.0")

# Dev CORS — the Vite frontend (localhost:5173) calls this directly.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Read
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats(db: Session = Depends(get_db)):
    signals = db.query(Signal).all()
    decisions = db.query(Decision).all()
    sig_by_type = defaultdict(int)
    for s in signals:
        sig_by_type[s.signal_type] += 1
    dec_by_outcome = defaultdict(int)
    for d in decisions:
        dec_by_outcome[d.outcome] += 1
    return {
        "customers": db.query(Customer).count(),
        "signals": len(signals),
        "signals_by_type": dict(sorted(sig_by_type.items())),
        "decisions": len(decisions),
        "decisions_by_outcome": dict(dec_by_outcome),
        "emails_sent": db.query(Action).filter(Action.sent_at.isnot(None)).count(),
        "escalations_open": db.query(Decision).filter(
            Decision.outcome == "escalate", Decision.rm_status != "resolved").count(),
    }


@app.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    sigs, decs = defaultdict(list), defaultdict(list)
    for s in db.query(Signal).all():
        sigs[s.customer_id].append(s)
    for d in db.query(Decision).all():
        decs[d.customer_id].append(d)
    return [S.customer_summary(c, sigs[c.customer_id], decs[c.customer_id]) for c in customers]


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    cust = db.get(Customer, customer_id)
    if cust is None:
        raise HTTPException(404, "customer not found")

    actions_by_decision = {a.decision_id: a for a in
                           db.query(Action).filter(Action.customer_id == customer_id)}
    outcomes_by_action = {o.action_id: o for o in
                          db.query(Outcome).filter(Outcome.customer_id == customer_id)}
    decisions = db.query(Decision).filter(Decision.customer_id == customer_id) \
        .order_by(Decision.created_at).all()
    txns = db.query(Transaction).filter(Transaction.customer_id == customer_id) \
        .order_by(Transaction.txn_time.desc()).limit(25).all()

    def _decision(d):
        act = actions_by_decision.get(d.decision_id)
        outcome = outcomes_by_action.get(act.action_id) if act else None
        return S.decision(d, act, outcome)

    out = S.customer_base(cust)
    out["accounts"] = [S.account(a) for a in
                       db.query(Account).filter(Account.customer_id == customer_id)]
    out["holdings"] = [S.holding(h) for h in
                       db.query(Holding).filter(Holding.customer_id == customer_id)]
    out["scores"] = [S.score(sc) for sc in
                     db.query(Score).filter(Score.customer_id == customer_id)]
    out["signals"] = [S.signal(s) for s in
                      db.query(Signal).filter(Signal.customer_id == customer_id)]
    out["decisions"] = [_decision(d) for d in decisions]
    out["recent_transactions"] = [S.transaction(t) for t in txns]
    return out


@app.get("/products")
def list_products(db: Session = Depends(get_db)):
    return [{"product_id": p.product_id, "name": p.name, "category": p.category,
             "depth": p.depth, "landing_url": p.landing_url, "tax_saving": p.tax_saving,
             "description": p.description, "primary_use": p.primary_use}
            for p in db.query(Product).all()]


@app.get("/insights/{customer_id}")
def insights(customer_id: str, db: Session = Depends(get_db)):
    """Customer-facing 'money at a glance' + APEX's suggestions. The suggestions are the agent's
    own act-decisions (already ethics-filtered: a wait/escalate produces no action) — so this is
    APEX's reasoning shown in-app, not a generic budgeting tracker."""
    cust = db.get(Customer, customer_id)
    if cust is None:
        raise HTTPException(404, "customer not found")

    balance = sum(float(a.balance or 0) for a in
                  db.query(Account).filter(Account.customer_id == customer_id))
    spend, credits = defaultdict(float), 0.0
    for t in db.query(Transaction).filter(Transaction.customer_id == customer_id):
        if t.direction == "debit":
            spend[t.merchant_category or "other"] += float(t.amount)
        else:
            credits += float(t.amount)
    top = sorted(spend.items(), key=lambda kv: -kv[1])[:5]

    decisions = {d.decision_id: d for d in db.query(Decision).filter(Decision.customer_id == customer_id)}
    outcomes = {o.action_id: o for o in db.query(Outcome).filter(Outcome.customer_id == customer_id)}
    suggestions = []
    for a in db.query(Action).filter(Action.customer_id == customer_id):
        oc = outcomes.get(a.action_id)
        d = decisions.get(a.decision_id)
        base = f"{PUBLIC_URL}/track/{a.action_id}"
        suggestions.append({
            "action_id": str(a.action_id),
            "message_text": a.message_text,
            "product_id": d.product_id if d else None,
            "open_url": base, "adopt_url": f"{base}/adopt", "dismiss_url": f"{base}/dismiss",
            "why_url": f"{PUBLIC_URL}/explain/{a.action_id}",
            "response": oc.response_type if oc else None,
        })

    return {
        "balance": balance,
        "monthly_income": float(cust.monthly_income) if cust.monthly_income is not None else None,
        "credits_90d": round(credits, 2),
        "spend_by_category": [{"category": c, "amount": round(v, 2)} for c, v in top],
        "suggestions": suggestions,
    }


@app.get("/explain/{action_id}")
def explain_action(action_id: str, db: Session = Depends(get_db)):
    """Customer-facing 'Why am I seeing this?' — a constrained, plain-language explanation built ONLY
    from a fact the customer can already see in their own account. If the outreach traces back to a
    vulnerable moment, it deliberately DECLINES to elaborate, so the customer can't reverse-engineer
    that something sensitive was detected (APEX_README §6). Defense in depth: the decline check is in
    code; the LLM only ever sees the non-sensitive case."""
    from ..agent import guardrails, llm

    a = db.get(Action, action_id)
    if a is None:
        raise HTTPException(404, "action not found")
    dec = db.get(Decision, a.decision_id)
    cust = db.get(Customer, a.customer_id)
    trigger = (dec.trigger_ref or "") if dec else ""
    signal_type, _, ref_id = trigger.partition(":")

    # Sensitive if the trigger is itself a vulnerability signal, the outreach is a re-engagement
    # (which only ever stems from a held-back / sensitive moment), or the customer is in a vulnerable
    # moment right now (an active life_event, or severe financial stress).
    sensitive = signal_type in guardrails.VULNERABILITY_SIGNALS or trigger.startswith("reengage:")
    if not sensitive:
        active = {s.signal_type for s in db.query(Signal).filter(Signal.customer_id == a.customer_id)}
        stress_row = db.query(Score).filter(
            Score.customer_id == a.customer_id, Score.score_type == "stress").first()
        stress = (stress_row.value or {}).get("score", 0.0) if stress_row else 0.0
        sensitive = bool(active & guardrails.VULNERABILITY_SIGNALS) or stress >= guardrails.SEVERE_STRESS

    if sensitive:
        return {"action_id": action_id, "declined": True,
                "explanation": "We reached out as part of looking out for your overall financial "
                               "wellbeing — there's nothing you need to read into it, and nothing you "
                               "have to do. We're here whenever you'd like to talk something through."}

    source_ref = None
    if ref_id:
        sig = db.get(Signal, ref_id)
        source_ref = sig.source_ref if sig else None
    product = None
    if dec and dec.product_id:
        p = db.get(Product, dec.product_id)
        if p:
            product = {"name": p.name, "description": p.description}
    payload = {
        "customer": {"first_name": (cust.name.split()[0] if cust else "there"),
                     "language_pref": (cust.language_pref if cust else None)},
        "signal_type": signal_type or "your account activity",
        "source_ref": source_ref, "product": product,
    }
    text = llm.explain(payload)
    if not text:                                        # graceful degrade (no key / failure)
        basis = source_ref or (signal_type or "recent activity").replace("_", " ")
        text = (f"You're seeing this because of something in your own account ({basis}). "
                "It's only a suggestion — act on it any time, or ignore it.")
    return {"action_id": action_id, "declined": False, "explanation": text}


# --------------------------------------------------------------------------- #
# RM escalation queue — where a human relationship manager picks up the cases the
# gate refused to auto-act on (churn risk, severe stress with only unsecured debt, no
# eligible product). Closes the `escalate` path: a real inbox, not a dead end.
# --------------------------------------------------------------------------- #
@app.get("/escalations")
def escalations(include_resolved: bool = False, db: Session = Depends(get_db)):
    q = db.query(Decision).filter(Decision.outcome == "escalate")
    if not include_resolved:
        q = q.filter(Decision.rm_status != "resolved")
    rows = q.order_by(Decision.created_at.desc()).all()
    custs = {c.customer_id: c for c in db.query(Customer).all()}
    out = []
    for d in rows:
        c = custs.get(d.customer_id)
        out.append({
            "decision_id": str(d.decision_id),
            "customer_id": str(d.customer_id),
            "customer_name": c.name if c else None,
            "city_tier": c.city_tier if c else None,
            "language_pref": c.language_pref if c else None,
            "monthly_income": float(c.monthly_income) if c and c.monthly_income is not None else None,
            "signal": (d.trigger_ref or "").split(":", 1)[0],
            "hypothesis": d.hypothesis,
            "reason": d.critique_result,
            "confidence": float(d.confidence) if d.confidence is not None else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "rm_status": d.rm_status or "open",
        })
    return out


@app.post("/escalations/{decision_id}/resolve")
def resolve_escalation(decision_id: str, db: Session = Depends(get_db)):
    d = db.get(Decision, decision_id)
    if d is None or d.outcome != "escalate":
        raise HTTPException(404, "escalation not found")
    d.rm_status = "resolved"
    db.commit()
    return {"ok": True, "decision_id": decision_id, "rm_status": "resolved"}


# --------------------------------------------------------------------------- #
# Pipeline triggers (synchronous — fine at demo scale; agent calls the LLM)
# --------------------------------------------------------------------------- #
@app.post("/pipeline/score")
def pipeline_score():
    from ..ml.score import score_all
    score_all()
    return {"ok": True, "step": "score"}


@app.post("/pipeline/detect")
def pipeline_detect():
    from ..signals.detect import detect_all
    detect_all()
    return {"ok": True, "step": "detect"}


@app.post("/pipeline/agent")
def pipeline_agent(limit: int | None = None, send: bool = False, reset: bool = True):
    from ..agent.loop import run as run_agent
    run_agent(limit=limit, send=send, reset=reset)  # reset=false → incremental (suppression on)
    return {"ok": True, "step": "agent", "limit": limit, "send": send, "reset": reset}


@app.post("/pipeline/reengage")
def pipeline_reengage(days: int = 3, send: bool = False):
    """Revisit WAIT decisions whose acute window has passed and send a gentle, product-free
    insight (APEX_README §6). days=0 revisits all waits now (demo pacing)."""
    from ..agent.reengage import run as run_reengage
    res = run_reengage(days=days, send=send)
    return {"ok": True, "step": "reengage", **res}


@app.post("/pipeline/run-all")
def pipeline_run_all(send: bool = False):
    from ..ml.score import score_all
    from ..signals.detect import detect_all
    from ..agent.loop import run as run_agent
    score_all()
    detect_all()
    run_agent(send=send)
    return {"ok": True, "steps": ["score", "detect", "agent"], "send": send}


# --------------------------------------------------------------------------- #
# Conversational modes (Guide / Concierge) + voice
# --------------------------------------------------------------------------- #
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    mode: str = "concierge"               # guide | concierge
    customer_id: str | None = None        # required for concierge
    messages: list[ChatMessage]


@app.post("/chat")
def chat(req: ChatRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    msgs = [m.model_dump() for m in req.messages]
    if req.mode == "concierge":
        if not req.customer_id:
            raise HTTPException(400, "concierge mode requires a customer_id")
        from ..agent.concierge import answer
        reply_text = answer(req.customer_id, msgs)
        # After replying, mine the conversation for stated intents → SIGNALS (best-effort, runs
        # in the background so it never delays the reply). The ethical split lives in intent.py.
        from ..agent.intent import extract_and_store
        background.add_task(extract_and_store, req.customer_id,
                            msgs + [{"role": "assistant", "content": reply_text}])
        return {"reply": reply_text}
    # Guide is for new/prospective customers; `customer_id`, when present (e.g. a signed-in demo
    # identity), lets it look up an unfinished application — the Tier-2 drop-off path.
    from ..agent.guide import reply
    return {"reply": reply(msgs, db, identity=req.customer_id)}


@app.post("/voice/transcribe")
async def voice_transcribe(file: UploadFile = File(...)):
    from ..agent.voice import transcribe
    data = await file.read()
    return {"text": transcribe(file.filename or "audio.webm", data)}


# --------------------------------------------------------------------------- #
# Demo mechanic — "simulate 3 months of activity" (Guide -> Analyser transition)
# --------------------------------------------------------------------------- #
@app.get("/demo/scenarios")
def demo_scenarios():
    from ..demo import SCENARIOS
    return [{"key": k, "label": v["label"]} for k, v in SCENARIOS.items()]


@app.post("/demo/simulate")
def demo_simulate(scenario: str = "idle_balance"):
    from ..demo import simulate
    try:
        return simulate(scenario)
    except KeyError:
        raise HTTPException(404, f"unknown scenario '{scenario}'")


# --------------------------------------------------------------------------- #
# Outcome capture — click tracking + adopt/dismiss + ignored sweep (the feedback loop)
# --------------------------------------------------------------------------- #
def _confirm_page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<html><body style='font-family:Arial;max-width:520px;margin:80px auto;color:#222'>"
        f"<h2 style='color:#1a4d8f'>APEX</h2><h3>{title}</h3><p style='color:#555'>{body}</p>"
        f"</body></html>"
    )


@app.get("/track/{action_id}")
def track_click(action_id: str, db: Session = Depends(get_db)):
    from ..agent import feedback
    a = db.get(Action, action_id)
    if a is None:
        raise HTTPException(404, "action not found")
    feedback.record_click(db, a)
    return RedirectResponse(a.deep_link or "/", status_code=302)


@app.get("/track/{action_id}/adopt")
def track_adopt(action_id: str, db: Session = Depends(get_db)):
    from ..agent import feedback
    a = db.get(Action, action_id)
    if a is None:
        raise HTTPException(404, "action not found")
    feedback.record_adopt(db, a)
    return _confirm_page(
        "Recorded as adopted (demo)",
        "For this demo we've logged this as adopted and added it to your holdings. In production "
        "APEX would learn this directly from SBI's systems — and would stop nudging you about it.",
    )


@app.get("/track/{action_id}/dismiss")
def track_dismiss(action_id: str, db: Session = Depends(get_db)):
    from ..agent import feedback
    a = db.get(Action, action_id)
    if a is None:
        raise HTTPException(404, "action not found")
    feedback.record_dismiss(db, a)
    return _confirm_page("Got it", "We won't nudge you about this again.")


@app.post("/pipeline/expire-outcomes")
def expire_outcomes(days: int = 7):
    from ..agent import feedback
    with SessionLocal() as session:
        n = feedback.mark_ignored(session, days=days)
    return {"ok": True, "marked_ignored": n}
