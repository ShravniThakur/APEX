"""Real outbound email for Analyser actions, via Resend (APEX_README §10-11).

In non-prod EVERY message routes to config.DEMO_EMAIL (the sink) regardless of the
customer's stored address — the demo never emails real third parties. Calm, institutional
formatting per the behavioral philosophy: no urgency, no marketing styling.

Links are click-tracked: they point back at the API (/track/<action_id>...), which records the
response in OUTCOMES and then redirects to the real SBI page. So engagement is captured for real.

Failures (no key, no sink, API error) are returned, never raised, so one bad send never
breaks the batch.
"""
from __future__ import annotations

import html as _html

from ..config import DEMO_EMAIL, EMAIL_FROM, PUBLIC_URL, RESEND_API_KEY

SUBJECT = "A note about your SBI account"

_ready = False


def _ensure():
    global _ready
    if not _ready:
        import resend
        resend.api_key = RESEND_API_KEY
        _ready = True


def _links(action_id: str) -> dict:
    base = f"{PUBLIC_URL}/track/{action_id}"
    return {"open": base, "adopt": f"{base}/adopt", "dismiss": f"{base}/dismiss"}


def _render_html(message_text: str, links: dict | None) -> str:
    body = _html.escape(message_text).replace("\n", "<br>")
    parts = [
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;'
        'color:#222;line-height:1.6;max-width:560px">',
        f"<p>{body}</p>",
    ]
    if links:
        parts.append(
            f'<p><a href="{_html.escape(links["open"], quote=True)}" '
            'style="color:#1a4d8f">Open in YONO / SBI</a></p>'
        )
        parts.append(
            f'<p style="font-size:13px;color:#666">'
            f'<a href="{_html.escape(links["adopt"], quote=True)}" style="color:#1a7f4d">'
            "✓ I've completed this (demo)</a>"
            "&nbsp;&nbsp;·&nbsp;&nbsp;"
            f'<a href="{_html.escape(links["dismiss"], quote=True)}" style="color:#999">'
            "Not interested</a></p>"
        )
    parts.append('<p style="color:#999;font-size:12px">Sent by APEX on behalf of SBI. '
                 "Reply to this email if you would prefer not to receive these notes.</p>")
    parts.append("</div>")
    return "".join(parts)


def _render_text(message_text: str, links: dict | None) -> str:
    if not links:
        return message_text
    return (f"{message_text}\n\n"
            f"Open in YONO / SBI: {links['open']}\n"
            f"Completed this (demo): {links['adopt']}\n"
            f"Not interested: {links['dismiss']}")


def send(message_text: str, action_id: str | None = None, subject: str = SUBJECT) -> dict:
    """Send one Analyser message to the non-prod sink. Returns {sent, id?|error}."""
    if not RESEND_API_KEY:
        return {"sent": False, "error": "RESEND_API_KEY not set"}
    if not DEMO_EMAIL:
        return {"sent": False, "error": "APEX_DEMO_EMAIL (sink) not set"}
    links = _links(action_id) if action_id else None
    try:
        _ensure()
        import resend
        resp = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [DEMO_EMAIL],
            "subject": subject,
            "text": _render_text(message_text, links),
            "html": _render_html(message_text, links),
        })
        return {"sent": True, "id": resp.get("id") if isinstance(resp, dict) else getattr(resp, "id", None)}
    except Exception as exc:  # noqa: BLE001
        return {"sent": False, "error": f"{type(exc).__name__}: {exc}"}
