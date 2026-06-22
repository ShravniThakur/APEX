"""ORM -> plain-JSON serializers for the API. Explicit (UUID->str, Decimal->float) so the
shape the frontend consumes is predictable and stable.
"""
from __future__ import annotations


def _dt(v):
    return v.isoformat() if v else None


def _f(v):
    return float(v) if v is not None else None


def score(sc) -> dict:
    return {"type": sc.score_type, "value": sc.value, "computed_at": _dt(sc.computed_at)}


def signal(s) -> dict:
    return {
        "id": str(s.signal_id), "type": s.signal_type, "source_ref": s.source_ref,
        "detected_at": _dt(s.detected_at), "status": s.status,
    }


def outcome(o) -> dict | None:
    if o is None:
        return None
    return {"response_type": o.response_type, "responded_at": _dt(o.responded_at),
            "window_closed": o.response_window_closed}


def action(a, oc=None) -> dict | None:
    if a is None:
        return None
    return {
        "id": str(a.action_id), "authority_level": a.authority_level, "channel": a.channel,
        "message_text": a.message_text, "deep_link": a.deep_link, "sent_at": _dt(a.sent_at),
        "response": outcome(oc),
    }


def decision(d, act=None, oc=None) -> dict:
    return {
        "id": str(d.decision_id), "mode": d.mode, "trigger_ref": d.trigger_ref,
        "hypothesis": d.hypothesis, "critique_result": d.critique_result,
        "confidence": _f(d.confidence), "outcome": d.outcome, "product_id": d.product_id,
        "created_at": _dt(d.created_at), "rm_status": d.rm_status, "action": action(act, oc),
    }


def account(a) -> dict:
    return {
        "id": str(a.account_id), "account_type": a.account_type, "balance": _f(a.balance),
        "status": a.status, "opened_date": _dt(a.opened_date),
    }


def holding(h) -> dict:
    return {"id": str(h.holding_id), "product_id": h.product_id, "current_value": _f(h.current_value)}


def transaction(t) -> dict:
    return {
        "id": str(t.txn_id), "amount": _f(t.amount), "direction": t.direction,
        "merchant_category": t.merchant_category, "channel": t.channel,
        "payee_id": t.payee_id, "txn_time": _dt(t.txn_time),
        "is_manual_recurring": t.is_manual_recurring,
    }


def customer_base(c) -> dict:
    return {
        "id": str(c.customer_id), "name": c.name, "age": c.age, "gender": c.gender,
        "city_tier": c.city_tier, "language_pref": c.language_pref, "occupation": c.occupation,
        "customer_type": c.customer_type, "kyc_status": c.kyc_status,
        "monthly_income": _f(c.monthly_income), "owns_property": c.owns_property,
        "dependents": c.dependents, "owns_gold": c.owns_gold,
        "has_papl_offer": c.has_papl_offer, "has_card_offer": c.has_card_offer,
    }


def customer_summary(c, signals, decisions) -> dict:
    out = customer_base(c)
    out["signal_count"] = len(signals)
    out["signal_types"] = sorted({s.signal_type for s in signals})
    outcomes = [d.outcome for d in decisions]
    out["decision_outcomes"] = {o: outcomes.count(o) for o in set(outcomes)}
    return out
