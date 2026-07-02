from __future__ import annotations

import os
from typing import Any


def stripe_status() -> dict[str, Any]:
    return {
        "configured": bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_PRICE_ID")),
        "mode": "live-or-test-by-key",
        "required_env": ["STRIPE_SECRET_KEY", "STRIPE_PRICE_ID", "STRIPE_WEBHOOK_SECRET"],
    }


def create_checkout_session(success_url: str, cancel_url: str) -> dict[str, Any]:
    if not os.getenv("STRIPE_SECRET_KEY"):
        return {"ok": False, "error": "STRIPE_SECRET_KEY not set"}
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": os.getenv("STRIPE_PRICE_ID"), "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"ok": True, "id": session.id, "url": session.url}
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}
