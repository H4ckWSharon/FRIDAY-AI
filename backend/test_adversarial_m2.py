"""
FRIDAY AI — Adversarial & Stress Testing Harness for Milestone 2
Challenger M2-1: Empirical verification of retired plan rejection,
price tampering defenses, edge cases, fuzzing, and grandfathered access.
"""

import hmac
import hashlib
import json
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

from main import app
from config import get_settings
from services.subscription import (
    PLAN_CONFIG,
    create_razorpay_order,
    create_order_direct,
    verify_payment_signature,
)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Isolated SQLite database for adversarial test runs."""
    db_file = str(tmp_path / "test_adversarial.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_mock_key_123")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_secret_adv_m2_xyz")
    get_settings.cache_clear()
    import importlib, services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()

    # Seed test users
    db_mod.create_user(email="attacker@evil.sec", name="Adversary", user_id="usr_attacker_99", provider="google")
    db_mod.create_user(email="victim@friday.sec", name="Victim", user_id="usr_victim_01", provider="google")
    db_mod.create_user(email="grandfathered@friday.sec", name="Grandfathered User", user_id="usr_gf_101", provider="google")

    yield db_mod
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def setup_mock_tokens():
    """Mock Firebase authentication for test operators."""
    from services.auth import set_mock_token_verifier
    def mock_verifier(token: str):
        if token == "token-attacker":
            return {"uid": "usr_attacker_99", "email": "attacker@evil.sec", "name": "Adversary", "picture": None}
        if token == "token-gf-user":
            return {"uid": "usr_gf_101", "email": "grandfathered@friday.sec", "name": "Grandfathered User", "picture": None}
        return None
    set_mock_token_verifier(mock_verifier)
    yield
    set_mock_token_verifier(None)


def generate_sig(order_id: str, payment_id: str, secret: str = "mock_secret_adv_m2_xyz") -> str:
    """Helper to generate HMAC-SHA256 signature."""
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


# ─── 1. RETIRED PLAN ORDER CREATION ADVERSARIAL CHALLENGES ───────────────────

RETIRED_PLANS = [
    "advanced_monthly",
    "advanced_yearly",
    "jr_hacker_monthly",
    "jr_hacker_yearly",
    "founder_unlimited",
    "free",
]

@pytest.mark.asyncio
@pytest.mark.parametrize("plan_id", RETIRED_PLANS)
async def test_adv_create_order_rejects_retired_plans_at_primary_endpoint(temp_db, plan_id):
    """POST /api/create-order must reject all retired or non-purchasable plans with HTTP 400."""
    headers = {"Authorization": "Bearer token-attacker"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/create-order", headers=headers, json={"plan_id": plan_id})
    assert res.status_code == 400, f"Expected 400 for retired plan {plan_id}, got {res.status_code}"
    detail = res.json().get("detail", "").lower()
    assert ("retired" in detail or "no longer offered" in detail or "invalid plan" in detail)


@pytest.mark.asyncio
@pytest.mark.parametrize("plan_id", RETIRED_PLANS)
async def test_adv_create_order_rejects_retired_plans_at_subscription_endpoint(temp_db, plan_id):
    """POST /api/subscription/create-order must reject all retired plans with HTTP 400."""
    headers = {"Authorization": "Bearer token-attacker"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/subscription/create-order", headers=headers, json={"plan_id": plan_id})
    assert res.status_code == 400, f"Expected 400 for retired plan {plan_id}, got {res.status_code}"


def test_adv_direct_service_rejects_retired_plans():
    """create_razorpay_order() service function must reject retired plans with HTTP 400."""
    from fastapi import HTTPException
    for plan_id in RETIRED_PLANS:
        with pytest.raises(HTTPException) as exc_info:
            create_razorpay_order(plan_id, "usr_attacker_99")
        assert exc_info.value.status_code == 400


# ─── 2. PRICE TAMPERING DEFENSE ON ORDER CREATION ────────────────────────────

@pytest.mark.asyncio
async def test_adv_create_order_overrides_client_supplied_tampered_price(temp_db):
    """
    Attacker passes plan_id='cyber_pro_monthly' but attempts to tamper amount to 100 paise (₹1).
    The server MUST ignore client-supplied amount and force 350,000 paise (₹3,500).
    """
    headers = {"Authorization": "Bearer token-attacker"}
    captured_payload = {}

    def mock_order_create(payload):
        captured_payload.update(payload)
        return {
            "id": "order_locked_price_01",
            "amount": payload["amount"],
            "currency": payload["currency"],
            "receipt": payload["receipt"],
        }

    mock_client = MagicMock()
    mock_client.order.create.side_effect = mock_order_create

    with patch("services.subscription._get_razorpay_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/create-order",
                headers=headers,
                json={"plan_id": "cyber_pro_monthly", "amount": 100},
            )
        assert res.status_code == 200
        # Assert server forced exact price in paise
        assert captured_payload["amount"] == 350000
        assert res.json()["amount"] == 350000


@pytest.mark.asyncio
async def test_adv_create_order_yearly_overrides_tampered_zero_price(temp_db):
    """
    Attacker passes plan_id='cyber_pro_yearly' with amount=0 or negative.
    The server MUST force 3,500,000 paise (₹35,000).
    """
    headers = {"Authorization": "Bearer token-attacker"}
    captured_payload = {}

    def mock_order_create(payload):
        captured_payload.update(payload)
        return {
            "id": "order_locked_yearly_01",
            "amount": payload["amount"],
            "currency": payload["currency"],
            "receipt": payload["receipt"],
        }

    mock_client = MagicMock()
    mock_client.order.create.side_effect = mock_order_create

    with patch("services.subscription._get_razorpay_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/create-order",
                headers=headers,
                json={"plan_id": "cyber_pro_yearly", "amount": -1000},
            )
        assert res.status_code == 200
        assert captured_payload["amount"] == 3500000
        assert res.json()["amount"] == 3500000


# ─── 3. PRICE TAMPERING & SPOOFING DEFENSE ON VERIFICATION ───────────────────

@pytest.mark.asyncio
async def test_adv_verify_payment_rejects_sub_plan_price(temp_db):
    """
    Attacker creates order for ₹1.00 (100 paise) and tries to activate cyber_pro_monthly (₹3,500).
    Verification MUST query Razorpay order and reject with HTTP 400.
    """
    headers = {"Authorization": "Bearer token-attacker"}
    order_id = "order_paid_100_paise"
    payment_id = "pay_legit_looking_100"
    valid_sig = generate_sig(order_id, payment_id)

    mock_rzp_order = {
        "id": order_id,
        "amount": 100,  # 100 paise
        "notes": {"plan_id": "cyber_pro_monthly"},
    }

    with patch("routes.subscription.fetch_razorpay_order", return_value=mock_rzp_order):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/verify-payment",
                headers=headers,
                json={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "signature": valid_sig,
                    "plan_id": "cyber_pro_monthly",
                },
            )
        assert res.status_code == 400
        assert "paid amount does not match" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_adv_verify_payment_rejects_one_paise_underpayment(temp_db):
    """
    Attacker pays 349,999 paise (1 paise short of ₹3,500).
    Verification MUST reject with HTTP 400.
    """
    headers = {"Authorization": "Bearer token-attacker"}
    order_id = "order_paid_349999"
    payment_id = "pay_legit_349999"
    valid_sig = generate_sig(order_id, payment_id)

    mock_rzp_order = {
        "id": order_id,
        "amount": 349999,
        "notes": {"plan_id": "cyber_pro_monthly"},
    }

    with patch("routes.subscription.fetch_razorpay_order", return_value=mock_rzp_order):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/verify-payment",
                headers=headers,
                json={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "signature": valid_sig,
                    "plan_id": "cyber_pro_monthly",
                },
            )
        assert res.status_code == 400
        assert "paid amount does not match" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_adv_verify_payment_rejects_plan_tier_escalation(temp_db):
    """
    Attacker pays ₹3,500 (350,000 paise) for cyber_pro_monthly, but attempts
    to verify and claim cyber_pro_yearly (₹35,000).
    Both price check (350,000 < 3,500,000) and plan mismatch check must reject.
    """
    headers = {"Authorization": "Bearer token-attacker"}
    order_id = "order_paid_monthly"
    payment_id = "pay_paid_monthly"
    valid_sig = generate_sig(order_id, payment_id)

    mock_rzp_order = {
        "id": order_id,
        "amount": 350000,
        "notes": {"plan_id": "cyber_pro_monthly"},
    }

    with patch("routes.subscription.fetch_razorpay_order", return_value=mock_rzp_order):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/verify-payment",
                headers=headers,
                json={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "signature": valid_sig,
                    "plan_id": "cyber_pro_yearly",
                },
            )
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_adv_verify_payment_rejects_plan_spoofing_even_if_amount_matches(temp_db):
    """
    Attacker creates order for ₹35,000 with notes {'plan_id': 'cyber_pro_monthly'},
    then tries to claim 'cyber_pro_yearly'. Server checks order notes and detects spoofing.
    """
    headers = {"Authorization": "Bearer token-attacker"}
    order_id = "order_spoof_notes"
    payment_id = "pay_spoof_notes"
    valid_sig = generate_sig(order_id, payment_id)

    mock_rzp_order = {
        "id": order_id,
        "amount": 3500000,
        "notes": {"plan_id": "cyber_pro_monthly"},
    }

    with patch("routes.subscription.fetch_razorpay_order", return_value=mock_rzp_order):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/verify-payment",
                headers=headers,
                json={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "signature": valid_sig,
                    "plan_id": "cyber_pro_yearly",
                },
            )
        assert res.status_code == 400
        assert "plan mismatch" in res.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("retired_id,amount", [
    ("jr_hacker_monthly", 249900),
    ("jr_hacker_yearly", 2499000),
    ("advanced_monthly", 499900),
    ("advanced_yearly", 4999000),
    ("founder_unlimited", 0),
    ("free", 0),
])
async def test_adv_verify_payment_must_reject_retired_plans(temp_db, retired_id, amount):
    """
    POST /api/verify-payment must reject activating retired plans with HTTP 400.
    A user cannot bypass checkout by paying a legacy plan's amount and activating a retired tier.
    """
    headers = {"Authorization": "Bearer token-attacker"}
    order_id = f"order_legacy_{retired_id[:6]}"
    payment_id = f"pay_legacy_{retired_id[:6]}"
    valid_sig = generate_sig(order_id, payment_id)

    mock_rzp_order = {
        "id": order_id,
        "amount": amount,
        "notes": {},
    }

    with patch("routes.subscription.fetch_razorpay_order", return_value=mock_rzp_order):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/verify-payment",
                headers=headers,
                json={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "signature": valid_sig,
                    "plan_id": retired_id,
                },
            )
    assert res.status_code == 400, (
        f"Security Flaw: /api/verify-payment accepted retired plan '{retired_id}' "
        f"and returned status {res.status_code} instead of 400!"
    )


# ─── 4. EDGE-CASE PLAN IDS & FUZZING ATTACKS ────────────────────────────────

FUZZ_PLAN_IDS = [
    "../",
    "../../etc/passwd",
    "..\\..\\windows\\system32",
    "",
    "   ",
    "' OR 1=1 --",
    "'; DROP TABLE subscriptions; --",
    "<script>alert('xss')</script>",
    "CYBER_PRO_MONTHLY",
    "cyber_pro_monthly ",
    " cyber_pro_monthly",
    "cyber_pro_monthly\x00",
    "nonexistent_plan_xyz_9999",
    "a" * 4096,
]

@pytest.mark.asyncio
@pytest.mark.parametrize("fuzz_id", FUZZ_PLAN_IDS)
async def test_adv_create_order_rejects_fuzzed_plan_ids(temp_db, fuzz_id):
    """POST /api/create-order must reject malicious/fuzzed plan_ids with HTTP 400."""
    headers = {"Authorization": "Bearer token-attacker"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/create-order", headers=headers, json={"plan_id": fuzz_id})
    assert res.status_code == 400, f"Expected 400 for fuzzed plan_id: {fuzz_id!r}, got {res.status_code}"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_amount", [-10000, -1, 0, 1, 99])
async def test_adv_create_order_rejects_invalid_raw_amounts(temp_db, bad_amount):
    """POST /api/create-order must reject amounts < 100 paise."""
    headers = {"Authorization": "Bearer token-attacker"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/create-order", headers=headers, json={"amount": bad_amount})
    assert res.status_code == 400
    assert "minimum amount is 100 paise" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_adv_create_order_empty_payload_rejected(temp_db):
    """POST /api/create-order with empty payload {} returns 400."""
    headers = {"Authorization": "Bearer token-attacker"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/create-order", headers=headers, json={})
    assert res.status_code == 400
    assert "must provide either 'amount'" in res.json()["detail"].lower()


# ─── 5. ANTI-REPLAY AND SIGNATURE TAMPERING ATTACKS ─────────────────────────

@pytest.mark.asyncio
async def test_adv_anti_replay_prevents_duplicate_activation(temp_db):
    """Submitting the exact same order and payment ID a second time must return 409 Conflict."""
    headers = {"Authorization": "Bearer token-attacker"}
    order_id = "order_replay_101"
    payment_id = "pay_replay_101"
    valid_sig = generate_sig(order_id, payment_id)

    mock_rzp_order = {
        "id": order_id,
        "amount": 350000,
        "notes": {"plan_id": "cyber_pro_monthly"},
    }

    with patch("routes.subscription.fetch_razorpay_order", return_value=mock_rzp_order):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1st attempt: Successful activation
            res1 = await ac.post(
                "/api/verify-payment",
                headers=headers,
                json={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "signature": valid_sig,
                    "plan_id": "cyber_pro_monthly",
                },
            )
            assert res1.status_code == 200

            # 2nd attempt: Replay attack with identical parameters
            res2 = await ac.post(
                "/api/verify-payment",
                headers=headers,
                json={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "signature": valid_sig,
                    "plan_id": "cyber_pro_monthly",
                },
            )
            assert res2.status_code == 409
            assert "already been processed" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_adv_tampered_signature_rejected(temp_db):
    """Flipping even a single character in the HMAC signature causes HTTP 400."""
    headers = {"Authorization": "Bearer token-attacker"}
    order_id = "order_sig_test"
    payment_id = "pay_sig_test"
    valid_sig = generate_sig(order_id, payment_id)
    tampered_sig = ("0" if valid_sig[0] != "0" else "1") + valid_sig[1:]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/verify-payment",
            headers=headers,
            json={
                "order_id": order_id,
                "payment_id": payment_id,
                "signature": tampered_sig,
            },
        )
    assert res.status_code == 400
    assert "signature mismatch" in res.json()["detail"].lower()


# ─── 6. GRANDFATHERED SUBSCRIBER PRESERVATION INTEGRITY ─────────────────────

@pytest.mark.asyncio
async def test_adv_grandfathered_active_subscriber_unaffected_by_new_pricing(temp_db):
    """
    A customer who previously purchased advanced_monthly (legacy) must:
    1. Retain active status in GET /api/subscription/status.
    2. Retain model_tier='model2' and is_unlimited=True.
    3. Preserve their original expiration date.
    4. Not be downgraded or blocked.
    """
    future_expiry = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
    temp_db.create_subscription(
        user_id="usr_gf_101",
        plan_id="advanced_monthly",
        model_tier="model2",
        expires_at=future_expiry,
        razorpay_order_id="order_gf_active_99",
        razorpay_payment_id="pay_gf_active_99",
    )

    headers = {"Authorization": "Bearer token-gf-user"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/subscription/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "active"
    assert data["plan_id"] == "advanced_monthly"
    assert data["model_tier"] == "model2"
    assert data["is_unlimited"] is True
    assert data["expires_at"] == future_expiry


@pytest.mark.asyncio
async def test_adv_expired_legacy_subscriber_cannot_renew_retired_plan(temp_db):
    """
    A legacy customer whose subscription has expired CANNOT purchase/renew
    a legacy plan. Attempting to create an order for advanced_monthly returns 400.
    """
    past_expiry = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    temp_db.create_subscription(
        user_id="usr_gf_101",
        plan_id="advanced_monthly",
        model_tier="model2",
        expires_at=past_expiry,
        razorpay_order_id="order_gf_expired_01",
        razorpay_payment_id="pay_gf_expired_01",
    )

    headers = {"Authorization": "Bearer token-gf-user"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Check status shows not active/unlimited
        status_res = await ac.get("/api/subscription/status", headers=headers)
        assert status_res.status_code == 200
        assert status_res.json()["is_unlimited"] is False

        # Attempt to renew retired plan
        renew_res = await ac.post(
            "/api/create-order",
            headers=headers,
            json={"plan_id": "advanced_monthly"},
        )
        assert renew_res.status_code == 400
        assert "retired or no longer offered" in renew_res.json()["detail"].lower()
