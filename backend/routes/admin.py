"""
FRIDAY AI — Administrator & Founder Analytics Route
Provides:
  - GET  /api/admin/users              — Comprehensive metrics & list of all operators, subscriptions, tiers & expiry
  - POST /api/admin/grant-subscription — Direct admin override to grant/extend plans to any user
  - POST /api/admin/revoke-subscription— Revoke paid access and return user to Free tier
  - GET  /admin, /admin.html           — Serve the standalone admin dashboard HTML
"""

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from routes.auth import get_current_user
from services.subscription import (
    is_admin_or_founder,
    FOUNDER_EMAILS,
    _FOUNDER_USER_IDS,
    PLAN_CONFIG,
    _window_key_utc,
)
from services.db import (
    get_db,
    get_daily_usage,
    get_user_by_email,
    get_user_by_id,
    create_subscription,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin & Founder Telemetry"])


# ─── Security Dependency ──────────────────────────────────────────────────────

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure caller has founder or admin privileges."""
    user_id = current_user.get("id")
    email = (current_user.get("email") or "").strip().lower()

    if email in FOUNDER_EMAILS or (user_id and user_id in _FOUNDER_USER_IDS) or is_admin_or_founder(user_id):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. Administrator / Founder clearance required.",
    )


# ─── Request Schemas ──────────────────────────────────────────────────────────

class GrantSubscriptionRequest(BaseModel):
    user_email_or_id: str = Field(..., description="User email or Firebase UID")
    plan_id: str = Field(..., description="Target plan ID: free, jr_hacker_monthly, advanced_monthly, founder_unlimited, etc.")
    days: Optional[int] = Field(30, description="Duration in days (or None for permanent)")


class RevokeSubscriptionRequest(BaseModel):
    user_email_or_id: str = Field(..., description="User email or Firebase UID")


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _resolve_user(email_or_id: str) -> Optional[dict]:
    """Find user record by email or by ID."""
    clean = email_or_id.strip()
    if "@" in clean:
        return get_user_by_email(clean.lower())
    return get_user_by_id(clean) or get_user_by_email(clean.lower())


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/api/admin/users")
async def get_admin_users(admin: dict = Depends(require_admin)):
    """
    Return comprehensive platform telemetry:
    - High-level KPI summary (Total users, Paid, Free, Founders, Expiring soon)
    - Full list of users with current plan, model tier, expiration, and daily chats
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    window_key = _window_key_utc()

    with get_db() as conn:
        # Cross-engine query: get each user and their latest active subscription
        sql = """
            SELECT 
                u.id, u.email, u.name, u.avatar, u.provider, u.created_at,
                s.id as sub_id, s.plan_id, s.model_tier, s.status as sub_status,
                s.starts_at, s.expires_at, s.razorpay_order_id, s.razorpay_payment_id
            FROM users u
            LEFT JOIN subscriptions s ON s.id = (
                SELECT s2.id FROM subscriptions s2
                WHERE s2.user_id = u.id AND s2.status = 'active'
                ORDER BY s2.created_at DESC LIMIT 1
            )
            ORDER BY u.created_at DESC
        """
        rows = conn.execute(sql).fetchall()

        # Conversation counts per user
        conv_rows = conn.execute(
            "SELECT user_id, count(*) as count FROM conversations WHERE user_id IS NOT NULL GROUP BY user_id"
        ).fetchall()
        conv_map = {dict(r)["user_id"]: int(dict(r)["count"]) for r in conv_rows}

        # Daily usage in current rolling window
        usage_rows = conn.execute(
            "SELECT user_id, count FROM daily_usage WHERE date = ?", (window_key,)
        ).fetchall()
        usage_map = {dict(r)["user_id"]: int(dict(r)["count"]) for r in usage_rows}

    users_data = []
    paid_count = 0
    free_count = 0
    founder_count = 0
    expiring_soon_count = 0
    model2_count = 0
    model1_count = 0
    seven_days_from_now = now + timedelta(days=7)

    for raw_row in rows:
        row = dict(raw_row)
        uid = row["id"]
        email = (row.get("email") or "").strip().lower()
        is_founder = is_admin_or_founder(uid) or email in FOUNDER_EMAILS

        sub_id = row.get("sub_id")
        plan_id = row.get("plan_id")
        raw_tier = row.get("model_tier")
        sub_status = row.get("sub_status")
        expires_at = row.get("expires_at")
        starts_at = row.get("starts_at")

        # Determine effective status and tier
        if is_founder:
            effective_plan = "founder_unlimited"
            effective_tier = "model2"
            effective_status = "active"
            display_expires = None
            days_remaining = None
            is_unlimited = True
            founder_count += 1
            model2_count += 1
        elif sub_id and sub_status == "active":
            # Check if expired
            is_expired = False
            if expires_at:
                try:
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp_dt <= now:
                        is_expired = True
                except Exception:
                    if expires_at <= now_iso:
                        is_expired = True

            if is_expired:
                effective_plan = "free"
                effective_tier = "free"
                effective_status = "expired"
                display_expires = expires_at
                days_remaining = -1
                is_unlimited = False
                free_count += 1
            else:
                effective_plan = plan_id or "free"
                effective_tier = raw_tier or "model1"
                effective_status = "active"
                display_expires = expires_at
                is_unlimited = (effective_tier == "model2")
                paid_count += 1
                if effective_tier == "model2":
                    model2_count += 1
                else:
                    model1_count += 1

                # Calculate days remaining
                if expires_at:
                    try:
                        exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        rem = (exp_dt - now).total_seconds() / 86400.0
                        days_remaining = max(0, round(rem, 1))
                        if exp_dt <= seven_days_from_now:
                            expiring_soon_count += 1
                    except Exception:
                        days_remaining = None
                else:
                    days_remaining = None
        else:
            effective_plan = "free"
            effective_tier = "free"
            effective_status = "free"
            display_expires = None
            days_remaining = None
            is_unlimited = False
            free_count += 1

        daily_used = usage_map.get(uid, 0)
        plan_meta = PLAN_CONFIG.get(effective_plan, PLAN_CONFIG["free"])

        users_data.append({
            "id": uid,
            "email": row["email"],
            "name": row["name"] or "Operator",
            "avatar": row.get("avatar"),
            "provider": row.get("provider") or "google-firebase",
            "created_at": row["created_at"],
            "is_founder": is_founder,
            "plan_id": effective_plan,
            "plan_label": plan_meta.get("label", effective_plan),
            "model_tier": effective_tier,
            "status": effective_status,
            "starts_at": starts_at,
            "expires_at": display_expires,
            "days_remaining": days_remaining,
            "is_unlimited": is_unlimited,
            "daily_used": daily_used,
            "daily_limit": plan_meta.get("daily_limit"),
            "conversations_count": conv_map.get(uid, 0),
            "razorpay_order_id": row.get("razorpay_order_id"),
            "razorpay_payment_id": row.get("razorpay_payment_id"),
        })

    return {
        "summary": {
            "total_users": len(users_data),
            "paid_users": paid_count,
            "free_users": free_count,
            "founder_users": founder_count,
            "expiring_soon": expiring_soon_count,
            "model2_users": model2_count,
            "model1_users": model1_count,
        },
        "users": users_data,
        "plans": PLAN_CONFIG,
        "server_time": now_iso,
    }


@router.post("/api/admin/grant-subscription")
async def grant_subscription(body: GrantSubscriptionRequest, admin: dict = Depends(require_admin)):
    """Admin endpoint to grant or update a user's subscription tier."""
    user = _resolve_user(body.user_email_or_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{body.user_email_or_id}' not found in database.",
        )

    target_uid = user["id"]
    plan_id = body.plan_id.strip()

    if plan_id not in PLAN_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan_id '{plan_id}'. Available: {list(PLAN_CONFIG.keys())}",
        )

    plan_meta = PLAN_CONFIG[plan_id]
    model_tier = plan_meta.get("model_tier", "free")

    if plan_id == "free":
        # Cancel any active subscription
        with get_db() as conn:
            conn.execute(
                "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = ? AND status = 'active'",
                (target_uid,),
            )
        return {
            "status": "success",
            "message": f"User {user['email']} reverted to Free plan.",
            "user_id": target_uid,
            "plan_id": "free",
            "model_tier": "free",
            "expires_at": None,
        }

    now = datetime.now(timezone.utc)
    if plan_id == "founder_unlimited" or body.days is None:
        expires_at = None
    else:
        expires_at = (now + timedelta(days=max(1, body.days))).isoformat()

    sub = create_subscription(
        user_id=target_uid,
        plan_id=plan_id,
        model_tier=model_tier,
        expires_at=expires_at,
        razorpay_order_id=f"admin_grant_by_{admin.get('id', 'admin')[:8]}",
        razorpay_payment_id="admin_override_grant",
    )

    logger.info(
        "Admin %s granted %s (%s) to user %s (expires: %s)",
        admin.get("email"), plan_id, model_tier, user["email"], expires_at,
    )

    return {
        "status": "success",
        "message": f"Successfully granted {plan_meta['label']} to {user['email']}.",
        "subscription": sub,
    }


@router.post("/api/admin/revoke-subscription")
async def revoke_subscription(body: RevokeSubscriptionRequest, admin: dict = Depends(require_admin)):
    """Admin endpoint to cancel an active subscription and return user to Free tier."""
    user = _resolve_user(body.user_email_or_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{body.user_email_or_id}' not found.",
        )

    target_uid = user["id"]
    with get_db() as conn:
        conn.execute(
            "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = ? AND status = 'active'",
            (target_uid,),
        )

    logger.info("Admin %s revoked subscription for user %s", admin.get("email"), user["email"])
    return {
        "status": "success",
        "message": f"Subscription revoked for {user['email']}. User is now on Free tier.",
        "user_id": target_uid,
    }


@router.get("/admin", include_in_schema=False)
@router.get("/admin.html", include_in_schema=False)
async def serve_admin_dashboard():
    """Serve the admin dashboard web application."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "admin.html",
        Path(__file__).resolve().parent.parent / "admin.html",
        Path("/opt/friday/admin.html"),
    ]
    for p in candidates:
        if p.exists():
            return FileResponse(p, media_type="text/html")
    raise HTTPException(status_code=404, detail="Admin dashboard file (admin.html) not found.")
