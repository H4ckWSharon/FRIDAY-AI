"""
FRIDAY AI — Firebase Authentication Routes & Centralized Dependency
Implements:
  - Centralized FastAPI dependency `get_current_user` requiring cryptographically valid Firebase ID tokens
  - Extraction and persistence of Firebase UID as the stable operator identity
  - Profile endpoint GET /api/auth/me
  - Token verification endpoint POST /api/auth/verify
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, status
from pydantic import BaseModel, Field

from services.auth import verify_firebase_token
from services.db import (
    create_user,
    upsert_firebase_user,
    get_user_by_id,
    get_user_by_email,
    update_user_profile,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ─── Request Schemas ─────────────────────────────────────────────────────────

class TokenVerifyRequest(BaseModel):
    id_token: str = Field(..., min_length=1, description="Firebase ID Token from Web SDK")


import time

_USER_CACHE: dict[str, tuple[float, dict]] = {}
_USER_CACHE_TTL = 300.0  # 5 minutes


def clear_user_cache() -> None:
    """Clear in-memory user cache (useful for testing and user invalidation)."""
    _USER_CACHE.clear()


# ─── Centralized Auth Dependencies ──────────────────────────────────────────

def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Extract authenticated operator from Authorization: Bearer <Firebase ID Token>.
    Returns user dict with 'id' equal to Firebase UID, or None if unauthenticated.
    Uses in-memory cache to eliminate cloud DB queries on repeat requests.
    """
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:].strip()
    if not token:
        return None

    verified = verify_firebase_token(token)
    if not verified or not verified.get("uid"):
        return None

    uid = verified["uid"]
    now_ts = time.time()
    cached = _USER_CACHE.get(uid)
    if cached and cached[0] > now_ts:
        return cached[1]

    email = verified.get("email") or f"{uid}@firebase.user"
    name = verified.get("name") or "Operator"
    picture = verified.get("picture")

    user_record = upsert_firebase_user(
        user_id=uid,
        email=email,
        name=name,
        avatar=picture,
        provider="google-firebase",
    )
    _USER_CACHE[uid] = (now_ts + _USER_CACHE_TTL, user_record)
    return user_record


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Strict FastAPI dependency for protected routes (/api/chat, /api/conversations, /api/auth/me).
    Requires a valid, non-expired Firebase ID token in Authorization: Bearer <token>.
    Raises HTTP 401 Unauthorized on missing, malformed, or invalid tokens.
    Uses in-memory cache to eliminate cloud DB queries on repeat requests.
    """
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in with Google or Email.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token cannot be empty.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    verified = verify_firebase_token(token)
    if not verified or not verified.get("uid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = verified["uid"]
    now_ts = time.time()
    cached = _USER_CACHE.get(uid)
    if cached and cached[0] > now_ts:
        return cached[1]

    email = verified.get("email") or f"{uid}@firebase.user"
    name = verified.get("name") or "Operator"
    picture = verified.get("picture")

    user_record = upsert_firebase_user(
        user_id=uid,
        email=email,
        name=name,
        avatar=picture,
        provider="google-firebase",
    )
    _USER_CACHE[uid] = (now_ts + _USER_CACHE_TTL, user_record)
    return user_record


def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Return authenticated user record if valid token provided, otherwise None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    if not token:
        return None
    verified = verify_firebase_token(token)
    if not verified or not verified.get("uid"):
        return None
    uid = verified["uid"]
    email = verified.get("email") or f"{uid}@firebase.user"
    name = verified.get("name") or "Operator"
    picture = verified.get("picture")
    return upsert_firebase_user(
        user_id=uid,
        email=email,
        name=name,
        avatar=picture,
        provider="google-firebase",
    )


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Retrieve profile of the current authenticated Firebase operator."""
    return {
        "uid": user["id"],
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "avatar": user["avatar"],
        "provider": user["provider"],
        "created_at": user["created_at"],
    }


@router.post("/verify")
async def verify_token_endpoint(body: TokenVerifyRequest):
    """
    Explicitly verify a Firebase ID Token received from the Web SDK.
    Returns operator profile if valid, raises HTTP 401 if invalid.
    """
    verified = verify_firebase_token(body.id_token)
    if not verified or not verified.get("uid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = verified["uid"]
    email = verified.get("email") or f"{uid}@firebase.user"
    name = verified.get("name") or "Operator"
    picture = verified.get("picture")

    user = get_user_by_id(uid)
    if not user:
        user = create_user(
            email=email,
            name=name,
            avatar=picture,
            provider="google-firebase",
            user_id=uid,
        )

    return {
        "uid": user["id"],
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "avatar": user["avatar"],
        "provider": user["provider"],
    }
