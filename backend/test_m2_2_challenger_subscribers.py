"""
Adversarial Stress Test Suite for Milestone 2 — Challenger M2-2
Focus: Existing Subscriber Preservation, Grandfathered Access Integrity, Expiration Boundaries, and Founder VIP Access.
"""

import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from config import get_settings
from services.subscription import (
    PLAN_CONFIG,
    FREE_DAILY_LIMIT,
    MODEL1_DAILY_LIMIT,
    MODEL_1_ID,
    MODEL_2_ID,
    is_admin_or_founder,
    get_user_model_tier,
    get_subscription_status,
    check_and_increment_usage,
    check_and_increment_model1_usage,
    track_usage,
)
from services.auth import set_mock_token_verifier


# ─── Isolated Database Fixture ────────────────────────────────────────────────

@pytest.fixture
def challenger_db(tmp_path, monkeypatch):
    """Isolated SQLite database for Challenger M2-2 test executions."""
    db_file = str(tmp_path / "challenger_m2_2.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_challenger_m2_2")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "mock_secret_challenger_m2_2")
    get_settings.cache_clear()

    import importlib
    import services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()

    # Pre-seed diverse test operators
    # 1. Free operator
    db_mod.create_user(
        email="free_op@test.sec",
        name="Free Operator",
        user_id="usr_free_op",
        provider="google",
    )

    # 2. Grandfathered Advanced Pentester Monthly (model2, unlimited)
    db_mod.create_user(
        email="legacy_adv_m@test.sec",
        name="Legacy Advanced Monthly User",
        user_id="usr_legacy_adv_m",
        provider="google",
    )
    future_30d = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    db_mod.create_subscription("usr_legacy_adv_m", "advanced_monthly", "model2", future_30d)

    # 3. Grandfathered Advanced Pentester Yearly (model2, unlimited)
    db_mod.create_user(
        email="legacy_adv_y@test.sec",
        name="Legacy Advanced Yearly User",
        user_id="usr_legacy_adv_y",
        provider="google",
    )
    future_300d = (datetime.now(timezone.utc) + timedelta(days=300)).isoformat()
    db_mod.create_subscription("usr_legacy_adv_y", "advanced_yearly", "model2", future_300d)

    # 4. Grandfathered Jr Hacker Monthly (model1, 50 chats/day)
    db_mod.create_user(
        email="legacy_jr_m@test.sec",
        name="Legacy Jr Hacker Monthly User",
        user_id="usr_legacy_jr_m",
        provider="google",
    )
    db_mod.create_subscription("usr_legacy_jr_m", "jr_hacker_monthly", "model1", future_30d)

    # 5. Grandfathered Jr Hacker Yearly (model1, 50 chats/day)
    db_mod.create_user(
        email="legacy_jr_y@test.sec",
        name="Legacy Jr Hacker Yearly User",
        user_id="usr_legacy_jr_y",
        provider="google",
    )
    db_mod.create_subscription("usr_legacy_jr_y", "jr_hacker_yearly", "model1", future_300d)

    # 6. Expired Advanced Monthly user (expired 1 hour ago)
    db_mod.create_user(
        email="expired_1h@test.sec",
        name="Expired Operator 1h",
        user_id="usr_expired_1h",
        provider="google",
    )
    past_1h = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db_mod.create_subscription("usr_expired_1h", "advanced_monthly", "model2", past_1h)

    # 7. Expired Jr Hacker user (expired 30 days ago)
    db_mod.create_user(
        email="expired_30d@test.sec",
        name="Expired Operator 30d",
        user_id="usr_expired_30d",
        provider="google",
    )
    past_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    db_mod.create_subscription("usr_expired_30d", "jr_hacker_monthly", "model1", past_30d)

    # 8. Boundary Expired user (expired 1 second ago)
    db_mod.create_user(
        email="expired_1s@test.sec",
        name="Expired Operator 1s",
        user_id="usr_expired_1s",
        provider="google",
    )
    past_1s = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    db_mod.create_subscription("usr_expired_1s", "advanced_monthly", "model2", past_1s)

    # 9. Boundary Active user (expires in 5 seconds)
    db_mod.create_user(
        email="active_5s@test.sec",
        name="Active Operator 5s",
        user_id="usr_active_5s",
        provider="google",
    )
    future_5s = (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()
    db_mod.create_subscription("usr_active_5s", "advanced_monthly", "model2", future_5s)

    # 10. Founder VIP user by UID
    db_mod.create_user(
        email="sharonanil555@gmail.com",
        name="Sharon Anil",
        user_id="ih5zm1zzusd3gwZLF69fYKWA14d2",
        provider="google",
    )

    # 11. Founder VIP user by Email (alternate UID)
    db_mod.create_user(
        email="sharon@hackwsharon.com",
        name="Founder Sharon Sec",
        user_id="usr_founder_email_match",
        provider="google",
    )

    yield db_mod
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def setup_mock_auth_tokens():
    """Mock authentication token mapping for challenger tests."""
    token_map = {
        "token-free-op": {
            "uid": "usr_free_op", "email": "free_op@test.sec", "name": "Free Operator", "email_verified": True
        },
        "token-legacy-adv-m": {
            "uid": "usr_legacy_adv_m", "email": "legacy_adv_m@test.sec", "name": "Legacy Advanced Monthly User", "email_verified": True
        },
        "token-legacy-adv-y": {
            "uid": "usr_legacy_adv_y", "email": "legacy_adv_y@test.sec", "name": "Legacy Advanced Yearly User", "email_verified": True
        },
        "token-legacy-jr-m": {
            "uid": "usr_legacy_jr_m", "email": "legacy_jr_m@test.sec", "name": "Legacy Jr Hacker Monthly User", "email_verified": True
        },
        "token-legacy-jr-y": {
            "uid": "usr_legacy_jr_y", "email": "legacy_jr_y@test.sec", "name": "Legacy Jr Hacker Yearly User", "email_verified": True
        },
        "token-expired-1h": {
            "uid": "usr_expired_1h", "email": "expired_1h@test.sec", "name": "Expired Operator 1h", "email_verified": True
        },
        "token-expired-30d": {
            "uid": "usr_expired_30d", "email": "expired_30d@test.sec", "name": "Expired Operator 30d", "email_verified": True
        },
        "token-expired-1s": {
            "uid": "usr_expired_1s", "email": "expired_1s@test.sec", "name": "Expired Operator 1s", "email_verified": True
        },
        "token-active-5s": {
            "uid": "usr_active_5s", "email": "active_5s@test.sec", "name": "Active Operator 5s", "email_verified": True
        },
        "token-founder-uid": {
            "uid": "ih5zm1zzusd3gwZLF69fYKWA14d2", "email": "sharonanil555@gmail.com", "name": "Sharon Anil", "email_verified": True
        },
        "token-founder-email": {
            "uid": "usr_founder_email_match", "email": "sharon@hackwsharon.com", "name": "Founder Sharon Sec", "email_verified": True
        },
    }

    def mock_verifier(token: str):
        return token_map.get(token)

    set_mock_token_verifier(mock_verifier)
    yield
    set_mock_token_verifier(None)


@pytest.fixture(autouse=True)
def mock_ollama_inference():
    """Mock backend Ollama calls for offline unit test consistency."""
    with patch("routes.chat.chat_complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = "Simulated defensive exploit audit report."
        yield mock_complete


# ==============================================================================
# SECTION 1: ACTIVE GRANDFATHERED SUBSCRIBER PRESERVATION & ACCESS INTEGRITY
# ==============================================================================

class TestGrandfatheredSubscriberIntegrity:
    """Stress-test existing legacy subscribers on retired plans."""

    @pytest.mark.asyncio
    async def test_legacy_advanced_monthly_status_and_unlimited_access(self, challenger_db):
        """Active advanced_monthly subscriber retains full unlimited model2 access."""
        headers = {"Authorization": "Bearer token-legacy-adv-m"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "active"
        assert data["plan_id"] == "advanced_monthly"
        assert data["model_tier"] == "model2"
        assert data["is_unlimited"] is True
        assert data["daily_limit"] is None
        assert data["chats_remaining"] is None

        # Verify chat endpoint accepts requests without throttling
        for i in range(15):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                c_res = await ac.post(
                    "/api/chat",
                    headers=headers,
                    json={"messages": [{"role": "user", "content": f"vector audit {i}"}], "stream": False},
                )
            assert c_res.status_code == 200

    @pytest.mark.asyncio
    async def test_legacy_advanced_yearly_status_and_unlimited_access(self, challenger_db):
        """Active advanced_yearly subscriber retains full unlimited model2 access."""
        headers = {"Authorization": "Bearer token-legacy-adv-y"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "active"
        assert data["plan_id"] == "advanced_yearly"
        assert data["model_tier"] == "model2"
        assert data["is_unlimited"] is True
        assert data["daily_limit"] is None

    @pytest.mark.asyncio
    async def test_legacy_jr_hacker_monthly_50_chat_quota_enforcement(self, challenger_db):
        """
        Jr Hacker subscribers must get 50 chats/day (not free tier 5),
        and strictly hit HTTP 429 upon exhausting chat #50.
        """
        headers = {"Authorization": "Bearer token-legacy-jr-m"}
        user_id = "usr_legacy_jr_m"

        # Check status before chats
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "active"
        assert data["plan_id"] == "jr_hacker_monthly"
        assert data["model_tier"] == "model1"
        assert data["daily_limit"] == 50
        assert data["is_unlimited"] is False

        # Simulate 5 chats (free limit): Jr Hacker user MUST NOT be throttled at 5!
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for _ in range(5):
            challenger_db.increment_daily_usage(user_id, today)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            c_res = await ac.post(
                "/api/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "chat number 6"}], "stream": False},
            )
        assert c_res.status_code == 200, "Jr Hacker subscriber was prematurely throttled at 5 chats!"

        # Now increment to exactly 50
        challenger_db.increment_daily_usage(user_id, today)  # 7
        for _ in range(43):  # total = 50
            challenger_db.increment_daily_usage(user_id, today)

        # 51st chat must return HTTP 429
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            c_res_429 = await ac.post(
                "/api/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "chat number 51"}], "stream": False},
            )
        assert c_res_429.status_code == 429
        err = c_res_429.json()["detail"]
        assert err["error"] == "daily_limit_reached"
        assert err["daily_limit"] == 50

    @pytest.mark.asyncio
    async def test_legacy_jr_hacker_blocked_from_model2_with_403(self, challenger_db):
        """
        Jr Hacker (model1) attempting to access MODEL_2_ID receives 403 Forbidden
        with upgrade_required = True.
        """
        headers = {"Authorization": "Bearer token-legacy-jr-m"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "exploit generation"}], "model": MODEL_2_ID, "stream": False},
            )
        assert res.status_code == 403
        detail = res.json()["detail"]
        assert detail["error"] == "model_access_denied"
        assert detail["upgrade_required"] is True
        assert detail["required_tier"] == "model2"

    @pytest.mark.asyncio
    async def test_legacy_advanced_monthly_allowed_on_model2(self, challenger_db):
        """Advanced Pentester (model2) subscriber can access MODEL_2_ID without 403."""
        headers = {"Authorization": "Bearer token-legacy-adv-m"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "exploit generation"}], "model": MODEL_2_ID, "stream": False},
            )
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_legacy_subscriber_retains_access_across_catalog_changes(self, challenger_db):
        """
        Even when catalog lists only cyber_pro tiers, legacy subscriber's active record
        remains completely unmutated and protected in DB.
        """
        sub_before = challenger_db.get_active_subscription("usr_legacy_adv_m")
        assert sub_before is not None
        assert sub_before["plan_id"] == "advanced_monthly"
        assert sub_before["status"] == "active"

        # Catalog query
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            cat_res = await ac.get("/api/subscription/plans")
        assert cat_res.status_code == 200

        sub_after = challenger_db.get_active_subscription("usr_legacy_adv_m")
        assert sub_after["id"] == sub_before["id"]
        assert sub_after["plan_id"] == sub_before["plan_id"]
        assert sub_after["expires_at"] == sub_before["expires_at"]


# ==============================================================================
# SECTION 2: EXPIRATION BOUNDARIES & CLEAN TRANSITION TO FREE TIER
# ==============================================================================

class TestExpirationBoundariesAndTransitions:
    """Stress-test expiration precision, sub-second boundaries, and fallback behavior."""

    @pytest.mark.asyncio
    async def test_expired_1h_cleanly_transitions_to_free_tier(self, challenger_db):
        """User whose plan expired 1 hour ago smoothly falls back to Free tier."""
        headers = {"Authorization": "Bearer token-expired-1h"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["plan_id"] == "free"
        assert data["model_tier"] == "free"
        assert data["daily_limit"] == 5
        assert data["is_unlimited"] is False

    @pytest.mark.asyncio
    async def test_expired_1s_boundary_falls_back_to_free_tier(self, challenger_db):
        """User whose plan expired 1 second ago immediately transitions to Free tier."""
        headers = {"Authorization": "Bearer token-expired-1s"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["plan_id"] == "free"
        assert data["model_tier"] == "free"
        assert data["daily_limit"] == 5

    @pytest.mark.asyncio
    async def test_active_5s_boundary_remains_active_until_elapsed(self, challenger_db):
        """User whose plan expires in 5 seconds is recognized as active right now."""
        headers = {"Authorization": "Bearer token-active-5s"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "active"
        assert data["plan_id"] == "advanced_monthly"
        assert data["is_unlimited"] is True

    @pytest.mark.asyncio
    async def test_expired_user_hits_free_quota_and_blocked_from_legacy_purchase(self, challenger_db):
        """
        Expired user exhausts 5 free chats -> gets 429 -> attempts to repurchase
        retired plan -> rejected with HTTP 400 Bad Request.
        """
        headers = {"Authorization": "Bearer token-expired-30d"}
        user_id = "usr_expired_30d"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Exhaust 5 free chats
        for _ in range(5):
            challenger_db.increment_daily_usage(user_id, today)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            c_res = await ac.post(
                "/api/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "chat over limit"}], "stream": False},
            )
        assert c_res.status_code == 429
        assert c_res.json()["detail"]["error"] == "daily_limit_reached"

        # Attempt to repurchase legacy plan fails with 400
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            order_res = await ac.post(
                "/api/create-order",
                headers=headers,
                json={"plan_id": "jr_hacker_monthly"},
            )
        assert order_res.status_code == 400
        assert "retired or no longer offered" in order_res.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_expired_user_can_upgrade_to_cyber_pro_monthly(self, challenger_db):
        """Expired user can successfully order the new active cyber_pro_monthly tier."""
        headers = {"Authorization": "Bearer token-expired-30d"}
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            "id": "order_upgrade_cyber_pro_999",
            "amount": 350000,
            "currency": "INR",
            "receipt": "rcpt_upgrade_01",
        }
        with patch("services.subscription._get_razorpay_client", return_value=mock_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post(
                    "/api/create-order",
                    headers=headers,
                    json={"plan_id": "cyber_pro_monthly"},
                )
        assert res.status_code == 200
        assert res.json()["order_id"] == "order_upgrade_cyber_pro_999"
        assert res.json()["amount"] == 350000


# ==============================================================================
# SECTION 3: FOUNDER VIP PERMANENT ZERO-THROTTLING ACCESS
# ==============================================================================

class TestFounderVIPZeroThrottling:
    """Stress-test VIP founder accounts across UIDs, emails, and limit bypasses."""

    @pytest.mark.asyncio
    async def test_founder_uid_unlimited_status_and_no_expiry(self, challenger_db):
        """Founder by UID receives lifetime VIP status with no expiration date."""
        headers = {"Authorization": "Bearer token-founder-uid"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["plan_id"] == "founder_unlimited"
        assert data["model_tier"] == "model2"
        assert data["status"] == "active"
        assert data["expires_at"] is None
        assert data["daily_limit"] is None
        assert data["is_unlimited"] is True

    @pytest.mark.asyncio
    async def test_founder_email_match_resolves_and_caches_founder_status(self, challenger_db):
        """Founder verified by email receives founder VIP status."""
        headers = {"Authorization": "Bearer token-founder-email"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["plan_id"] == "founder_unlimited"
        assert data["model_tier"] == "model2"
        assert data["is_unlimited"] is True

    @pytest.mark.asyncio
    async def test_founder_immune_to_daily_usage_exhaustion(self, challenger_db):
        """
        Founder can perform dozens of chats beyond 5 (free) and 50 (jr_hacker),
        never encountering HTTP 429.
        """
        headers = {"Authorization": "Bearer token-founder-uid"}
        user_id = "ih5zm1zzusd3gwZLF69fYKWA14d2"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Artificially set usage count to 150 chats in DB
        for _ in range(150):
            challenger_db.increment_daily_usage(user_id, today)

        # Chat endpoint must STILL succeed without 429
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            c_res = await ac.post(
                "/api/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "deep network audit"}], "stream": False},
            )
        assert c_res.status_code == 200

    @pytest.mark.asyncio
    async def test_founder_immune_to_cancelled_or_expired_subscription_records(self, challenger_db):
        """
        Even if an expired or cancelled subscription record exists in DB for a founder,
        founder exemption strictly overrides DB records and preserves VIP access.
        """
        founder_uid = "ih5zm1zzusd3gwZLF69fYKWA14d2"
        past_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        challenger_db.create_subscription(founder_uid, "free", "free", past_date)

        # Verify model tier and status
        tier = get_user_model_tier(founder_uid)
        assert tier == "model2", "Founder model tier fell below model2!"

        headers = {"Authorization": "Bearer token-founder-uid"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/subscription/status", headers=headers)
        assert res.status_code == 200
        assert res.json()["plan_id"] == "founder_unlimited"
        assert res.json()["is_unlimited"] is True


# ==============================================================================
# SECTION 4: CORRUPTED RECORDS & ADMIN INTERACTION STRESS TESTS
# ==============================================================================

class TestEdgeCasesAndAdminInteractions:
    """Stress-test malformed DB records, admin grant/revoke, and multi-sub resolution."""

    @pytest.mark.asyncio
    async def test_unknown_plan_id_in_db_handles_gracefully_without_crash(self, challenger_db):
        """
        If a user has an active subscription with a completely unknown/corrupted plan_id,
        status endpoint handles gracefully without crashing with 500.
        """
        corrupted_uid = "usr_corrupted_plan"
        challenger_db.create_user("corrupted@test.sec", "Corrupted User", user_id=corrupted_uid)
        future_date = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
        challenger_db.create_subscription(corrupted_uid, "archived_unknown_tier_v0", "model2", future_date)

        status_data = get_subscription_status(corrupted_uid)
        assert status_data is not None
        assert status_data["status"] == "active"
        assert status_data["plan_id"] == "archived_unknown_tier_v0"

    @pytest.mark.asyncio
    async def test_admin_grant_and_revoke_lifecycle(self, challenger_db):
        """Admin grants cyber_pro_monthly to expired user, then revokes to free cleanly."""
        admin_headers = {"Authorization": "Bearer token-founder-uid"}
        user_headers = {"Authorization": "Bearer token-expired-1h"}

        # 1. Admin grants cyber_pro_monthly
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            grant_res = await ac.post(
                "/api/admin/grant-subscription",
                headers=admin_headers,
                json={"user_email_or_id": "expired_1h@test.sec", "plan_id": "cyber_pro_monthly", "days": 30},
            )
        assert grant_res.status_code == 200
        assert grant_res.json()["status"] == "success"

        # Verify user is now active cyber_pro_monthly
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            u_res = await ac.get("/api/subscription/status", headers=user_headers)
        assert u_res.status_code == 200
        assert u_res.json()["plan_id"] == "cyber_pro_monthly"
        assert u_res.json()["is_unlimited"] is True

        # 2. Admin revokes subscription
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            revoke_res = await ac.post(
                "/api/admin/revoke-subscription",
                headers=admin_headers,
                json={"user_email_or_id": "expired_1h@test.sec"},
            )
        assert revoke_res.status_code == 200

        # Verify user is back to Free
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            rev_res = await ac.get("/api/subscription/status", headers=user_headers)
        assert rev_res.status_code == 200
        assert rev_res.json()["plan_id"] == "free"
        assert rev_res.json()["daily_limit"] == 5

    @pytest.mark.asyncio
    async def test_daily_usage_rollover_resets_chat_limit(self, challenger_db):
        """Usage from a previous date does not count against today's limit."""
        user_id = "usr_free_op"
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Free user used 5 chats yesterday
        for _ in range(5):
            challenger_db.increment_daily_usage(user_id, yesterday)

        headers = {"Authorization": "Bearer token-free-op"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            s_res = await ac.get("/api/subscription/status", headers=headers)
        assert s_res.status_code == 200
        assert s_res.json()["daily_used"] == 0, "Yesterday's chats leaked into today's window!"
        assert s_res.json()["chats_remaining"] == 5

        # Today's first chat succeeds
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            c_res = await ac.post(
                "/api/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "today chat"}], "stream": False},
            )
        assert c_res.status_code == 200
