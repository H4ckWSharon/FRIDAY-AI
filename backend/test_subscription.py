"""
FRIDAY AI — Subscription & Razorpay Test Suite
Verifies plan configuration, access gating (free 5 chats/day, Model 2 paywall),
Razorpay order creation, payment signature verification, and plan activation.
"""

import hmac
import hashlib
import json
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

from main import app
from config import get_settings
from services.subscription import (
    PLAN_CONFIG,
    FREE_DAILY_LIMIT,
    MODEL_1_ID,
    MODEL_2_ID,
)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Isolated SQLite database for subscription test runs."""
    db_file = str(tmp_path / "test_subscription.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_mock_key_123")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_secret_abc123xyz")
    get_settings.cache_clear()
    import importlib, services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()

    # Pre-create test users
    db_mod.create_user(email="free_user@friday.sec", name="Free Operator", user_id="usr_free_101", provider="google")
    db_mod.create_user(email="paid_user@friday.sec", name="Paid Operator", user_id="usr_paid_202", provider="google")

    yield db_mod
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def setup_mock_tokens():
    """Mock Firebase authentication for test operators."""
    from services.auth import set_mock_token_verifier
    def mock_verifier(token: str):
        if token == "token-free-user":
            return {"uid": "usr_free_101", "email": "free_user@friday.sec", "name": "Free Operator", "picture": None}
        if token == "token-paid-user":
            return {"uid": "usr_paid_202", "email": "paid_user@friday.sec", "name": "Paid Operator", "picture": None}
        return None
    set_mock_token_verifier(mock_verifier)
    yield
    set_mock_token_verifier(None)


@pytest.mark.asyncio
async def test_get_plans_returns_configured_pricing(temp_db):
    """GET /api/subscription/plans returns Model 1 Monthly (₹2499) and Model 2 Monthly (₹4999)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/subscription/plans")
    assert res.status_code == 200
    plans = res.json()["plans"]
    plan_map = {p["plan_id"]: p for p in plans}

    assert "jr_hacker_monthly" in plan_map
    assert plan_map["jr_hacker_monthly"]["price_inr"] == 2499.0
    assert plan_map["jr_hacker_monthly"]["model_tier"] == "model1"

    assert "advanced_monthly" in plan_map
    assert plan_map["advanced_monthly"]["price_inr"] == 4999.0
    assert plan_map["advanced_monthly"]["model_tier"] == "model2"

    assert "jr_hacker_yearly" in plan_map
    assert plan_map["jr_hacker_yearly"]["price_inr"] == 24990.0

    assert "advanced_yearly" in plan_map
    assert plan_map["advanced_yearly"]["price_inr"] == 49990.0


@pytest.mark.asyncio
async def test_free_user_status_and_daily_limit(temp_db):
    """GET /api/subscription/status returns 5 chats/day limit for free users."""
    headers = {"Authorization": "Bearer token-free-user"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/subscription/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["model_tier"] == "free"
    assert data["daily_limit"] == 5
    assert data["daily_used"] == 0
    assert data["chats_remaining"] == 5
    assert data["is_unlimited"] is False


@pytest.mark.asyncio
async def test_free_user_can_chat_model_1_and_increments_usage(temp_db):
    """Free users can chat with Model 1 (Jr Hacker) and usage increments."""
    headers = {"Authorization": "Bearer token-free-user"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": MODEL_1_ID,
                "stream": False,
            },
        )
    assert res.status_code == 200

    # Status check should show 1 used
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        status_res = await ac.get("/api/subscription/status", headers=headers)
    assert status_res.json()["daily_used"] == 1
    assert status_res.json()["chats_remaining"] == 4


@pytest.mark.asyncio
async def test_free_user_can_use_both_models_within_limit(temp_db):
    """Free users can use both Model 1 and Model 2 within their 5 chats/day limit."""
    headers = {"Authorization": "Bearer token-free-user"}
    with patch("routes.chat.chat_complete", return_value="Exploit analysis simulation."):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "run exploit test"}],
                    "model": MODEL_2_ID,
                    "stream": False,
                },
            )
        assert res.status_code == 200

    # Model 1 subscribers, however, are blocked from Model 2 with 403
    secret = "mock_secret_abc123xyz"
    order_id = "order_m1_sub"
    payment_id = "pay_m1_sub"
    valid_sig = hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(
            "/api/verify-payment",
            headers=headers,
            json={
                "plan_id": "jr_hacker_monthly",
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": valid_sig,
            },
        )
        res_blocked = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "run exploit test"}],
                "model": MODEL_2_ID,
                "stream": False,
            },
        )
    assert res_blocked.status_code == 403
    data = res_blocked.json()
    assert data["detail"]["upgrade_required"] is True
    assert data["detail"]["required_tier"] == "model2"


@pytest.mark.asyncio
async def test_free_user_hitting_limit_returns_429(temp_db):
    """When a free user hits 5 messages, subsequent chat returns HTTP 429."""
    headers = {"Authorization": "Bearer token-free-user"}
    from services.subscription import _today_utc
    today = _today_utc()

    # Pre-set 5 usage counts in DB
    for _ in range(5):
        temp_db.increment_daily_usage("usr_free_101", today)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "sixth message"}],
                "model": MODEL_1_ID,
                "stream": False,
            },
        )
    assert res.status_code == 429
    detail = res.json()["detail"]
    assert detail["error"] == "daily_limit_reached"
    assert detail["upgrade_required"] is True


@pytest.mark.asyncio
async def test_razorpay_order_creation(temp_db):
    """POST /api/create-order and /api/subscription/create-order create orders."""
    headers = {"Authorization": "Bearer token-free-user"}

    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_mock_test_999",
        "amount": 249900,
        "currency": "INR",
        "receipt": "friday_receipt_123",
    }

    with patch("services.subscription._get_razorpay_client", return_value=mock_client):
        # 1. Via /api/create-order
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/create-order",
                headers=headers,
                json={"plan_id": "jr_hacker_monthly"},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["order_id"] == "order_mock_test_999"
        assert data["amount"] == 249900

        # 2. Direct amount in paise (minimum 100 paise)
        mock_client.order.create.return_value = {
            "id": "order_mock_direct_500",
            "amount": 5000,
            "currency": "INR",
            "receipt": "friday_rcpt_custom",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res_direct = await ac.post(
                "/api/create-order",
                headers=headers,
                json={"amount": 5000, "currency": "INR"},
            )
        assert res_direct.status_code == 200
        assert res_direct.json()["order_id"] == "order_mock_direct_500"


@pytest.mark.asyncio
async def test_create_order_rejects_sub_100_paise(temp_db):
    """POST /api/create-order rejects amount < 100 paise with HTTP 400."""
    headers = {"Authorization": "Bearer token-free-user"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/create-order",
            headers=headers,
            json={"amount": 50, "currency": "INR"},
        )
    assert res.status_code == 400
    assert "minimum amount is 100 paise" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_payment_signature_mismatch_returns_400(temp_db):
    """POST /api/verify-payment returns HTTP 400 if HMAC signature does not match."""
    headers = {"Authorization": "Bearer token-free-user"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/verify-payment",
            headers=headers,
            json={
                "order_id": "order_test_999",
                "payment_id": "pay_test_999",
                "signature": "completely_invalid_signature_hex",
            },
        )
    assert res.status_code == 400
    assert "signature mismatch" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_payment_missing_fields_returns_400(temp_db):
    """POST /api/verify-payment returns HTTP 400 if required fields are missing."""
    headers = {"Authorization": "Bearer token-free-user"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/verify-payment",
            headers=headers,
            json={"order_id": "order_only"},
        )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_verify_payment_and_activate_plan(temp_db):
    """POST /api/verify-payment activates plan after HMAC verification and unlocks models."""
    headers = {"Authorization": "Bearer token-free-user"}
    secret = "mock_secret_abc123xyz"
    order_id = "order_test_888"
    payment_id = "pay_test_777"

    # Compute valid signature
    valid_sig = hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/verify-payment",
            headers=headers,
            json={
                "plan_id": "advanced_yearly",
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": valid_sig,
            },
        )
    assert res.status_code == 200
    assert res.json()["status"] == "active"
    assert res.json()["model_tier"] == "model2"

    # Now verify user status: is_unlimited should be True and model_tier == model2
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        status_res = await ac.get("/api/subscription/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["model_tier"] == "model2"
    assert status_data["is_unlimited"] is True

    # Now Model 2 should NOT be blocked for this user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        chat_res = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": MODEL_2_ID,
                "stream": False,
            },
        )
    assert chat_res.status_code == 200
