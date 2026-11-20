"""Stripe payments – switched OFF until STRIPE_SECRET_KEY is set.

Later, to turn on:
  1. pip install stripe
  2. set STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET and STRIPE_PRICE_BRONZE/SILVER/GOLD in .env
  3. implement the two functions below (Checkout Sessions) and the /stripe/webhook route in main.py
"""
from .config import settings


def enabled() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def checkout_for_quote(request_id: int, amount_cents: int, email: str) -> str | None:
    """Return a Stripe Checkout URL for paying an accepted quote (None while payments are off)."""
    if not enabled():
        return None
    raise NotImplementedError("Stripe checkout for quotes not wired up yet")


def checkout_for_plan(plan_key: str, email: str) -> str | None:
    """Return a Stripe Checkout URL for a monthly plan subscription (None while payments are off)."""
    if not enabled():
        return None
    raise NotImplementedError("Stripe subscription checkout not wired up yet")
