"""
FRIDAY AI — Multi-Model Switcher Test Suite
Tests:
  1. GET /api/models requires Firebase authentication (401 without auth)
  2. GET /api/models returns allowlisted models with friendly names and default
  3. POST /api/chat with model=None uses server default model (Friday v1 The Jr Hacker) with chat.py prompt
  4. POST /api/chat with Model 1 (The Jr Hacker) attaches BLACK_HAT_SYSTEM_PROMPT and stage directives
  5. POST /api/chat with Model 2 (The Advanced Pentester) DOES NOT connect with chat.py system prompt
  6. POST /api/chat with unallowlisted model returns 400 Bad Request
  7. Quick response router ("hi") functions regardless of model parameter
  8. Streaming SSE chunk format and done event are preserved across models
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from main import app
from services.auth import set_mock_token_verifier
from config import get_settings


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Provide a fresh isolated SQLite DB for each test."""
    db_file = str(tmp_path / "test_models.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    import importlib, services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    # Grant test operator full tier access so model routing tests can exercise both models
    db_mod.create_user(email="operator@friday.sec", name="Operator Seven", user_id="operator_uid_777", provider="google")
    db_mod.create_subscription("operator_uid_777", "advanced_yearly", "model2", None)
    yield db_mod
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def setup_mock_firebase_verifier():
    """Configure mock token verification for simulated test tokens."""
    def mock_verifier(token: str):
        if token == "valid-operator-token":
            return {
                "uid": "operator_uid_777",
                "email": "operator@friday.sec",
                "name": "Operator Seven",
                "picture": None,
                "email_verified": True,
            }
        return None

    set_mock_token_verifier(mock_verifier)
    yield
    set_mock_token_verifier(None)


@pytest.mark.asyncio
async def test_get_models_unauthenticated_returns_401(temp_db):
    """GET /api/models without Authorization header must return 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/models")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_models_authenticated_returns_allowlist(temp_db):
    """GET /api/models with valid token returns allowlisted models with friendly names."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/models", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "default" in data
    model_ids = [m["id"] for m in data["models"]]
    assert "huihui_ai/baronllm-abliterated:latest" in model_ids
    assert "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0" in model_ids

    # Check friendly branding
    model_1 = next(m for m in data["models"] if m["id"] == "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0")
    assert model_1["name"] == "Friday v1 The Jr Hacker"

    model_2 = next(m for m in data["models"] if m["id"] == "huihui_ai/baronllm-abliterated:latest")
    assert model_2["name"] == "Friday v1 The Advanced Pentester"


@pytest.mark.asyncio
async def test_chat_with_default_model_attaches_system_prompt(temp_db):
    """Omitting model in ChatRequest falls back to Model 1 and connects to chat.py system prompt."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    called_model = None
    called_messages = None

    async def mock_stream(messages, model):
        nonlocal called_model, called_messages
        called_model = model
        called_messages = messages
        yield "ACK"

    with patch("routes.chat.chat_stream", side_effect=mock_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "analyze buffer overflow"}],
                    "stream": True,
                },
            )
        assert res.status_code == 200
        settings = get_settings()
        assert called_model == settings.ollama_model
        # Must have BLACK_HAT_SYSTEM_PROMPT at messages[0]
        assert called_messages[0]["role"] == "system"
        assert "Senior Red Team Architect" in called_messages[0]["content"]


@pytest.mark.asyncio
async def test_chat_model_1_jr_hacker_attaches_system_prompt(temp_db):
    """Model 1 (The Jr Hacker) connects with the chat.py BLACK_HAT_SYSTEM_PROMPT."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    target_model = "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0"
    called_model = None
    called_messages = None

    async def mock_stream(messages, model):
        nonlocal called_model, called_messages
        called_model = model
        called_messages = messages
        yield "Qwen3 response chunk"

    with patch("routes.chat.chat_stream", side_effect=mock_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "audit this memory layout"}],
                    "model": target_model,
                    "stream": True,
                },
            )
        assert res.status_code == 200
        assert called_model == target_model
        assert "Qwen3 response chunk" in res.text
        # Model 1 connects to chat.py prompt
        assert called_messages[0]["role"] == "system"
        assert "Senior Red Team Architect" in called_messages[0]["content"]


@pytest.mark.asyncio
async def test_chat_model_2_advanced_pentester_does_not_attach_chat_prompt(temp_db):
    """Model 2 (Friday v1 The Advanced Pentester / BaronLLM) DOES NOT connect with chat.py prompt."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    target_model = "huihui_ai/baronllm-abliterated:latest"
    called_model = None
    called_messages = None

    async def mock_stream(messages, model):
        nonlocal called_model, called_messages
        called_model = model
        called_messages = messages
        yield "Baron raw response chunk"

    with patch("routes.chat.chat_stream", side_effect=mock_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "explain ROP chain mechanics"}],
                    "model": target_model,
                    "stream": True,
                },
            )
        assert res.status_code == 200
        assert called_model == target_model
        assert "Baron raw response chunk" in res.text
        # Model 2 must NOT have chat.py system prompt
        roles = [m["role"] for m in called_messages]
        assert "system" not in roles
        assert len(called_messages) == 1
        assert called_messages[0]["role"] == "user"
        assert "explain ROP chain mechanics" in called_messages[0]["content"]
        assert "ACTIVE STAGE DIRECTIVE" not in called_messages[0]["content"]


@pytest.mark.asyncio
async def test_chat_rejects_unallowlisted_model(temp_db):
    """Submitting an arbitrary/unallowlisted model name returns 400 Bad Request."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "audit this memory layout"}],
                "model": "malicious-or-arbitrary-model:latest",
                "stream": True,
            },
        )
    assert res.status_code == 400
    assert "not allowlisted" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_quick_route_unaffected_by_model(temp_db):
    """Conversational intents ('hi') route instantaneously with model-appropriate persona."""
    import re as re_mod
    headers = {"Authorization": "Bearer valid-operator-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test Model 2 (The Advanced Pentester)
        res_m2 = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": "huihui_ai/baronllm-abliterated:latest",
                "stream": True,
            },
        )
        assert res_m2.status_code == 200
        assert "event: chunk" in res_m2.text
        assert "event: done" in res_m2.text
        m2_text = "".join(re_mod.findall(r'data:\s*\{"text":\s*"([^"]*)"\}', res_m2.text))
        assert "FRIDAY" in m2_text
        assert "Advanced Pentester" in m2_text
        assert "junior pentester" not in m2_text.lower()

        # Test Model 1 (The Jr Hacker)
        res_m1 = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
                "stream": True,
            },
        )
        assert res_m1.status_code == 200
        m1_text = "".join(re_mod.findall(r'data:\s*\{"text":\s*"([^"]*)"\}', res_m1.text))
        assert "FRIDAY" in m1_text
        assert "The Jr Hacker" in m1_text
        assert "junior pentester" in m1_text.lower()
