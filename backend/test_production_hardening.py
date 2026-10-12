"""
Production Hardening & Reliability Test Suite for FRIDAY AI
Validates OWASP controls, concurrency governor, IDOR authorization protections,
payload limits, security headers, and dual-signal health check.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from schemas import ChatMessage, ChatRequest
from config import get_settings
from services.ollama import acquire_inference_capacity

client = TestClient(app)

MOCK_USER_A = {"uid": "user_alpha_123", "email": "alpha@example.com", "name": "Alpha"}
MOCK_USER_B = {"uid": "user_bravo_456", "email": "bravo@example.com", "name": "Bravo"}


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Provide a fresh isolated SQLite DB for tests."""
    db_file = str(tmp_path / "test_hardening.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    import importlib, services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    yield db_mod
    get_settings.cache_clear()


def test_security_headers_and_request_id():
    """Verify OWASP recommended security headers and X-Request-ID telemetry."""
    res = client.get("/health")
    assert res.status_code == 200
    headers = res.headers
    assert "x-request-id" in headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "x-response-time" in headers


def test_payload_size_limit_413():
    """Verify payloads exceeding 10MB are rejected with 413 Payload Too Large."""
    huge_headers = {"content-length": str(12 * 1024 * 1024)}
    res = client.post("/api/chat", headers=huge_headers, content=b"x" * 100)
    assert res.status_code == 413
    assert "Payload too large" in res.json()["detail"]


def test_input_validation_schema_bounds():
    """Verify input validation rejecting oversized message turns or contents."""
    # Oversized content > 64KB
    huge_text = "A" * 70000
    with pytest.raises(Exception):
        ChatMessage(role="user", content=huge_text)

    # Oversized turn history > 100 turns
    too_many_messages = [ChatMessage(role="user", content=f"msg {i}") for i in range(105)]
    with pytest.raises(Exception):
        ChatRequest(messages=too_many_messages)


def test_dual_signal_health_endpoint():
    """Verify health endpoint reports both database and ollama reachability."""
    with patch("services.ollama.check_ollama_reachable", return_value=True), \
         patch("services.db.check_db_reachable", return_value=True):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["database_reachable"] is True
        assert data["ollama_reachable"] is True


def test_idor_cross_user_isolation(temp_db):
    """Verify strict user ownership prevents cross-user conversation access."""
    # Create accounts for both users
    temp_db.create_user(email=MOCK_USER_A["email"], name=MOCK_USER_A["name"], user_id=MOCK_USER_A["uid"])
    temp_db.create_user(email=MOCK_USER_B["email"], name=MOCK_USER_B["name"], user_id=MOCK_USER_B["uid"])

    # Create conversation as User A
    conv = temp_db.create_conversation(title="Secret Ops", user_id=MOCK_USER_A["uid"])
    conv_id = conv["id"]
    temp_db.append_message(conv_id, "user", "Alpha confidential data")

    # Verify User A can fetch it
    conv_a = temp_db.get_conversation(conv_id, user_id=MOCK_USER_A["uid"])
    assert conv_a is not None
    assert conv_a["title"] == "Secret Ops"

    # User B attempting to read User A's conversation must receive None (IDOR blocked)
    conv_b = temp_db.get_conversation(conv_id, user_id=MOCK_USER_B["uid"])
    assert conv_b is None

    # User B attempting to rename User A's conversation must fail
    renamed = temp_db.update_conversation_title(conv_id, "Hacked by B", user_id=MOCK_USER_B["uid"])
    assert renamed is False
    assert temp_db.get_conversation(conv_id, user_id=MOCK_USER_A["uid"])["title"] == "Secret Ops"

    # User B attempting to delete User A's conversation must fail
    deleted = temp_db.delete_conversation(conv_id, user_id=MOCK_USER_B["uid"])
    assert deleted is False
    assert temp_db.get_conversation(conv_id, user_id=MOCK_USER_A["uid"]) is not None

    # Clean up with User A
    cleanup = temp_db.delete_conversation(conv_id, user_id=MOCK_USER_A["uid"])
    assert cleanup is True


@pytest.mark.asyncio
async def test_concurrency_governor_user_double_submit_lock():
    """Verify concurrency governor rejects simultaneous active requests for same user with 429."""
    from fastapi import HTTPException
    user_id = "test_user_concurrent"

    async with acquire_inference_capacity(user_id):
        # Attempting second concurrent inference within same user context must raise 429
        with pytest.raises(HTTPException) as exc_info:
            async with acquire_inference_capacity(user_id):
                pass
        assert exc_info.value.status_code == 429
        assert "active generation in progress" in exc_info.value.detail


@pytest.mark.asyncio
async def test_concurrency_governor_global_backpressure(monkeypatch):
    """Verify capacity governor rejects excess requests with 503 and Retry-After header."""
    import asyncio
    from fastapi import HTTPException
    import services.ollama as ollama_service

    monkeypatch.setenv("MAX_CONCURRENT_INFERENCES", "1")
    monkeypatch.setenv("MAX_INFERENCE_QUEUE", "1")
    get_settings.cache_clear()
    ollama_service._inference_semaphore = asyncio.Semaphore(1)

    event_holder_started = asyncio.Event()
    event_release_holder = asyncio.Event()

    async def permit_holder():
        async with acquire_inference_capacity("holder_user"):
            event_holder_started.set()
            await event_release_holder.wait()

    async def waiter():
        async with acquire_inference_capacity("waiting_user"):
            pass

    holder_task = asyncio.create_task(permit_holder())
    await event_holder_started.wait()

    # holder_user now holds the only permit.
    # Start waiting_user which will increment waiting_count to 1 and wait for semaphore
    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.05)

    try:
        # Third user attempts to acquire capacity when waiting_count (1) >= max_inference_queue (1)
        with pytest.raises(HTTPException) as exc_info:
            async with acquire_inference_capacity("third_user"):
                pass
        assert exc_info.value.status_code == 503
        assert exc_info.value.headers.get("Retry-After") == "5"
    finally:
        event_release_holder.set()
        await holder_task
        await waiter_task
        ollama_service._inference_semaphore = None
        get_settings.cache_clear()
