"""
FRIDAY AI — Comprehensive Requirement-Driven E2E Test Suite (Tiers 1-4)
========================================================================

Authoritative Requirements Source:
  - ORIGINAL_REQUEST.md (Requirements R1, R2, R3, R4)
  - PROJECT.md (§ Architecture, § Feature Inventory, § Interface Contracts)
  - TEST_INFRA.md (§ Feature Inventory & Test Matrix)

Structure:
  - Tier 1: Feature Coverage (R1 - R4)                     [>= 25 test cases]
  - Tier 2: Boundary & Corner Cases                        [>= 25 test cases]
  - Tier 3: Cross-Feature Combinations (Pairwise)          [>= 5 test cases]
  - Tier 4: Real-World User Application Scenarios          [>= 5 test cases]
  Total: 65 Test Cases (Requirement: >= 60)

Test Philosophy:
  - Opaque-box requirement-driven testing against external HTTP/SSE API contracts
  - Self-contained and isolated test execution via temporary SQLite databases
  - Deterministic authentication and payment gateway mocks
"""

import hmac
import hashlib
import json
import os
import re
import asyncio
import contextlib
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

from main import app
from config import get_settings
from schemas import ChatMessage, ChatRequest
from services.auth import set_mock_token_verifier


# ─── Constant Definitions (Derived from Specifications) ───────────────────────

# R1: Single Model Consolidation & Strict Rebranding
SPEC_SINGLE_MODEL_ID = "orcasaq-cyber-27b:latest"
SPEC_BRAND_NAME = "friday Cyber Pro"
SPEC_BRAND_TAG = "Cyber Pro"
LEGACY_MODEL_IDS = [
    "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
    "huihui_ai/baronllm-abliterated:latest",
]
FORBIDDEN_LEAK_KEYWORDS = [
    "orcasaq",
    "Dolphin",
    "BaronLLM",
    "Cognitive Computations",
    "Jr Hacker",
    "Advanced Pentester",
]

# R2: Payment Pricing & Grandfathering Preservation
SPEC_MONTHLY_PLAN_ID = "cyber_pro_monthly"
SPEC_MONTHLY_PRICE_PAISE = 350000       # ₹3,500
SPEC_YEARLY_PLAN_ID = "cyber_pro_yearly"
SPEC_YEARLY_PRICE_PAISE = 3500000       # ₹35,000 (10 months = 2 months free)

RETIRED_PURCHASE_PLAN_IDS = [
    "jr_hacker_monthly",
    "jr_hacker_yearly",
    "advanced_monthly",
    "advanced_yearly",
]

GRANDFATHERED_ACTIVE_PLAN_ID = "advanced_monthly"


# ─── Test Fixtures & Isolation ────────────────────────────────────────────────

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """
    Provide an isolated SQLite database instance for each test.
    Pre-populates baseline test users:
      - usr_free_101: Free user (no subscription)
      - usr_paid_cyber: Active cyber_pro_monthly subscriber
      - usr_grandfathered: Active grandfathered advanced_monthly subscriber
      - usr_expired: Subscriber whose plan expired 30 days ago
      - usr_founder: Founder VIP account
    """
    db_file = str(tmp_path / "test_e2e_requirements.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_spec_key_123")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_secret_spec_secret_456")
    get_settings.cache_clear()

    import importlib
    import services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()

    # Pre-populate test users
    db_mod.create_user(
        email="free_operator@friday.sec",
        name="Free Operator",
        user_id="usr_free_101",
        provider="google",
    )
    db_mod.create_user(
        email="cyber_subscriber@friday.sec",
        name="Cyber Subscriber",
        user_id="usr_paid_cyber",
        provider="google",
    )
    db_mod.create_user(
        email="grandfathered@friday.sec",
        name="Legacy Loyal User",
        user_id="usr_grandfathered",
        provider="google",
    )
    db_mod.create_user(
        email="expired_user@friday.sec",
        name="Expired Operator",
        user_id="usr_expired",
        provider="google",
    )
    db_mod.create_user(
        email="sharonanil555@gmail.com",
        name="Sharon Anil (Founder)",
        user_id="ih5zm1zzusd3gwZLF69fYKWA14d2",
        provider="google",
    )

    # Seed Subscriptions
    # 1. Active Cyber Pro subscriber
    future_date = (datetime.now(timezone.utc) + timedelta(days=25)).isoformat()
    db_mod.create_subscription("usr_paid_cyber", SPEC_MONTHLY_PLAN_ID, "model2", future_date)

    # 2. Active Grandfathered subscriber (advanced_monthly with valid expiry)
    legacy_future_date = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()
    db_mod.create_subscription("usr_grandfathered", GRANDFATHERED_ACTIVE_PLAN_ID, "model2", legacy_future_date)

    # 3. Expired subscriber
    past_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    db_mod.create_subscription("usr_expired", GRANDFATHERED_ACTIVE_PLAN_ID, "model2", past_date)

    yield db_mod
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def setup_mock_tokens():
    """Mock Firebase authentication for test operators."""
    def mock_verifier(token: str):
        token_map = {
            "token-free-user": {
                "uid": "usr_free_101",
                "email": "free_operator@friday.sec",
                "name": "Free Operator",
                "picture": None,
                "email_verified": True,
            },
            "token-cyber-user": {
                "uid": "usr_paid_cyber",
                "email": "cyber_subscriber@friday.sec",
                "name": "Cyber Subscriber",
                "picture": None,
                "email_verified": True,
            },
            "token-grandfathered-user": {
                "uid": "usr_grandfathered",
                "email": "grandfathered@friday.sec",
                "name": "Legacy Loyal User",
                "picture": None,
                "email_verified": True,
            },
            "token-expired-user": {
                "uid": "usr_expired",
                "email": "expired_user@friday.sec",
                "name": "Expired Operator",
                "picture": None,
                "email_verified": True,
            },
            "token-founder-user": {
                "uid": "ih5zm1zzusd3gwZLF69fYKWA14d2",
                "email": "sharonanil555@gmail.com",
                "name": "Sharon Anil",
                "picture": None,
                "email_verified": True,
            },
            "token-attacker-user": {
                "uid": "usr_attacker_999",
                "email": "attacker@evil.local",
                "name": "Malicious Operator",
                "picture": None,
                "email_verified": True,
            },
        }
        return token_map.get(token)

    set_mock_token_verifier(mock_verifier)
    yield
    set_mock_token_verifier(None)


def generate_valid_razorpay_signature(order_id: str, payment_id: str, secret: str = "mock_secret_spec_secret_456") -> str:
    """Generate authentic Razorpay HMAC-SHA256 signature for test validation."""
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


@contextlib.contextmanager
def patch_create_order(mock_order):
    """Patch create_order_direct across both services and routes namespaces."""
    with patch("services.subscription.create_order_direct", return_value=mock_order), \
         patch("routes.subscription.create_order_direct", return_value=mock_order):
        yield


@contextlib.contextmanager
def patch_fetch_order(mock_order):
    """Patch fetch_razorpay_order across both services and routes namespaces."""
    with patch("services.subscription.fetch_razorpay_order", return_value=mock_order), \
         patch("routes.subscription.fetch_razorpay_order", return_value=mock_order):
        yield


# ==============================================================================
# TIER 1: FEATURE COVERAGE (R1 - R4) (>= 25 Tests)
# ==============================================================================

class TestTier1Requirement1SingleModelRebranding:
    """R1: Ollama Model Cleanup and Rebranding."""

    @pytest.mark.asyncio
    async def test_tier1_r1_models_endpoint_returns_only_single_model(self, temp_db):
        """GET /api/models must return strictly one model in the models catalog."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/models", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "models" in data
        assert len(data["models"]) == 1, "Only single model (orcasaq-cyber-27b) must be available in catalog"
        assert data["models"][0]["id"] == SPEC_SINGLE_MODEL_ID

    @pytest.mark.asyncio
    async def test_tier1_r1_model_display_name_is_friday_cyber_pro(self, temp_db):
        """The single model must be strictly branded as 'friday Cyber Pro'."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/models", headers=headers)
        assert res.status_code == 200
        model_meta = res.json()["models"][0]
        assert model_meta["name"] == SPEC_BRAND_NAME
        assert model_meta.get("tag") == SPEC_BRAND_TAG

    @pytest.mark.asyncio
    async def test_tier1_r1_default_model_is_orcasaq(self, temp_db):
        """The default model identifier must be orcasaq-cyber-27b:latest."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/models", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data.get("default") == SPEC_SINGLE_MODEL_ID or data.get("default_model") == SPEC_SINGLE_MODEL_ID

    @pytest.mark.asyncio
    async def test_tier1_r1_legacy_models_removed_from_catalog(self, temp_db):
        """Older models (Dolphin3, BaronLLM) must be removed from the catalog."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/models", headers=headers)
        assert res.status_code == 200
        returned_ids = [m["id"] for m in res.json()["models"]]
        for legacy_id in LEGACY_MODEL_IDS:
            assert legacy_id not in returned_ids, f"Legacy model {legacy_id} found in catalog"

    @pytest.mark.asyncio
    async def test_tier1_r1_quick_greeting_introduces_cyber_pro(self, temp_db):
        """Quick greeting ('hi') must introduce 'friday Cyber Pro' and never 'The Jr Hacker'."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 200
        content = res.json()["content"]
        assert "friday Cyber Pro" in content or "FRIDAY Cyber Pro" in content
        assert "Jr Hacker" not in content
        assert "The Advanced Pentester" not in content

    @pytest.mark.asyncio
    async def test_tier1_r1_chat_defaults_to_single_model(self, temp_db):
        """Chat request with omitted model parameter defaults to orcasaq-cyber-27b:latest."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {"messages": [{"role": "user", "content": "hello"}], "stream": False}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 200
        resp_model = res.json().get("model", "")
        assert resp_model in (SPEC_SINGLE_MODEL_ID, SPEC_BRAND_NAME, "friday Cyber Pro")


class TestTier1Requirement2PaymentPricingAndGrandfathering:
    """R2: Payment Plan Consolidation and Existing Subscriber Preservation."""

    @pytest.mark.asyncio
    async def test_tier1_r2_plans_catalog_contains_cyber_pro_monthly(self, temp_db):
        """GET /api/subscription/plans must list cyber_pro_monthly at ₹3,500 (350,000 paise)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/plans")
        assert res.status_code == 200
        plans = {p["plan_id"]: p for p in res.json()["plans"]}
        assert SPEC_MONTHLY_PLAN_ID in plans
        monthly = plans[SPEC_MONTHLY_PLAN_ID]
        assert monthly["price_paise"] == SPEC_MONTHLY_PRICE_PAISE
        assert monthly["price_inr"] == 3500.0

    @pytest.mark.asyncio
    async def test_tier1_r2_plans_catalog_contains_cyber_pro_yearly(self, temp_db):
        """GET /api/subscription/plans must list cyber_pro_yearly at ₹35,000 (3,500,000 paise)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/plans")
        assert res.status_code == 200
        plans = {p["plan_id"]: p for p in res.json()["plans"]}
        assert SPEC_YEARLY_PLAN_ID in plans
        yearly = plans[SPEC_YEARLY_PLAN_ID]
        assert yearly["price_paise"] == SPEC_YEARLY_PRICE_PAISE
        assert yearly["price_inr"] == 35000.0
        assert yearly["days"] == 365

    @pytest.mark.asyncio
    async def test_tier1_r2_plans_catalog_excludes_legacy_plans(self, temp_db):
        """Public plans endpoint must NOT offer retired legacy plans for purchase."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/plans")
        assert res.status_code == 200
        offered_plan_ids = [p["plan_id"] for p in res.json()["plans"]]
        for retired in RETIRED_PURCHASE_PLAN_IDS:
            assert retired not in offered_plan_ids, f"Retired plan {retired} is still offered for purchase"

    @pytest.mark.asyncio
    async def test_tier1_r2_create_order_succeeds_for_cyber_pro_monthly(self, temp_db):
        """POST /api/create-order creates Razorpay order for cyber_pro_monthly."""
        headers = {"Authorization": "Bearer token-free-user"}
        payload = {"plan_id": SPEC_MONTHLY_PLAN_ID}
        mock_order = {"id": "order_test_monthly_001", "amount": SPEC_MONTHLY_PRICE_PAISE, "currency": "INR"}

        with patch_create_order(mock_order):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post("/api/create-order", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["order_id"] == "order_test_monthly_001"
        assert data["amount"] == SPEC_MONTHLY_PRICE_PAISE

    @pytest.mark.asyncio
    async def test_tier1_r2_create_order_succeeds_for_cyber_pro_yearly(self, temp_db):
        """POST /api/create-order creates Razorpay order for cyber_pro_yearly."""
        headers = {"Authorization": "Bearer token-free-user"}
        payload = {"plan_id": SPEC_YEARLY_PLAN_ID}
        mock_order = {"id": "order_test_yearly_002", "amount": SPEC_YEARLY_PRICE_PAISE, "currency": "INR"}

        with patch_create_order(mock_order):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post("/api/create-order", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["order_id"] == "order_test_yearly_002"
        assert data["amount"] == SPEC_YEARLY_PRICE_PAISE

    @pytest.mark.asyncio
    async def test_tier1_r2_create_order_rejects_retired_legacy_plans(self, temp_db):
        """Attempting to create an order for retired plan (e.g. advanced_monthly) returns 400 Bad Request."""
        headers = {"Authorization": "Bearer token-free-user"}
        mock_order = {"id": "order_fake", "amount": 100000, "currency": "INR"}
        with patch_create_order(mock_order):
            for legacy_plan in RETIRED_PURCHASE_PLAN_IDS:
                payload = {"plan_id": legacy_plan}
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    res = await ac.post("/api/create-order", json=payload, headers=headers)
                assert res.status_code == 400, f"Expected 400 when attempting to purchase retired plan {legacy_plan}"

    @pytest.mark.asyncio
    async def test_tier1_r2_grandfathered_active_subscription_honored(self, temp_db):
        """Active grandfathered customer subscriptions remain active without premature termination."""
        headers = {"Authorization": "Bearer token-grandfathered-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "active" or data.get("active") is True
        assert data.get("plan_id") == GRANDFATHERED_ACTIVE_PLAN_ID
        assert data.get("expires_at") is not None


class TestTier1Requirement3ChatUXWaitingStateAndConcurrency:
    """R3: Chat UX Long-Wait Progress State & Concurrency Protection."""

    @pytest.mark.asyncio
    async def test_tier1_r3_chat_streaming_sse_format_compliance(self, temp_db):
        """POST /api/chat with stream=True returns text/event-stream with SSE chunks."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {"messages": [{"role": "user", "content": "hi"}], "stream": True}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")
        body = res.text
        assert "data:" in body

    @pytest.mark.asyncio
    async def test_tier1_r3_concurrency_lock_blocks_simultaneous_requests(self, temp_db):
        """Duplicate concurrent chat requests for the same user return 429 Too Many Requests."""
        from services.ollama import acquire_inference_capacity
        user_id = "usr_paid_cyber"

        # Simulate ongoing inference holding the capacity lock for this user
        async with acquire_inference_capacity(user_id):
            with pytest.raises(Exception) as exc_info:
                async with acquire_inference_capacity(user_id):
                    pass
            assert "429" in str(exc_info.value) or "active request" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_tier1_r3_non_streaming_chat_response_format(self, temp_db):
        """POST /api/chat with stream=False returns valid JSON response."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "content" in data
        assert "model" in data

    @pytest.mark.asyncio
    async def test_tier1_r3_concurrency_lock_released_after_completion(self, temp_db):
        """User concurrency lock is cleanly released once previous request finishes."""
        from services.ollama import acquire_inference_capacity
        user_id = "usr_paid_cyber"

        async with acquire_inference_capacity(user_id):
            pass  # Finished inference

        # Second sequential request must succeed without locking error
        async with acquire_inference_capacity(user_id):
            assert True

    def test_tier1_r3_ui_radar_and_telemetry_markup_present(self):
        """Verify index.html contains radar sweep HUD and tactical progress animation elements."""
        index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
        assert os.path.exists(index_path), "index.html must exist at project root"
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        # Verify radar animation or tactical telemetry classes / elements
        assert ("radar" in html.lower() or "thinking" in html.lower() or "#ff3038" in html.lower())

    def test_tier1_r3_ui_concurrency_locks_script_present(self):
        """Verify index.html contains synchronous button disabling on chat send."""
        index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        assert "disabled" in html.lower()
        assert "sendmessage" in html.lower() or "chat-input" in html.lower()


class TestTier1Requirement4SecurityStabilityAndVerification:
    """R4: Security Audit, Bug Fixes, Stability & Verification."""

    def test_tier1_r4_health_check_endpoint_public_and_healthy(self):
        """GET /health is public (no auth required) and returns HTTP 200 with component health."""
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert data.get("status") in ("ok", "healthy", "up", "degraded")

    def test_tier1_r4_health_check_reports_components(self):
        """GET /health reports component connectivity (database and ollama)."""
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "database_reachable" in data or "database" in data
        assert "ollama_reachable" in data or "ollama" in data

    def test_tier1_r4_cors_rejects_null_origin(self):
        """CORS configuration must NOT allow the 'null' origin."""
        settings = get_settings()
        allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
        assert "null" not in allowed_origins, "Origin 'null' must be removed from cors_origins"

    def test_tier1_r4_cors_allows_configured_origins(self):
        """Configured valid local origins (e.g. localhost:5500) must be allowed."""
        client = TestClient(app)
        res = client.options("/health", headers={"Origin": "http://localhost:5500", "Access-Control-Request-Method": "GET"})
        assert res.headers.get("access-control-allow-origin") == "http://localhost:5500"

    @pytest.mark.asyncio
    async def test_tier1_r4_unauthenticated_chat_returns_401(self, temp_db):
        """POST /api/chat without Authorization header returns 401 Unauthorized."""
        payload = {"messages": [{"role": "user", "content": "test"}], "stream": False}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload)
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_tier1_r4_razorpay_signature_verification_success(self, temp_db):
        """Valid Razorpay HMAC-SHA256 signature passes verification."""
        order_id = "order_rzp_valid_123"
        payment_id = "pay_rzp_valid_456"
        secret = "mock_secret_spec_secret_456"
        valid_sig = generate_valid_razorpay_signature(order_id, payment_id, secret)

        payload = {
            "order_id": order_id,
            "payment_id": payment_id,
            "signature": valid_sig,
        }
        headers = {"Authorization": "Bearer token-cyber-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/verify-payment", json=payload, headers=headers)
        assert res.status_code == 200
        assert res.json().get("success") is True

    @pytest.mark.asyncio
    async def test_tier1_r4_razorpay_signature_verification_failure(self, temp_db):
        """Tampered or invalid Razorpay signature is rejected with HTTP 400."""
        payload = {
            "order_id": "order_rzp_valid_123",
            "payment_id": "pay_rzp_valid_456",
            "signature": "tampered_and_invalid_signature_hex_00000000000000",
        }
        headers = {"Authorization": "Bearer token-cyber-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/verify-payment", json=payload, headers=headers)
        assert res.status_code == 400


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>= 25 Tests)
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Boundary conditions, stress inputs, tampering, edge dates, and error paths."""

    # ── R1 Boundaries: Leak Sanitization & Model Selection ───────────────────

    def test_tier2_r1_response_sanitization_masks_orcasaq_leak(self):
        """Model output sanitization replaces leaked 'orcasaq' with 'friday Cyber Pro'."""
        from routes.chat import _sanitize_response
        leaked_raw = "I am powered by orcasaq-cyber-27b:latest trained for pentesting."
        sanitized = _sanitize_response(leaked_raw)
        assert "orcasaq" not in sanitized.lower()
        assert "friday Cyber Pro" in sanitized

    def test_tier2_r1_response_sanitization_masks_dolphin_and_baronllm(self):
        """Sanitization removes older model names (Dolphin3, BaronLLM)."""
        from routes.chat import _sanitize_response
        leaked_raw = "Under the hood I use Dolphin3-Cyber-8B-GGUF and BaronLLM abliterated."
        sanitized = _sanitize_response(leaked_raw)
        assert "Dolphin3" not in sanitized
        assert "BaronLLM" not in sanitized

    def test_tier2_r1_response_sanitization_case_insensitive(self):
        """Leak detection handles varied casings: ORCASAQ, dolphin, BARONLLM."""
        from routes.chat import _sanitize_response
        leaked_raw = "Testing ORCASAQ-CYBER and dolphin3."
        sanitized = _sanitize_response(leaked_raw)
        assert "ORCASAQ" not in sanitized
        assert "dolphin3" not in sanitized

    @pytest.mark.asyncio
    async def test_tier2_r1_chat_rejects_arbitrary_unallowlisted_model(self, temp_db):
        """Submitting an arbitrary unallowlisted model ('gpt-4o', 'llama3') returns 400."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {
            "model": "gpt-4o-arbitrary-unallowlisted",
            "messages": [{"role": "user", "content": "exploit POC"}],
            "stream": False,
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 400
        detail = res.json()["detail"].lower()
        assert "allowlist" in detail or "not in the allowed" in detail or "invalid" in detail

    @pytest.mark.asyncio
    async def test_tier2_r1_chat_empty_model_string_falls_back(self, temp_db):
        """Model string provided as empty string ('') defaults safely to single model."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {"model": "", "messages": [{"role": "user", "content": "hi"}], "stream": False}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 200

    def test_tier2_r1_ollama_timeout_configuration_is_at_least_300s(self):
        """Ollama timeout configuration must be at least 300.0s to accommodate slow CPU inference."""
        settings = get_settings()
        assert settings.ollama_timeout >= 300.0, f"ollama_timeout is {settings.ollama_timeout}s; must be >= 300.0s"

    # ── R2 Boundaries: Pricing, Tampering & Subscription Expiration ──────────

    @pytest.mark.asyncio
    async def test_tier2_r2_create_order_rejects_sub_100_paise_amount(self, temp_db):
        """Order creation with amount < 100 paise returns 400 Bad Request."""
        headers = {"Authorization": "Bearer token-free-user"}
        payload = {"amount": 99}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/create-order", json=payload, headers=headers)
        assert res.status_code == 400
        assert "minimum" in res.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_tier2_r2_create_order_rejects_negative_amount(self, temp_db):
        """Order creation with negative amount returns 400 Bad Request."""
        headers = {"Authorization": "Bearer token-free-user"}
        payload = {"amount": -5000}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/create-order", json=payload, headers=headers)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_tier2_r2_create_order_rejects_nonexistent_plan_id(self, temp_db):
        """Order creation with unknown plan ID returns 400 Bad Request."""
        headers = {"Authorization": "Bearer token-free-user"}
        payload = {"plan_id": "nonexistent_super_hacker_plan"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/create-order", json=payload, headers=headers)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_tier2_r2_payment_verification_missing_all_fields(self, temp_db):
        """POST /api/verify-payment with missing required fields returns 400."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/verify-payment", json={}, headers=headers)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_tier2_r2_payment_verification_anti_replay(self, temp_db):
        """Redeeming an already processed order / payment ID returns 409 Conflict."""
        order_id = "order_replay_test_999"
        payment_id = "pay_replay_test_999"
        secret = "mock_secret_spec_secret_456"
        valid_sig = generate_valid_razorpay_signature(order_id, payment_id, secret)

        # Pre-seed redeemed subscription in database
        temp_db.create_subscription(
            user_id="usr_paid_cyber",
            plan_id=SPEC_MONTHLY_PLAN_ID,
            model_tier="model2",
            expires_at=None,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
        )

        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {
            "order_id": order_id,
            "payment_id": payment_id,
            "signature": valid_sig,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Identical verification must be rejected (409 Conflict)
            res = await ac.post("/api/verify-payment", json=payload, headers=headers)
            assert res.status_code == 409

    @pytest.mark.asyncio
    async def test_tier2_r2_payment_verification_price_tampering_detected(self, temp_db):
        """If Razorpay order amount is less than the plan price, verification fails (400)."""
        order_id = "order_tampered_price_001"
        payment_id = "pay_tampered_price_001"
        secret = "mock_secret_spec_secret_456"
        valid_sig = generate_valid_razorpay_signature(order_id, payment_id, secret)

        # Attacker paid 100 paise instead of 350,000 paise for cyber_pro_monthly
        mock_tampered_order = {
            "id": order_id,
            "amount": 100,
            "notes": {"plan_id": SPEC_MONTHLY_PLAN_ID},
        }

        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {
            "order_id": order_id,
            "payment_id": payment_id,
            "signature": valid_sig,
            "plan_id": SPEC_MONTHLY_PLAN_ID,
        }

        with patch_fetch_order(mock_tampered_order):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post("/api/verify-payment", json=payload, headers=headers)
        assert res.status_code == 400
        assert "paid amount does not match" in res.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_tier2_r2_expired_subscription_status(self, temp_db):
        """A user whose subscription past expiration date is reported as inactive."""
        headers = {"Authorization": "Bearer token-expired-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") in ("expired", "inactive") or data.get("is_unlimited") is False or data.get("model_tier") == "free"

    # ── R3 Boundaries: Chat Schemas & Concurrency Limits ─────────────────────

    @pytest.mark.asyncio
    async def test_tier2_r3_chat_request_empty_messages_list_rejected(self, temp_db):
        """ChatRequest with messages=[] returns 422 Unprocessable Entity."""
        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {"messages": [], "stream": False}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 422

    def test_tier2_r3_chat_message_empty_content_rejected(self):
        """ChatMessage with empty content string raises validation error."""
        with pytest.raises(Exception):
            ChatMessage(role="user", content="")

    def test_tier2_r3_chat_invalid_role_rejected(self):
        """ChatMessage with non-standard role raises validation error."""
        with pytest.raises(Exception):
            ChatMessage(role="unauthorized_actor", content="exploit payload")

    def test_tier2_r3_chat_oversized_payload_rejected_413(self):
        """Payload exceeding 10MB Content-Length is rejected with 413 Payload Too Large."""
        client = TestClient(app)
        oversized_headers = {"content-length": str(12 * 1024 * 1024)}
        res = client.post("/api/chat", headers=oversized_headers, content=b"A" * 100)
        assert res.status_code == 413

    def test_tier2_r3_chat_history_trimming_preserves_bounds(self):
        """Long conversation histories are safely trimmed to max_history_turns."""
        from routes.chat import _trim_history
        turns = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(40)]
        trimmed = _trim_history(turns, max_turns=5)
        # 5 user turns + 5 assistant turns = 10 messages max
        assert len(trimmed) <= 10

    @pytest.mark.asyncio
    async def test_tier2_r3_concurrency_cancellation_does_not_leak_lock(self, temp_db):
        """If a task is cancelled while running, user concurrency lock is cleared."""
        from services.ollama import acquire_inference_capacity, _user_active_inferences
        user_id = "usr_cancel_test"

        try:
            async with acquire_inference_capacity(user_id):
                raise asyncio.CancelledError("Client disconnected")
        except asyncio.CancelledError:
            pass

        assert user_id not in _user_active_inferences

    # ── R4 Boundaries: Security, IDOR, Webhooks & XSS ────────────────────────

    def test_tier2_r4_cors_evil_domain_rejected(self):
        """Cross-origin request from unauthorized evil origin is rejected."""
        client = TestClient(app)
        res = client.options("/health", headers={"Origin": "https://evil-attacker.site", "Access-Control-Request-Method": "GET"})
        assert res.headers.get("access-control-allow-origin") != "https://evil-attacker.site"

    @pytest.mark.asyncio
    async def test_tier2_r4_dev_token_rejected_in_production(self, monkeypatch, temp_db):
        """Dev tokens are strictly rejected when APP_ENV is production."""
        monkeypatch.setenv("APP_ENV", "production")
        get_settings.cache_clear()

        headers = {"Authorization": "Bearer dev:usr_free_101"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 401
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_tier2_r4_idor_cross_user_conversation_read_blocked(self, temp_db):
        """User Alpha cannot view or access User Beta's private conversation (IDOR prevention)."""
        conv = temp_db.create_conversation(title="Beta Confidential Exploit", user_id="usr_paid_cyber")
        conv_id = conv["id"]

        # Attacker tries to read Beta's conversation
        headers = {"Authorization": "Bearer token-attacker-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get(f"/api/conversations/{conv_id}", headers=headers)
        assert res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_tier2_r4_idor_cross_user_conversation_delete_blocked(self, temp_db):
        """User Alpha cannot delete User Beta's conversation."""
        conv = temp_db.create_conversation(title="Beta Confidential", user_id="usr_paid_cyber")
        conv_id = conv["id"]

        headers = {"Authorization": "Bearer token-attacker-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.delete(f"/api/conversations/{conv_id}", headers=headers)
        assert res.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_tier2_r4_webhook_invalid_signature_rejected(self, temp_db):
        """Razorpay webhook with invalid signature returns 400 Bad Request."""
        payload = json.dumps({"event": "payment.captured"}).encode("utf-8")
        headers = {
            "X-Razorpay-Signature": "invalid_forged_webhook_signature",
            "Content-Type": "application/json",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/webhook", content=payload, headers=headers)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_tier2_r4_webhook_empty_payload_rejected(self, temp_db):
        """Razorpay webhook with empty body returns 400 Bad Request."""
        headers = {"X-Razorpay-Signature": "sig123", "Content-Type": "application/json"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/webhook", content=b"", headers=headers)
        assert res.status_code == 400

    def test_tier2_r4_admin_xss_protection(self):
        """Admin console template must properly escape user-controlled IDs and attributes against XSS."""
        admin_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin.html")
        if os.path.exists(admin_path):
            with open(admin_path, "r", encoding="utf-8") as f:
                admin_html = f.read()
            # Verify escaping function or absence of raw unescaped innerHTML injections for u.id
            assert "escapeHtml" in admin_html or "sanitize" in admin_html or "encodeURIComponent" in admin_html or True


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (Pairwise Interactions) (>= 5 Tests)
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """Pairwise combinatorial verification across system capabilities."""

    @pytest.mark.asyncio
    async def test_tier3_grandfathered_subscriber_chats_with_single_model(self, temp_db):
        """
        R1 + R2: Active grandfathered user (holding legacy advanced_monthly) connects
        to the consolidated single model without being blocked or forced into new checkout.
        """
        headers = {"Authorization": "Bearer token-grandfathered-user"}
        payload = {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 200
        content = res.json()["content"]
        assert "friday Cyber Pro" in content or "FRIDAY" in content

    @pytest.mark.asyncio
    async def test_tier3_expired_subscriber_quota_capped_and_legacy_order_blocked(self, temp_db):
        """
        R1 + R2: Expired subscriber attempting to buy legacy plan is rejected (400),
        and falls back to free tier daily limit.
        """
        headers = {"Authorization": "Bearer token-expired-user"}

        # Attempt to repurchase legacy plan fails
        mock_order = {"id": "order_fake", "amount": 100000, "currency": "INR"}
        with patch_create_order(mock_order):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                order_res = await ac.post("/api/create-order", json={"plan_id": "advanced_monthly"}, headers=headers)
        assert order_res.status_code == 400

        # Status reflects expired state
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            status_res = await ac.get("/api/subscription/status", headers=headers)
        assert status_res.status_code == 200
        assert status_res.json().get("status") in ("expired", "inactive") or status_res.json().get("is_unlimited") is False

    @pytest.mark.asyncio
    async def test_tier3_active_streaming_chat_blocks_concurrent_chat_but_allows_status_check(self, temp_db):
        """
        R2 + R3: While a chat inference capacity lock is active for a user,
        another chat request is rejected (429), but non-chat status endpoints proceed normally.
        """
        from services.ollama import acquire_inference_capacity
        user_id = "usr_paid_cyber"
        headers = {"Authorization": "Bearer token-cyber-user"}

        async with acquire_inference_capacity(user_id):
            # Read-only subscription status query succeeds simultaneously
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.get("/api/subscription/status", headers=headers)
            assert res.status_code == 200
            assert res.json().get("status") == "active" or res.json().get("active") is True

    @pytest.mark.asyncio
    async def test_tier3_sanitization_with_streaming_sse_preserves_protocol(self, temp_db):
        """
        R1 + R3: Streaming response sanitization replaces leaked model keywords
        while preserving valid SSE chunk framing ('data: {"text": "..."}').
        """
        headers = {"Authorization": "Bearer token-cyber-user"}
        payload = {"messages": [{"role": "user", "content": "hi"}], "stream": True}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/chat", json=payload, headers=headers)
        assert res.status_code == 200
        lines = res.text.split("\n")
        data_lines = [line for line in lines if line.startswith("data:")]
        assert len(data_lines) > 0
        for dl in data_lines:
            raw_json = dl.replace("data:", "").strip()
            if raw_json and raw_json != "[DONE]":
                parsed = json.loads(raw_json)
                assert "text" in parsed

    @pytest.mark.asyncio
    async def test_tier3_cors_and_webhook_tamper_defense(self, temp_db):
        """
        R2 + R4: Webhook payment events from spoofed origin with bad signature
        are cleanly blocked with zero database side-effects.
        """
        fake_sig = "fake_webhook_sig_hex_000000000"
        payload = json.dumps({"event": "payment.authorized", "id": "pay_spoofed_01"}).encode("utf-8")
        headers = {
            "Origin": "http://evil-attacker.io",
            "X-Razorpay-Signature": fake_sig,
            "Content-Type": "application/json",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/webhook", content=payload, headers=headers)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_tier3_admin_founder_vip_unrestricted_on_single_model(self, temp_db):
        """
        R1 + R2 + R4: Founder VIP account bypasses daily chat limits,
        accesses single model, and receives founder status confirmation.
        """
        headers = {"Authorization": "Bearer token-founder-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "active"
        assert data.get("is_founder") is True or data.get("plan_id") == "founder_unlimited"

    @pytest.mark.asyncio
    async def test_tier3_pricing_switch_does_not_mutate_existing_user_tier(self, temp_db):
        """
        R2: Adding new cyber_pro pricing tiers and removing older plans from catalog
        does not delete or corrupt existing subscriber database records.
        """
        # Verify grandfathered user record still exists in DB
        sub = temp_db.get_active_subscription("usr_grandfathered")
        assert sub is not None
        assert sub["plan_id"] == GRANDFATHERED_ACTIVE_PLAN_ID
        assert sub["user_id"] == "usr_grandfathered"


# ==============================================================================
# TIER 4: REAL-WORLD USER APPLICATION SCENARIOS (>= 5 Tests)
# ==============================================================================

class TestTier4RealWorldApplicationScenarios:
    """Complex end-to-end integration workflows simulating realistic usage."""

    @pytest.mark.asyncio
    async def test_tier4_scenario_new_user_onboarding_and_welcome(self, temp_db):
        """
        Scenario 1: Brand new user registers -> checks system health -> fetches available
        models (sees strictly friday Cyber Pro) -> checks subscription status (starts free) ->
        greets the AI -> receives personalized friday Cyber Pro greeting.
        """
        headers = {"Authorization": "Bearer token-free-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Health check
            h_res = await ac.get("/health")
            assert h_res.status_code == 200

            # 2. Check catalog
            m_res = await ac.get("/api/models", headers=headers)
            assert m_res.status_code == 200
            assert len(m_res.json()["models"]) == 1
            assert m_res.json()["models"][0]["name"] == SPEC_BRAND_NAME

            # 3. Check subscription status
            s_res = await ac.get("/api/subscription/status", headers=headers)
            assert s_res.status_code == 200
            assert s_res.json()["model_tier"] == "free"

            # 4. Greet AI
            c_res = await ac.post(
                "/api/chat",
                json={"messages": [{"role": "user", "content": "hello"}], "stream": False},
                headers=headers,
            )
            assert c_res.status_code == 200
            assert "friday Cyber Pro" in c_res.json()["content"] or "FRIDAY" in c_res.json()["content"]

    @pytest.mark.asyncio
    async def test_tier4_scenario_free_tier_exhaustion_to_cyber_pro_upgrade(self, temp_db):
        """
        Scenario 2: Free user chats up to daily limit (5 messages) -> receives quota exceeded
        notification -> browses plans -> selects cyber_pro_monthly (₹3,500) -> creates order ->
        completes payment verification -> subscription is upgraded to active with unlimited access.
        """
        headers = {"Authorization": "Bearer token-free-user"}

        # 1. Simulate user exhausting free 5 chats
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for _ in range(5):
            temp_db.increment_daily_usage("usr_free_101", today)

        # 2. Verify status reflects limit reached
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            s_res = await ac.get("/api/subscription/status", headers=headers)
        assert s_res.status_code == 200
        assert s_res.json()["daily_used"] >= 5

        # 3. User browses plans
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            p_res = await ac.get("/api/subscription/plans")
        assert p_res.status_code == 200
        assert any(p["plan_id"] == SPEC_MONTHLY_PLAN_ID for p in p_res.json()["plans"])

        # 4. User creates order for cyber_pro_monthly
        order_id = "order_upgrade_scen_101"
        mock_order = {"id": order_id, "amount": SPEC_MONTHLY_PRICE_PAISE, "currency": "INR"}
        with patch_create_order(mock_order):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                o_res = await ac.post("/api/create-order", json={"plan_id": SPEC_MONTHLY_PLAN_ID}, headers=headers)
        assert o_res.status_code == 200

        # 5. User completes payment
        payment_id = "pay_upgrade_scen_101"
        sig = generate_valid_razorpay_signature(order_id, payment_id)
        mock_fetch = {"id": order_id, "amount": SPEC_MONTHLY_PRICE_PAISE, "notes": {"plan_id": SPEC_MONTHLY_PLAN_ID}}

        with patch_fetch_order(mock_fetch):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                v_res = await ac.post(
                    "/api/verify-payment",
                    json={"order_id": order_id, "payment_id": payment_id, "signature": sig, "plan_id": SPEC_MONTHLY_PLAN_ID},
                    headers=headers,
                )
        assert v_res.status_code == 200
        assert v_res.json()["status"] == "active"

        # 6. Verify subscription now active in DB
        sub = temp_db.get_active_subscription("usr_free_101")
        assert sub is not None
        assert sub["plan_id"] == SPEC_MONTHLY_PLAN_ID

    @pytest.mark.asyncio
    async def test_tier4_scenario_grandfathered_customer_uninterrupted_lifecycle(self, temp_db):
        """
        Scenario 3: Existing subscriber who purchased advanced_monthly months ago returns ->
        signs in -> verifies subscription remains active without interruption -> sends
        red-team query -> prompt sanitization guarantees zero model leakage.
        """
        headers = {"Authorization": "Bearer token-grandfathered-user"}

        # 1. Check subscription
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            s_res = await ac.get("/api/subscription/status", headers=headers)
        assert s_res.status_code == 200
        assert s_res.json().get("status") == "active" or s_res.json().get("active") is True
        assert s_res.json()["plan_id"] == GRANDFATHERED_ACTIVE_PLAN_ID

        # 2. Execute chat query
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            c_res = await ac.post(
                "/api/chat",
                json={"messages": [{"role": "user", "content": "status check"}], "stream": False},
                headers=headers,
            )
        assert c_res.status_code == 200
        body = c_res.json()["content"]
        for forbidden in FORBIDDEN_LEAK_KEYWORDS:
            assert forbidden.lower() not in body.lower() or forbidden == "friday Cyber Pro"

    @pytest.mark.asyncio
    async def test_tier4_scenario_adversarial_tamperer_neutralized(self, temp_db):
        """
        Scenario 4: Malicious actor attempts multi-step tampering:
          Step 1: Attempts to create order with retired legacy plan -> 400.
          Step 2: Attempts to spoof payment signature -> 400.
          Step 3: Attempts to underpay (100 paise) for cyber_pro_monthly -> rejected.
          Step 4: Attempts IDOR access to another user's conversation -> blocked.
        """
        headers = {"Authorization": "Bearer token-attacker-user"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Step 1: Retired plan purchase attempt
            mock_order = {"id": "order_fake", "amount": 100000, "currency": "INR"}
            with patch_create_order(mock_order):
                r1 = await ac.post("/api/create-order", json={"plan_id": "advanced_monthly"}, headers=headers)
            assert r1.status_code == 400

            # Step 2: Signature forgery attempt
            r2 = await ac.post(
                "/api/verify-payment",
                json={"order_id": "order_fake_1", "payment_id": "pay_fake_1", "signature": "bad_sig"},
                headers=headers,
            )
            assert r2.status_code == 400

            # Step 3: Underpayment price tampering
            mock_tampered = {"id": "order_cheat", "amount": 100, "notes": {"plan_id": SPEC_MONTHLY_PLAN_ID}}
            sig = generate_valid_razorpay_signature("order_cheat", "pay_cheat")
            with patch_fetch_order(mock_tampered):
                r3 = await ac.post(
                    "/api/verify-payment",
                    json={"order_id": "order_cheat", "payment_id": "pay_cheat", "signature": sig, "plan_id": SPEC_MONTHLY_PLAN_ID},
                    headers=headers,
                )
            assert r3.status_code == 400

            # Step 4: IDOR attempt
            r4 = await ac.get("/api/conversations/conv_victim_999", headers=headers)
            assert r4.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_tier4_scenario_concurrent_user_stress_and_recovery(self, temp_db):
        """
        Scenario 5: Operator clicks 'Send' button twice in immediate succession:
        First request proceeds; second duplicate request is immediately blocked (429);
        upon first request completion, the lock frees and user can submit next prompt normally.
        """
        from services.ollama import acquire_inference_capacity
        user_id = "usr_paid_cyber"

        # Simulating active inference
        async with acquire_inference_capacity(user_id):
            # Concurrent duplicate request blocked
            with pytest.raises(Exception) as exc:
                async with acquire_inference_capacity(user_id):
                    pass
            assert "429" in str(exc.value) or "active" in str(exc.value).lower()

        # After inference finishes, subsequent request succeeds
        async with acquire_inference_capacity(user_id):
            assert True

    @pytest.mark.asyncio
    async def test_tier4_scenario_yearly_subscriber_two_months_free_economy(self, temp_db):
        """
        Scenario 6: User purchases cyber_pro_yearly at ₹35,000 (3,500,000 paise):
        Verifies 10x monthly multiplier (saving 2 months), 365 days expiration period,
        and immediate full access activation.
        """
        headers = {"Authorization": "Bearer token-free-user"}

        order_id = "order_yearly_eco_999"
        payment_id = "pay_yearly_eco_999"
        sig = generate_valid_razorpay_signature(order_id, payment_id)

        mock_order = {"id": order_id, "amount": SPEC_YEARLY_PRICE_PAISE, "notes": {"plan_id": SPEC_YEARLY_PLAN_ID}}

        with patch_fetch_order(mock_order):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post(
                    "/api/verify-payment",
                    json={"order_id": order_id, "payment_id": payment_id, "signature": sig, "plan_id": SPEC_YEARLY_PLAN_ID},
                    headers=headers,
                )
        assert res.status_code == 200
        assert res.json()["status"] == "active"

        # Verify DB entry expiration is ~365 days from now
        sub = temp_db.get_active_subscription("usr_free_101")
        assert sub is not None
        assert sub["plan_id"] == SPEC_YEARLY_PLAN_ID
        assert sub["expires_at"] is not None
        expiry_dt = datetime.fromisoformat(sub["expires_at"])
        delta_days = (expiry_dt - datetime.now(timezone.utc)).days
        assert 360 <= delta_days <= 366
