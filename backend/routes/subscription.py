"""
FRIDAY AI — Razorpay Standard Web Checkout & Subscription Routes
Implements:
1. POST /api/create-order & POST /api/subscription/create-order (creates order via Razorpay API)
2. POST /api/verify-payment & POST /api/subscription/verify (verifies HMAC-SHA256 signature)
3. GET  /api/subscription/status (returns plan tier and daily usage)
4. GET  /api/subscription/plans (returns available plans & pricing)
5. POST /api/subscription/webhook & POST /api/webhook (async Razorpay webhook verification)
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from config import get_settings
from routes.auth import get_current_user, get_optional_current_user
from services.subscription import (
    PLAN_CONFIG,
    get_subscription_status,
    create_order_direct,
    create_razorpay_order,
    verify_payment_signature,
    verify_and_activate,
    verify_webhook_signature,
)
from services.db import create_subscription

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Razorpay & Subscriptions"])


# ─── Request & Response Schemas ───────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    amount: Optional[int] = Field(None, description="Amount in paise (minimum 100 paise = ₹1.00)")
    currency: Optional[str] = Field("INR", description="Currency code (e.g. INR)")
    receipt: Optional[str] = Field(None, description="Optional receipt identifier")
    plan_id: Optional[str] = Field(None, description="Plan ID (e.g. jr_hacker_yearly, advanced_yearly)")
    notes: Optional[dict] = Field(None, description="Optional notes/metadata")


class VerifyPaymentRequest(BaseModel):
    order_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    payment_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    signature: Optional[str] = None
    razorpay_signature: Optional[str] = None
    plan_id: Optional[str] = None


# ─── Order Creation Core Handler ──────────────────────────────────────────────

async def _handle_create_order(
    body: CreateOrderRequest,
    user: Optional[dict] = None,
) -> dict:
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Payment gateway not configured.")

    amount = body.amount
    plan_id = body.plan_id
    currency = (body.currency or "INR").upper()
    user_id = user["id"] if user else "guest"
    notes = body.notes or {}

    # If plan_id is provided, derive price from PLAN_CONFIG
    if plan_id:
        if plan_id not in PLAN_CONFIG or plan_id == "free":
            raise HTTPException(status_code=400, detail=f"Invalid plan: {plan_id}")
        plan = PLAN_CONFIG[plan_id]
        amount = plan["price_paise"]
        notes["plan_id"] = plan_id
        notes["plan_label"] = plan.get("label", plan_id)
        notes["user_id"] = user_id

    # If neither plan_id nor amount provided
    if amount is None:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'amount' (in paise, min 100) or a valid 'plan_id'.",
        )

    # Validate amount >= 100 paise (Razorpay requirement)
    if amount < 100:
        raise HTTPException(
            status_code=400,
            detail="Minimum amount is 100 paise (₹1.00).",
        )

    receipt = body.receipt or f"rcpt_{user_id[:8]}_{uuid.uuid4().hex[:8]}"

    try:
        order = create_order_direct(
            amount=amount,
            currency=currency,
            receipt=receipt,
            notes=notes,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Razorpay API order creation error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create Razorpay order.")

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "razorpay_key_id": settings.razorpay_key_id,
        "plan_id": plan_id,
        "plan_label": PLAN_CONFIG.get(plan_id, {}).get("label") if plan_id else None,
    }


# ─── Payment Verification Core Handler ────────────────────────────────────────

async def _handle_verify_payment(
    body: VerifyPaymentRequest,
    user: Optional[dict] = None,
) -> dict:
    order_id = body.razorpay_order_id or body.order_id
    payment_id = body.razorpay_payment_id or body.payment_id
    signature = body.razorpay_signature or body.signature

    # Validate missing fields
    if not order_id or not payment_id or not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: order_id, payment_id, and signature are required.",
        )

    # Validate HMAC signature
    is_valid = verify_payment_signature(
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
    )

    if not is_valid:
        logger.warning("Payment signature verification failed for order %s", order_id)
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed. Signature mismatch.",
        )

    # If plan_id is present and user is identified, activate plan in database
    sub_record = None
    plan_id = body.plan_id
    if plan_id and plan_id in PLAN_CONFIG:
        plan = PLAN_CONFIG[plan_id]
        user_id = user["id"] if user else None
        if user_id:
            expires_at = None
            if plan["days"]:
                expires_at = (datetime.now(timezone.utc) + timedelta(days=plan["days"])).isoformat()
            sub_record = create_subscription(
                user_id=user_id,
                plan_id=plan_id,
                model_tier=plan["model_tier"],
                expires_at=expires_at,
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
            )
            logger.info("Activated subscription for user %s plan %s", user_id, plan_id)

    plan_label = PLAN_CONFIG.get(plan_id, {}).get("label", "FRIDAY Premium") if plan_id else "Payment"
    return {
        "success": True,
        "status": "active",
        "model_tier": sub_record.get("model_tier") if sub_record else (PLAN_CONFIG.get(plan_id, {}).get("model_tier", "model2") if plan_id else None),
        "message": f"🎉 Payment verified successfully! Welcome to {plan_label}.",
        "order_id": order_id,
        "payment_id": payment_id,
        "subscription": sub_record,
    }


# ─── Step 1 Endpoints: Create Order ───────────────────────────────────────────

@router.post("/api/create-order")
async def create_order_endpoint(
    body: CreateOrderRequest,
    user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Standard Razorpay order creation endpoint.
    Accepts: { amount (paise >= 100), currency, receipt, plan_id, notes }
    Returns: { order_id, amount, currency, razorpay_key_id }
    """
    return await _handle_create_order(body, user)


@router.post("/api/subscription/create-order")
async def create_subscription_order_endpoint(
    body: CreateOrderRequest,
    user: Optional[dict] = Depends(get_optional_current_user),
):
    """Alias for subscription order creation."""
    return await _handle_create_order(body, user)


# ─── Step 3 Endpoints: Verify Signature ───────────────────────────────────────

@router.post("/api/verify-payment")
async def verify_payment_endpoint(
    body: VerifyPaymentRequest,
    user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Standard Razorpay payment signature verification endpoint.
    Verifies HMAC-SHA256(order_id + "|" + payment_id, KEY_SECRET).
    Returns success only if signatures match.
    """
    return await _handle_verify_payment(body, user)


@router.post("/api/subscription/verify")
async def verify_subscription_payment_endpoint(
    body: VerifyPaymentRequest,
    user: Optional[dict] = Depends(get_optional_current_user),
):
    """Alias for subscription payment verification."""
    return await _handle_verify_payment(body, user)


# ─── Subscription Status & Plans ──────────────────────────────────────────────

@router.get("/api/subscription/status")
async def subscription_status(user: dict = Depends(get_current_user)):
    """Return authenticated operator's current subscription status & remaining chats."""
    user_id = user["id"]
    return get_subscription_status(user_id)


@router.get("/api/subscription/plans")
async def list_plans():
    """Return all available subscription plans with pricing and features (public)."""
    plans = []
    for plan_id, config in PLAN_CONFIG.items():
        if plan_id == "free":
            continue
        plans.append({
            "plan_id": plan_id,
            "label": config["label"],
            "model_tier": config["model_tier"],
            "price_paise": config["price_paise"],
            "price_inr": config["price_paise"] / 100,
            "days": config["days"],
            "daily_limit": config.get("daily_limit"),
            "is_yearly": config["days"] == 365 if config["days"] else False,
            "features": config["features"],
        })
    return {"plans": plans}


# ─── Webhook Endpoints ────────────────────────────────────────────────────────

@router.post("/api/subscription/webhook")
@router.post("/api/webhook")
async def razorpay_webhook(request: Request):
    """Handle async Razorpay webhook notifications with HMAC-SHA256 verification."""
    body_bytes = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(body_bytes, signature):
        logger.warning("Rejected Razorpay webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    import json
    try:
        payload = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    event = payload.get("event", "")
    logger.info("Razorpay webhook received: %s", event)
    return {"status": "ok", "event": event}
