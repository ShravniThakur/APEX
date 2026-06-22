"""Customer-response capture — writes the OUTCOMES table (the feedback loop).

clicked / dismissed / ignored are captured for real (tracked link, dismiss link, time sweep).
completed (adoption) genuinely needs SBI's CBS in production; for the demo, `adopt` simulates
it — it logs `completed` AND creates a HOLDING, so the substrate reflects that the customer now
holds the product (which also makes future sweeps skip them: natural suppression).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from ..database.models import Action, Decision, Holding, Outcome

# Responses that close the response window (no further outreach expected for this action).
_CLOSING = {"dismissed", "completed", "ignored"}


def _set_outcome(session, action: Action, response_type: str) -> Outcome:
    """Upsert one outcome per action — the latest/strongest response wins."""
    o = session.query(Outcome).filter(Outcome.action_id == action.action_id).first()
    if o is None:
        o = Outcome(action_id=action.action_id, customer_id=action.customer_id)
        session.add(o)
    o.response_type = response_type
    o.responded_at = datetime.utcnow()
    o.response_window_closed = response_type in _CLOSING
    return o


def record_click(session, action: Action):
    _set_outcome(session, action, "clicked")
    session.commit()


def record_dismiss(session, action: Action):
    _set_outcome(session, action, "dismissed")
    session.commit()


def record_adopt(session, action: Action):
    """Demo stand-in for the CBS read that would confirm adoption: log completed + add the holding."""
    _set_outcome(session, action, "completed")
    dec = session.get(Decision, action.decision_id)
    if dec and dec.product_id:
        session.add(Holding(
            customer_id=action.customer_id, product_id=dec.product_id,
            units=1, current_value=None, acquired_date=datetime.utcnow().date(),
        ))
    session.commit()


def mark_ignored(session, days: int = 7) -> int:
    """Any sent action older than `days` with no response yet → ignored (window closed)."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    n = 0
    for a in session.query(Action).filter(Action.sent_at.isnot(None), Action.sent_at < cutoff):
        if session.query(Outcome).filter(Outcome.action_id == a.action_id).first() is None:
            session.add(Outcome(
                action_id=a.action_id, customer_id=a.customer_id,
                response_type="ignored", responded_at=datetime.utcnow(),
                response_window_closed=True,
            ))
            n += 1
    session.commit()
    return n
