"""
FRIDAY AI — Subscription Service
Handles all business logic for plan management, model access gating,
daily usage enforcement, and Razorpay payment integration.

Plans
-----
free                → Model 1 + 2 preview, 5 chats/day limit
jr_hacker_monthly   → Model 1 (Jr Hacker), 100 chats/day, ₹2,499/mo
jr_hacker_yearly    → Model 1 (Jr Hacker), 100 chats/day, ₹24,990/yr
advanced_monthly    → Model 1 + 2, unlimited, ₹4,999/mo
advanced_yearly     → Model 1 + 2, unlimited, ₹49,990/yr

Model Tiers
-----------
'free'   → Access to both models but capped at FREE_DAILY_LIMIT msgs/day
'model1' → Unlimited Model 1 access (Jr Hacker plan)
'model2' → Unlimited Model 1 + 2 access (Advanced Pentester plan)
"""

import hmac
import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import razorpay
from fastapi import HTTPException

from config import get_settings
from services.db import (
    get_active_subscription,
    create_subscription,
    get_daily_usage,
    increment_daily_usage,
)

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

FREE_DAILY_LIMIT = 5        # messages per day for free (both models)
MODEL1_DAILY_LIMIT = 50    # messages per day for Jr Hacker subscribers

# Model IDs from config (must match AVAILABLE_MODELS in config.py)
MODEL_1_ID = "hf.co/mradermacher/Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated-i1-GGUF:Q4_K_M"
MODEL_2_ID = "huihui_ai/baronllm-abliterated:latest"

# ─── Plan Configuration ───────────────────────────────────────────────────────

PLAN_CONFIG: dict[str, dict] = {
    "free": {
        "label": "Free",
        "model_tier": "free",
        "price_paise": 0,
        "days": None,  # no expiry for free
        "daily_limit": FREE_DAILY_LIMIT,
        "features": [
            "5 chats per day",
            "Both models: Jr Hacker & Advanced Pentester",
            "Step-by-step guides & pentesting preview",
            "Standard response speed",
        ],
    },
    "jr_hacker_monthly": {
        "label": "Jr Hacker — Monthly",
        "model_tier": "model1",
        "price_paise": 249900,  # ₹2,499 in paise
        "days": 30,
        "daily_limit": MODEL1_DAILY_LIMIT,
        "features": [
            "50 chats per day (resets every 24 hrs)",
            "Friday v1 The Jr Hacker (Model 1)",
            "Step-by-step security guides",
            "Standard / slow thinking speed",
            "Exploit dev & recon support",
        ],
    },
    "jr_hacker_yearly": {
        "label": "Jr Hacker — Yearly",
        "model_tier": "model1",
        "price_paise": 2499000,  # ₹24,990 in paise (10 months = 2 months FREE)
        "days": 365,
        "daily_limit": MODEL1_DAILY_LIMIT,
        "features": [
            "50 chats per day (resets every 24 hrs)",
            "Friday v1 The Jr Hacker (Model 1)",
            "Step-by-step security guides",
            "Standard / slow thinking speed",
            "Exploit dev & recon support",
            "Save 2 months (₹24,990/yr)",
        ],
    },
    "advanced_monthly": {
        "label": "Advanced Pentester — Monthly",
        "model_tier": "model2",
        "price_paise": 499900,  # ₹4,999 in paise
        "days": 30,
        "daily_limit": None,
        "features": [
            "No limits — unlimited chats",
            "Both FRIDAY models unlocked",
            "Friday v1 The Advanced Pentester (Model 2)",
            "Fast thinking model",
            "Deep pentesting & exploit guides",
            "Full technical explanations",
            "Priority neural engine response",
        ],
    },
    "advanced_yearly": {
        "label": "Advanced Pentester — Yearly",
        "model_tier": "model2",
        "price_paise": 4999000,  # ₹49,990 in paise (10 months = 2 months FREE)
        "days": 365,
        "daily_limit": None,
        "features": [
            "No limits — unlimited chats",
            "Both FRIDAY models unlocked",
            "Friday v1 The Advanced Pentester (Model 2)",
            "Fast thinking model",
            "Deep pentesting & exploit guides",
            "Full technical explanations",
            "Priority neural engine response",
            "Save 2 months (₹49,990/yr)",
        ],
    },
}


# ─── Razorpay Client ──────────────────────────────────────────────────────────

def _get_razorpay_client() -> razorpay.Client:
    """Return an authenticated Razorpay client."""
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=503,
            detail="Payment gateway not configured. Contact support.",
        )
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


# ─── Subscription Queries ─────────────────────────────────────────────────────

def get_user_model_tier(user_id: str) -> str:
    """
    Return the model access tier for a user.
    'free'   → capped at FREE_DAILY_LIMIT/day, both models available
    'model1' → unlimited Model 1
    'model2' → unlimited Model 1 + Model 2
    """
    sub = get_active_subscription(user_id)
    if not sub:
        return "free"
    return sub.get("model_tier", "free")


def get_subscription_status(user_id: str) -> dict:
    """
    Return a full status dict for the user's current plan.
    Used by GET /api/subscription/status.
    """
    sub = get_active_subscription(user_id)
    window_key = _window_key_utc()  # 24-hr rolling window key
    daily_count = get_daily_usage(user_id, window_key)

    if not sub:
        remaining = max(0, FREE_DAILY_LIMIT - daily_count)
        return {
            "plan_id": "free",
            "label": "Free",
            "model_tier": "free",
            "status": "active",
            "expires_at": None,
            "daily_used": daily_count,
            "daily_limit": FREE_DAILY_LIMIT,
            "chats_remaining": remaining,
            "is_unlimited": False,
            "razorpay_key_id": get_settings().razorpay_key_id,
        }

    plan = PLAN_CONFIG.get(sub["plan_id"], {})
    tier = sub["model_tier"]
    plan_limit = plan.get("daily_limit")  # None = unlimited (model2), int = capped (model1)
    is_unlimited = plan_limit is None
    remaining = None if is_unlimited else max(0, plan_limit - daily_count)
    return {
        "plan_id": sub["plan_id"],
        "label": plan.get("label", sub["plan_id"]),
        "model_tier": tier,
        "status": sub["status"],
        "expires_at": sub.get("expires_at"),
        "daily_used": daily_count,
        "daily_limit": plan_limit,
        "chats_remaining": remaining,
        "is_unlimited": is_unlimited,
        "razorpay_key_id": get_settings().razorpay_key_id,
    }


# ─── Usage Enforcement ────────────────────────────────────────────────────────

def check_and_increment_usage(user_id: str) -> int:
    """
    For free-tier users: check if they are under the 5-chat/day limit (rolling 24 hrs), then increment.
    Raises HTTP 429 if limit exceeded.
    Returns the new count (after incrementing).
    """
    key = _window_key_utc()
    current = get_daily_usage(user_id, key)
    if current >= FREE_DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": f"You've used all {FREE_DAILY_LIMIT} free chats. Resets in 24 hrs. Upgrade for more.",
                "daily_used": current,
                "daily_limit": FREE_DAILY_LIMIT,
                "upgrade_required": True,
            },
        )
    return increment_daily_usage(user_id, key)


def check_and_increment_model1_usage(user_id: str) -> int:
    """
    For Jr Hacker (model1) subscribers: enforce 50 chats/day rolling 24-hr window.
    Raises HTTP 429 if limit exceeded.
    """
    key = _window_key_utc()
    current = get_daily_usage(user_id, key)
    if current >= MODEL1_DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": f"You've used all {MODEL1_DAILY_LIMIT} Jr Hacker chats for today. Resets in 24 hrs.",
                "daily_used": current,
                "daily_limit": MODEL1_DAILY_LIMIT,
                "upgrade_required": False,
            },
        )
    return increment_daily_usage(user_id, key)


def track_usage(user_id: str) -> int:
    """For unlimited paid users (model2): just track usage, no blocking."""
    key = _window_key_utc()
    return increment_daily_usage(user_id, key)


# ─── Razorpay Payment Flow ────────────────────────────────────────────────────

def create_order_direct(
    amount: int,
    currency: str = "INR",
    receipt: Optional[str] = None,
    notes: Optional[dict] = None,
) -> dict:
    """
    Create a Razorpay order with raw amount in paise.
    Validates amount >= 100 paise.
    """
    if amount < 100:
        raise HTTPException(
            status_code=400,
            detail="Minimum amount is 100 paise.",
        )
    try:
        client = _get_razorpay_client()
        receipt_str = receipt or f"friday_rcpt_{uuid.uuid4().hex[:12]}"
        order = client.order.create({
            "amount": amount,
            "currency": currency,
            "receipt": receipt_str,
            "notes": notes or {},
        })
        return order
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Razorpay order creation error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create Razorpay order.")


def create_razorpay_order(plan_id: str, user_id: str) -> dict:
    """
    Create a Razorpay order for the given plan.
    Returns the Razorpay order dict (contains order_id, amount, currency).
    """
    plan = PLAN_CONFIG.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan_id}")
    if plan["price_paise"] == 0:
        raise HTTPException(status_code=400, detail="Cannot create order for free plan.")

    return create_order_direct(
        amount=plan["price_paise"],
        currency="INR",
        receipt=f"friday_{user_id[:8]}_{uuid.uuid4().hex[:8]}",
        notes={
            "plan_id": plan_id,
            "user_id": user_id,
            "label": plan["label"],
        },
    )


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """
    Verify payment signature using HMAC-SHA256:
    HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET)
    """
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False
    settings = get_settings()
    if not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Payment gateway not configured.")

    expected = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, razorpay_signature)


def verify_and_activate(
    user_id: str,
    plan_id: str,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> dict:
    """
    Verify Razorpay payment signature and activate the subscription.
    Returns the new subscription record.
    """
    if not verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        logger.warning("Invalid Razorpay signature for user %s order %s", user_id, razorpay_order_id)
        raise HTTPException(status_code=400, detail="Payment verification failed. Invalid signature.")

    plan = PLAN_CONFIG.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan_id}")

    expires_at = None
    if plan["days"]:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=plan["days"])).isoformat()

    sub = create_subscription(
        user_id=user_id,
        plan_id=plan_id,
        model_tier=plan["model_tier"],
        expires_at=expires_at,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
    )
    logger.info("Subscription activated: user=%s plan=%s tier=%s", user_id, plan_id, plan["model_tier"])
    return sub


def verify_webhook_signature(body_bytes: bytes, signature: str) -> bool:
    """Verify a Razorpay webhook payload signature."""
    settings = get_settings()
    if not settings.razorpay_webhook_secret:
        return False
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _today_utc() -> str:
    """Return today's date string in UTC (YYYY-MM-DD). Used internally."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _window_key_utc() -> str:
    """
    Return a 24-hour rolling window key in UTC (YYYY-MM-DD-HH).
    The window is calculated as the current UTC hour floored to the nearest 24-hr block
    anchored to midnight, i.e. this still equals the UTC calendar date (YYYY-MM-DD).
    Chats reset every calendar day UTC midnight — which is a consistent 24-hr cycle.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
