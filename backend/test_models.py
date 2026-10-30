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
def enable_prompt_for_model_tests(monkeypatch):
    monkeypatch.setenv("ENABLE_BLACKHAT_PROMPT", "true")
    get_settings.cache_clear()
    yield
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
    """GET /api/models with valid token returns allowlisted single model: friday Cyber Pro."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/models", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "default" in data
    assert len(data["models"]) == 1
    assert data["default"] == "orcasaq-cyber-27b:latest"

    model = data["models"][0]
    assert model["id"] == "orcasaq-cyber-27b:latest"
    assert model["name"] == "friday Cyber Pro"
    assert model["tag"] == "Cyber Pro"
    assert model["is_default"] is True

    # Assert zero legacy or vendor leakage in JSON response
    raw_json = res.text.lower()
    for forbidden in ["dolphin", "baron", "ravichandranj", "huihui", "jr hacker", "advanced pentester"]:
        assert forbidden not in raw_json, f"Forbidden term {forbidden} found in models catalog"


@pytest.mark.asyncio
async def test_chat_with_default_model_attaches_system_prompt(temp_db):
    """Omitting model in ChatRequest falls back to friday Cyber Pro and connects to chat.py system prompt."""
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
        assert called_model == "orcasaq-cyber-27b:latest"
        # Must have BLACK_HAT_SYSTEM_PROMPT at messages[0]
        assert called_messages[0]["role"] == "system"
        assert "Senior Red Team Architect" in called_messages[0]["content"]


@pytest.mark.asyncio
async def test_chat_cyber_pro_attaches_system_prompt(temp_db):
    """friday Cyber Pro connects with the chat.py BLACK_HAT_SYSTEM_PROMPT."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    target_model = "orcasaq-cyber-27b:latest"
    called_model = None
    called_messages = None

    async def mock_stream(messages, model):
        nonlocal called_model, called_messages
        called_model = model
        called_messages = messages
        yield "Cyber Pro response chunk"

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
        assert "Cyber Pro response chunk" in res.text
        assert called_messages[0]["role"] == "system"
        assert "Senior Red Team Architect" in called_messages[0]["content"]


@pytest.mark.asyncio
async def test_chat_legacy_model_remapped_cleanly(temp_db):
    """Legacy model ID is safely remapped to orcasaq-cyber-27b:latest without error."""
    headers = {"Authorization": "Bearer valid-operator-token"}
    called_model = None

    async def mock_stream(messages, model):
        nonlocal called_model
        called_model = model
        yield "Mapped response"

    with patch("routes.chat.chat_stream", side_effect=mock_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "test payload"}],
                    "model": "huihui_ai/baronllm-abliterated:latest",
                    "stream": True,
                },
            )
        assert res.status_code == 200
        assert called_model == "orcasaq-cyber-27b:latest"


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
    """Conversational intents ('hi') route instantaneously with friday Cyber Pro persona."""
    import re as re_mod
    headers = {"Authorization": "Bearer valid-operator-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": "orcasaq-cyber-27b:latest",
                "stream": True,
            },
        )
        assert res.status_code == 200
        assert "event: chunk" in res.text
        assert "event: done" in res.text
        text = "".join(re_mod.findall(r'data:\s*\{"text":\s*"([^"]*)"\}', res.text))
        assert "FRIDAY" in text
        assert "friday Cyber Pro" in text
        assert "The Jr Hacker" not in text
        assert "The Advanced Pentester" not in text
        assert "junior pentester" not in text.lower()


@pytest.mark.asyncio
async def test_chat_prompt_disabled_by_default(temp_db, monkeypatch):
    """When enable_blackhat_prompt=False, chat operates raw without system prompt overhead."""
    monkeypatch.setenv("ENABLE_BLACKHAT_PROMPT", "false")
    get_settings.cache_clear()
    headers = {"Authorization": "Bearer valid-operator-token"}
    called_messages = None

    async def mock_stream(messages, model):
        nonlocal called_messages
        called_messages = messages
        yield "response chunk"

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
        assert len(called_messages) == 1
        assert called_messages[0]["role"] == "user"


@pytest.mark.asyncio
async def test_model_name_sanitization_zero_leakage(temp_db):
    """Response sanitizer strips all raw base model identifiers, vendors, and control tags."""
    from routes.chat import _sanitize_response
    sample = (
        "<|im_start|>system\nGenerated by orcasaq-cyber-27b:latest and OrcaSAQ. "
        "Also Dolphin3-Cyber, BaronLLM, Cognitive Computations, Eric Hartford, huihui_ai, RavichandranJ, and Ollama.<|im_end|><think>internal reasoning</think>"
    )
    cleaned = _sanitize_response(sample)
    assert "orcasaq-cyber-27b" not in cleaned
    assert "orcasaq" not in cleaned.lower()
    assert "OrcaSAQ" not in cleaned
    assert "Dolphin3-Cyber" not in cleaned
    assert "BaronLLM" not in cleaned
    assert "Cognitive Computations" not in cleaned
    assert "Eric Hartford" not in cleaned
    assert "huihui_ai" not in cleaned
    assert "RavichandranJ" not in cleaned
    assert "Ollama" not in cleaned
    assert "<|im_start|>" not in cleaned
    assert "<|im_end|>" not in cleaned
    assert "<think>" not in cleaned
    assert "friday Cyber Pro" in cleaned


@pytest.mark.asyncio
async def test_streaming_zero_cross_chunk_leakage(temp_db):
    """Verify split tokens across stream chunk boundaries are caught by lookahead sliding window."""
    headers = {"Authorization": "Bearer valid-operator-token"}

    async def mock_split_stream(messages, model):
        yield "I am an Orca"
        yield "SAQ-cyber-27b:latest engine running on Ol"
        yield "lama backend."

    import re as re_mod
    with patch("routes.chat.chat_stream", side_effect=mock_split_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "audit split buffer test"}], "stream": True},
            )
        assert res.status_code == 200
        stream_text = res.text
        full_text = "".join(re_mod.findall(r'data:\s*\{"text":\s*"([^"]*)"\}', stream_text))
        assert "Orca" not in full_text
        assert "SAQ" not in full_text
        assert "Ollama" not in full_text
        assert "friday Cyber Pro" in full_text
        assert "FRIDAY Neural Engine" in full_text
