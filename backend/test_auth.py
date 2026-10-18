"""
Tests for FRIDAY AI Firebase Authentication & Protected Routes
Validates:
  1. GET /health remains publicly accessible without authentication
  2. POST /api/chat without Authorization header returns 401 Unauthorized
  3. POST /api/chat with malformed / invalid / expired token returns 401 Unauthorized
  4. POST /api/chat with valid Firebase ID token passes to chat pipeline and persists under Firebase UID
  5. GET/POST /api/conversations requires valid Firebase ID token (401 when missing/invalid)
  6. Multi-user history isolation: User A cannot see or access User B's conversations
  7. Token verification and profile retrieval endpoints (/api/auth/me, /api/auth/verify)
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from services.auth import set_mock_token_verifier


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Provide a fresh isolated SQLite DB for each test."""
    db_file = str(tmp_path / "test_firebase_auth.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    from config import get_settings
    get_settings.cache_clear()
    import importlib, services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    from routes.auth import clear_user_cache
    clear_user_cache()
    yield db_mod
    clear_user_cache()
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def setup_mock_firebase_verifier():
    """Configure mock token verification for simulated test tokens."""
    def mock_verifier(token: str):
        if token == "valid-token-alpha":
            return {
                "uid": "firebase_uid_alpha_001",
                "email": "alpha@operator.sec",
                "name": "Operator Alpha",
                "picture": "https://lh3.googleusercontent.com/avatar_alpha.png",
                "email_verified": True,
            }
        elif token == "valid-token-beta":
            return {
                "uid": "firebase_uid_beta_002",
                "email": "beta@operator.sec",
                "name": "Operator Beta",
                "picture": "https://lh3.googleusercontent.com/avatar_beta.png",
                "email_verified": True,
            }
        elif token == "expired-token":
            # Simulate expired token
            return None
        # All other tokens return None (invalid)
        return None

    set_mock_token_verifier(mock_verifier)
    yield
    set_mock_token_verifier(None)


@pytest.mark.asyncio
async def test_health_endpoint_is_public(temp_db):
    """GET /health must be accessible without any Authorization header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "ollama_reachable" in data


@pytest.mark.asyncio
async def test_chat_unauthenticated_returns_401(temp_db):
    """POST /api/chat without token must return HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": False},
        )
        assert res.status_code == 401
        assert "Authentication required" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_chat_invalid_and_expired_tokens_return_401(temp_db):
    """POST /api/chat with malformed, invalid, or expired tokens must return HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Malformed header (no Bearer prefix)
        res1 = await ac.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": False},
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert res1.status_code == 401

        # 2. Empty Bearer token
        res2 = await ac.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": False},
            headers={"Authorization": "Bearer "},
        )
        assert res2.status_code == 401

        # 3. Invalid token string
        res3 = await ac.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": False},
            headers={"Authorization": "Bearer garbage-token-12345"},
        )
        assert res3.status_code == 401

        # 4. Expired token
        res4 = await ac.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": False},
            headers={"Authorization": "Bearer expired-token"},
        )
        assert res4.status_code == 401


@pytest.mark.asyncio
async def test_chat_with_valid_firebase_token_succeeds(temp_db):
    """POST /api/chat with valid token reaches chat pipeline and persists under Firebase UID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Send quick-route greeting message
        res = await ac.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "hi friday"}],
                "conversation_id": "conv-test-alpha-001",
                "stream": False,
            },
            headers={"Authorization": "Bearer valid-token-alpha"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "FRIDAY" in data["content"]

        # Verify conversation in database is tied to Firebase UID
        conv = temp_db.get_conversation("conv-test-alpha-001", user_id="firebase_uid_alpha_001")
        assert conv is not None
        assert conv["user_id"] == "firebase_uid_alpha_001"


@pytest.mark.asyncio
async def test_conversations_require_authentication(temp_db):
    """Conversation management endpoints must return HTTP 401 when unauthenticated."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # GET /api/conversations without token
        res_list = await ac.get("/api/conversations")
        assert res_list.status_code == 401

        # POST /api/conversations without token
        res_create = await ac.post("/api/conversations", json={"title": "Unauthorized"})
        assert res_create.status_code == 401


@pytest.mark.asyncio
async def test_multi_user_history_isolation_by_firebase_uid(temp_db):
    """Verify that Operator Alpha cannot see or access Operator Beta's conversations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Operator Alpha creates a session
        c_a = await ac.post(
            "/api/conversations",
            json={"title": "Alpha Red Team Operation"},
            headers={"Authorization": "Bearer valid-token-alpha"},
        )
        assert c_a.status_code == 201
        id_a = c_a.json()["id"]

        # 2. Operator Beta creates a session
        c_b = await ac.post(
            "/api/conversations",
            json={"title": "Beta Lateral Movement"},
            headers={"Authorization": "Bearer valid-token-beta"},
        )
        assert c_b.status_code == 201
        id_b = c_b.json()["id"]

        # 3. Alpha lists sessions -> sees ONLY Alpha's session
        list_a = await ac.get(
            "/api/conversations",
            headers={"Authorization": "Bearer valid-token-alpha"},
        )
        assert list_a.status_code == 200
        titles_a = [c["title"] for c in list_a.json()]
        assert "Alpha Red Team Operation" in titles_a
        assert "Beta Lateral Movement" not in titles_a

        # 4. Beta lists sessions -> sees ONLY Beta's session
        list_b = await ac.get(
            "/api/conversations",
            headers={"Authorization": "Bearer valid-token-beta"},
        )
        assert list_b.status_code == 200
        titles_b = [c["title"] for c in list_b.json()]
        assert "Beta Lateral Movement" in titles_b
        assert "Alpha Red Team Operation" not in titles_b

        # 5. Beta cannot read Alpha's session by ID
        unauth_get = await ac.get(
            f"/api/conversations/{id_a}",
            headers={"Authorization": "Bearer valid-token-beta"},
        )
        assert unauth_get.status_code == 404


@pytest.mark.asyncio
async def test_auth_me_and_verify_endpoints(temp_db):
    """Verify /api/auth/me and /api/auth/verify endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # GET /api/auth/me
        me_res = await ac.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer valid-token-alpha"},
        )
        assert me_res.status_code == 200
        data = me_res.json()
        assert data["uid"] == "firebase_uid_alpha_001"
        assert data["email"] == "alpha@operator.sec"
        assert data["name"] == "Operator Alpha"

        # POST /api/auth/verify
        verify_res = await ac.post(
            "/api/auth/verify",
            json={"id_token": "valid-token-alpha"},
        )
        assert verify_res.status_code == 200
        v_data = verify_res.json()
        assert v_data["uid"] == "firebase_uid_alpha_001"


@pytest.mark.asyncio
async def test_dev_token_rejected_in_production(monkeypatch):
    """Dev tokens must be strictly rejected when APP_ENV is production."""
    from config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "hi"}], "stream": False},
            headers={"Authorization": "Bearer dev-token:bad-uid:bad@mail.com:Bad User"},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_replace_conversation_messages_endpoint(temp_db):
    """Verify PUT /api/conversations/{conv_id}/messages security & replacement."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthenticated request -> 401
        res = await ac.put(
            "/api/conversations/test-conv/messages",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
        assert res.status_code == 401

        # 2. Operator Alpha creates a session
        create_res = await ac.post(
            "/api/conversations",
            json={"id": "conv-alpha-edit", "title": "Alpha Session"},
            headers={"Authorization": "Bearer valid-token-alpha"},
        )
        assert create_res.status_code == 201

        # Append messages to Alpha's session
        temp_db.append_message("conv-alpha-edit", "user", "original prompt 1")
        temp_db.append_message("conv-alpha-edit", "assistant", "original reply 1")
        temp_db.append_message("conv-alpha-edit", "user", "original prompt 2")

        # 3. Operator Beta attempts to edit Alpha's session -> 404
        beta_edit = await ac.put(
            "/api/conversations/conv-alpha-edit/messages",
            json={"messages": [{"role": "user", "content": "hijacked prompt"}]},
            headers={"Authorization": "Bearer valid-token-beta"},
        )
        assert beta_edit.status_code == 404

        # 4. Operator Alpha submits invalid role -> 422
        invalid_role = await ac.put(
            "/api/conversations/conv-alpha-edit/messages",
            json={"messages": [{"role": "invalid_role", "content": "bad"}]},
            headers={"Authorization": "Bearer valid-token-alpha"},
        )
        assert invalid_role.status_code == 422

        # 5. Operator Alpha replaces messages -> 200 and messages updated
        alpha_edit = await ac.put(
            "/api/conversations/conv-alpha-edit/messages",
            json={
                "messages": [
                    {"role": "user", "content": "edited prompt 1"},
                    {"role": "assistant", "content": "new reply 1"},
                ]
            },
            headers={"Authorization": "Bearer valid-token-alpha"},
        )
        assert alpha_edit.status_code == 200
        assert alpha_edit.json()["count"] == 2

        # 6. Verify via GET that session messages reflect replacement
        get_res = await ac.get(
            "/api/conversations/conv-alpha-edit",
            headers={"Authorization": "Bearer valid-token-alpha"},
        )
        assert get_res.status_code == 200
        data = get_res.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "edited prompt 1"
        assert data["messages"][1]["content"] == "new reply 1"
