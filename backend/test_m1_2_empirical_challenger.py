"""
Adversarial Stress Test Suite for Milestone 1
Challenger M1-2: API Boundary, Legacy Model Remapping & Model Allowlist Rejection
"""

import pytest
import asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from main import app
from config import get_settings
from services.auth import set_mock_token_verifier


FORBIDDEN_TERMS = [
    "dolphin",
    "baron",
    "ravichandranj",
    "huihui",
    "jr hacker",
    "advanced pentester",
    "model 1",
    "model 2",
    "eric hartford",
    "cognitive computations",
]


@pytest.fixture
def challenger_db(tmp_path, monkeypatch):
    """Isolated database fixture for challenger tests."""
    db_file = str(tmp_path / "challenger_m1_2.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    import importlib, services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()

    # Create test operators:
    # 1. Full access operator (tier: model2 / paid)
    for idx in range(25):
        db_mod.create_user(
            email=f"operator_paid_{idx}@friday.sec",
            name="Paid Operator",
            user_id=f"uid_paid_operator_{idx}",
            provider="google",
        )
        db_mod.create_subscription(f"uid_paid_operator_{idx}", "advanced_yearly", "model2", None)

    db_mod.create_user(
        email="operator_paid@friday.sec",
        name="Paid Operator",
        user_id="uid_paid_operator",
        provider="google",
    )
    db_mod.create_subscription("uid_paid_operator", "advanced_yearly", "model2", None)

    # 2. Free operator (tier: free)
    db_mod.create_user(
        email="operator_free@friday.sec",
        name="Free Operator",
        user_id="uid_free_operator",
        provider="google",
    )

    # 3. Legacy Jr Hacker operator (tier: model1)
    db_mod.create_user(
        email="operator_jr@friday.sec",
        name="Legacy Jr Operator",
        user_id="uid_legacy_jr_operator",
        provider="google",
    )
    db_mod.create_subscription("uid_legacy_jr_operator", "jr_hacker_monthly", "model1", None)

    yield db_mod
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def setup_mock_auth():
    """Mock auth verifier for test operators."""
    def mock_verifier(token: str):
        if token == "token-paid-operator":
            return {
                "uid": "uid_paid_operator",
                "email": "operator_paid@friday.sec",
                "name": "Paid Operator",
                "picture": None,
                "email_verified": True,
            }
        elif token.startswith("token-paid-operator-"):
            idx = token.split("-")[-1]
            return {
                "uid": f"uid_paid_operator_{idx}",
                "email": f"operator_paid_{idx}@friday.sec",
                "name": "Paid Operator",
                "picture": None,
                "email_verified": True,
            }
        elif token == "token-free-operator":
            return {
                "uid": "uid_free_operator",
                "email": "operator_free@friday.sec",
                "name": "Free Operator",
                "picture": None,
                "email_verified": True,
            }
        elif token == "token-legacy-jr":
            return {
                "uid": "uid_legacy_jr_operator",
                "email": "operator_jr@friday.sec",
                "name": "Legacy Jr Operator",
                "picture": None,
                "email_verified": True,
            }
        return None

    set_mock_token_verifier(mock_verifier)
    yield
    set_mock_token_verifier(None)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. GET /api/models Boundary & Leakage Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_models_unauthenticated_strict_401(challenger_db):
    """Unauthenticated calls to /api/models must strictly return 401 and leak no metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/models")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    # Verify no model information is leaked in error response
    body = res.text.lower()
    for term in FORBIDDEN_TERMS + ["orcasaq"]:
        assert term not in body, f"Term '{term}' leaked in 401 response: {res.text}"


@pytest.mark.asyncio
async def test_get_models_malformed_auth_headers(challenger_db):
    """Malformed and invalid tokens must return 401 with no model leakage."""
    bad_headers = [
        {"Authorization": "Basic admin:admin"},
        {"Authorization": "Bearer "},
        {"Authorization": "Bearer invalid.jwt.token"},
        {"Authorization": "Token 123456"},
        {"Authorization": ""},
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for headers in bad_headers:
            res = await ac.get("/api/models", headers=headers)
            assert res.status_code == 401, f"Header {headers} gave {res.status_code} instead of 401"
            body = res.text.lower()
            for term in FORBIDDEN_TERMS:
                assert term not in body, f"Forbidden term '{term}' leaked with header {headers}"


@pytest.mark.asyncio
async def test_get_models_authenticated_single_cyber_pro(challenger_db):
    """Authenticated request returns strictly single model: orcasaq-cyber-27b:latest as friday Cyber Pro."""
    headers = {"Authorization": "Bearer token-paid-operator"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/models", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()

    assert "models" in data, "Response missing 'models' key"
    assert "default" in data, "Response missing 'default' key"
    assert len(data["models"]) == 1, f"Expected exactly 1 model, found {len(data['models'])}"
    assert data["default"] == "orcasaq-cyber-27b:latest"

    model = data["models"][0]
    assert model["id"] == "orcasaq-cyber-27b:latest"
    assert model["name"] == "friday Cyber Pro"
    assert model["tag"] == "Cyber Pro"
    assert model["is_default"] is True

    raw_json = res.text.lower()
    for term in FORBIDDEN_TERMS:
        assert term not in raw_json, f"Forbidden term '{term}' found in /api/models response!"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. POST /api/chat Legacy Model Remapping Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_model", [
    "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
    "huihui_ai/baronllm-abliterated:latest",
])
async def test_legacy_model_remapped_streaming(challenger_db, legacy_model):
    """Legacy model IDs in streaming mode cleanly remap to orcasaq-cyber-27b:latest without 400/500."""
    headers = {"Authorization": "Bearer token-paid-operator"}
    captured_model = None

    async def mock_chat_stream(messages, model):
        nonlocal captured_model
        captured_model = model
        yield "Streaming chunk response"

    with patch("routes.chat.chat_stream", side_effect=mock_chat_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "analyze buffer overflow"}],
                    "model": legacy_model,
                    "stream": True,
                },
            )
    assert res.status_code == 200, f"Expected 200 for legacy model {legacy_model}, got {res.status_code}"
    assert captured_model == "orcasaq-cyber-27b:latest", (
        f"Legacy model {legacy_model} did not map to orcasaq-cyber-27b:latest; got {captured_model}"
    )
    assert "Streaming chunk response" in res.text


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_model", [
    "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
    "huihui_ai/baronllm-abliterated:latest",
])
async def test_legacy_model_remapped_non_streaming(challenger_db, legacy_model):
    """Legacy model IDs in non-streaming mode cleanly remap to orcasaq-cyber-27b:latest with model='friday Cyber Pro'."""
    headers = {"Authorization": "Bearer token-paid-operator"}
    captured_model = None

    async def mock_chat_complete(messages, model):
        nonlocal captured_model
        captured_model = model
        return "Non-streaming exploit analysis complete."

    with patch("routes.chat.chat_complete", side_effect=mock_chat_complete):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "synthesize shellcode payload"}],
                    "model": legacy_model,
                    "stream": False,
                },
            )
    assert res.status_code == 200, f"Expected 200 for legacy model {legacy_model}, got {res.status_code}"
    assert captured_model == "orcasaq-cyber-27b:latest", (
        f"Legacy model {legacy_model} did not map to orcasaq-cyber-27b:latest; got {captured_model}"
    )
    data = res.json()
    assert data["model"] == "friday Cyber Pro", f"Expected display_model 'friday Cyber Pro', got {data.get('model')}"
    assert data["content"] == "Non-streaming exploit analysis complete."


@pytest.mark.asyncio
async def test_legacy_model_remapped_for_free_tier(challenger_db):
    """Free tier users requesting legacy model 1 get clean remapping to orcasaq-cyber-27b:latest."""
    headers = {"Authorization": "Bearer token-free-operator"}
    captured_model = None

    async def mock_chat_stream(messages, model):
        nonlocal captured_model
        captured_model = model
        yield "Free operator response"

    with patch("routes.chat.chat_stream", side_effect=mock_chat_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "analyze network scan"}],
                    "model": "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
                    "stream": True,
                },
            )
    assert res.status_code == 200
    assert captured_model == "orcasaq-cyber-27b:latest"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. POST /api/chat Unallowlisted Model Rejection Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.parametrize("arbitrary_model", [
    "llama3:8b",
    "gpt-4o",
    "claude-3-5-sonnet",
    "deepseek-r1:70b",
    "mistral:7b",
    "orcasaq-cyber-27b",  # missing :latest tag
    "ORCASAQ-CYBER-27B:LATEST",  # case variation
    "orcasaq_cyber_27b:latest",  # underscore variation
    "dolphin",  # partial name
    "baronllm",  # partial name
    "../../../etc/passwd",  # path traversal payload
    "model; DROP TABLE users;--",  # SQL injection payload
    "orcasaq-cyber-27b:latest\nmalicious",  # newline injection
])
async def test_unallowlisted_models_strictly_rejected_400(challenger_db, arbitrary_model):
    """Arbitrary, malicious, or malformed model names must be rejected with HTTP 400."""
    headers = {"Authorization": "Bearer token-paid-operator"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "perform penetration test"}],
                "model": arbitrary_model,
                "stream": True,
            },
        )
    assert res.status_code == 400, (
        f"Model '{arbitrary_model}' was NOT rejected with 400; got {res.status_code}: {res.text}"
    )
    data = res.json()
    assert "not allowlisted" in data["detail"].lower(), (
        f"Unexpected error detail for '{arbitrary_model}': {data}"
    )


@pytest.mark.asyncio
async def test_chat_omitted_model_falls_back_to_cyber_pro(challenger_db):
    """When 'model' field is omitted or None, request falls back to default orcasaq-cyber-27b:latest."""
    headers = {"Authorization": "Bearer token-paid-operator"}
    captured_model = None

    async def mock_chat_stream(messages, model):
        nonlocal captured_model
        captured_model = model
        yield "Default model response"

    with patch("routes.chat.chat_stream", side_effect=mock_chat_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Test 1: model is None
            res1 = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "offensive analysis"}],
                    "model": None,
                    "stream": True,
                },
            )
            assert res1.status_code == 200
            assert captured_model == "orcasaq-cyber-27b:latest"

            # Test 2: model field completely omitted
            res2 = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "reverse engineering binary"}],
                    "stream": True,
                },
            )
            assert res2.status_code == 200
            assert captured_model == "orcasaq-cyber-27b:latest"


@pytest.mark.asyncio
async def test_chat_empty_or_whitespace_model_falls_back_cleanly(challenger_db):
    """Empty string or whitespace-only model field falls back cleanly to default model."""
    headers = {"Authorization": "Bearer token-paid-operator"}
    captured_model = None

    async def mock_chat_stream(messages, model):
        nonlocal captured_model
        captured_model = model
        yield "Whitespace model response"

    with patch("routes.chat.chat_stream", side_effect=mock_chat_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            for empty_val in ["", "   ", "\t\n"]:
                res = await ac.post(
                    "/api/chat",
                    headers=headers,
                    json={
                        "messages": [{"role": "user", "content": "analyze kernel memory"}],
                        "model": empty_val,
                        "stream": True,
                    },
                )
                assert res.status_code == 200, f"Value {empty_val!r} failed with {res.status_code}"
                assert captured_model == "orcasaq-cyber-27b:latest"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Quick Route Interaction with Model Parameter
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_quick_route_branding_and_behavior_under_unallowlisted_model(challenger_db):
    """
    Empirically test whether quick routes (e.g. 'hi') execute when an unallowlisted model is passed.
    Note: Document whether quick route intercepts before model validation.
    """
    headers = {"Authorization": "Bearer token-paid-operator"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "model": "unallowlisted-model:8b",
                "stream": False,
            },
        )
    # Record empirical outcome
    assert res.status_code in (200, 400), f"Unexpected status: {res.status_code}"
    if res.status_code == 200:
        data = res.json()
        assert data["model"] == "friday Cyber Pro"
        assert "friday cyber pro" in data["content"].lower()
        for forbidden in FORBIDDEN_TERMS:
            assert forbidden not in data["content"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GET /health and GET /api/health Verification Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["/health", "/api/health"])
async def test_health_endpoints_brand_and_reachability(challenger_db, endpoint):
    """Health endpoints are public, return 200, and show model: 'friday Cyber Pro'."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(endpoint)
    assert res.status_code == 200, f"Endpoint {endpoint} returned {res.status_code}"
    data = res.json()

    assert data["model"] == "friday Cyber Pro", f"Expected model 'friday Cyber Pro', got {data.get('model')}"
    assert data["version"] == "2.0.0"
    assert "status" in data
    assert "ollama_reachable" in data
    assert "database_reachable" in data

    # Verify zero legacy exposure in raw health payload
    raw_text = res.text.lower()
    for forbidden in FORBIDDEN_TERMS + ["orcasaq"]:
        assert forbidden not in raw_text, f"Term '{forbidden}' exposed in {endpoint} response: {res.text}"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Streaming Cross-Chunk Leakage Stress Test
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_streaming_cross_chunk_boundary_scrubbing(challenger_db):
    """
    Stress-test sliding window buffer against malicious / raw model strings split across chunks.
    Ensures tokens split directly down the middle (e.g. 'Orca' + 'SAQ') are sanitized.
    """
    headers = {"Authorization": "Bearer token-paid-operator"}

    split_scenarios = [
        ["I am an Orca", "SAQ-cyber-27b model trained for cybersecurity."],
        ["Based on Dol", "phin3-Cyber-8B architecture."],
        ["Powered by Baron", "LLM-abliterated weights."],
        ["Developed by Cogni", "tive Computations."],
        ["Created by Eric ", "Hartford."],
        ["Hosted via Ol", "lama engine."],
        ["<|im_", "start|>system\nYou are an assistant<|im_", "end|>"],
        ["<th", "ink>pondering vulnerability mechanics</th", "ink>Exploit ready."],
    ]

    for scenario_chunks in split_scenarios:
        async def mock_stream(messages, model):
            for c in scenario_chunks:
                yield c

        with patch("routes.chat.chat_stream", side_effect=mock_stream):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post(
                    "/api/chat",
                    headers=headers,
                    json={
                        "messages": [{"role": "user", "content": "deep architecture query"}],
                        "model": "orcasaq-cyber-27b:latest",
                        "stream": True,
                    },
                )
            assert res.status_code == 200
            assembled_stream = res.text.lower()
            for forbidden in FORBIDDEN_TERMS:
                assert forbidden not in assembled_stream, (
                    f"Forbidden term '{forbidden}' leaked across chunk boundary in scenario: {scenario_chunks}\nOutput: {res.text}"
                )
            # Ensure tokenizer tags were stripped
            assert "<|im_start|>" not in assembled_stream
            assert "<|im_end|>" not in assembled_stream
            assert "<think>" not in assembled_stream
            assert "</think>" not in assembled_stream


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Legacy Model Access for 'model1' Tier Operator
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_legacy_model1_tier_access_boundaries(challenger_db):
    """
    Test how legacy model1 tier (Jr Hacker plan) behaves when requesting:
    - Legacy Model 1 (Dolphin3): should succeed and map to orcasaq-cyber-27b:latest
    - Legacy Model 2 (BaronLLM): should be blocked with 403 under current subscription gating
    """
    headers = {"Authorization": "Bearer token-legacy-jr"}

    # Legacy Model 1 (Dolphin3) -> Allowed for model1 tier
    captured_model = None
    async def mock_stream(messages, model):
        nonlocal captured_model
        captured_model = model
        yield "Jr tier chunk"

    with patch("routes.chat.chat_stream", side_effect=mock_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res1 = await ac.post(
                "/api/chat",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": "analyze network scan"}],
                    "model": "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
                    "stream": True,
                },
            )
        assert res1.status_code == 200
        assert captured_model == "orcasaq-cyber-27b:latest"

    # Legacy Model 2 (BaronLLM) -> In M1, model1 tier is blocked from Model 2 before remapping
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res2 = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "advanced exploit generation"}],
                "model": "huihui_ai/baronllm-abliterated:latest",
                "stream": True,
            },
        )
    # Documents current M1 behavior (403 required_tier: model2), scheduled for M2 consolidation
    assert res2.status_code == 403
    assert res2.json()["detail"]["error"] == "model_access_denied"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. High-Concurrency & Adversarial Payload Stress Testing
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_concurrent_legacy_and_valid_requests(challenger_db):
    """
    Fire 20 concurrent requests mixing legacy model IDs, valid model IDs, and omitted models.
    All must succeed (200 OK) with all legacy models properly remapped to orcasaq-cyber-27b:latest.
    """
    headers = {"Authorization": "Bearer token-paid-operator"}
    captured_models = []

    async def mock_stream(messages, model):
        captured_models.append(model)
        yield f"Chunk from {model}"

    models_to_test = [
        "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0",
        "huihui_ai/baronllm-abliterated:latest",
        "orcasaq-cyber-27b:latest",
        None,
    ] * 5  # 20 requests total

    with patch("routes.chat.chat_stream", side_effect=mock_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            tasks = [
                ac.post(
                    "/api/chat",
                    headers={"Authorization": f"Bearer token-paid-operator-{i}"},
                    json={
                        "messages": [{"role": "user", "content": f"concurrent test {i}"}],
                        "model": m,
                        "stream": True,
                    },
                )
                for i, m in enumerate(models_to_test)
            ]
            responses = await asyncio.gather(*tasks)

    for i, res in enumerate(responses):
        assert res.status_code == 200, f"Request {i} failed with status {res.status_code}"

    # Verify every single captured model was orcasaq-cyber-27b:latest
    assert len(captured_models) == 20
    for m in captured_models:
        assert m == "orcasaq-cyber-27b:latest", f"Unexpected model captured during concurrency: {m}"


@pytest.mark.asyncio
async def test_adversarial_malformed_payloads(challenger_db):
    """
    Adversarial inputs:
    - Extremely long model name (>5000 chars) -> 400 Bad Request
    - Non-string model type (int, list, dict) -> 422 Unprocessable Entity
    - Empty messages list -> 422 Unprocessable Entity
    - Invalid role (e.g. 'root', 'attacker') -> 422 Unprocessable Entity
    """
    headers = {"Authorization": "Bearer token-paid-operator"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Long model name
        res_long = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "overflow attempt"}],
                "model": "A" * 6000,
                "stream": True,
            },
        )
        assert res_long.status_code in (400, 422), f"Long model got {res_long.status_code}"

        # Non-string model
        res_type = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "type attack"}],
                "model": 1337,
                "stream": True,
            },
        )
        assert res_type.status_code == 422

        # Empty messages
        res_empty = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [],
                "model": "orcasaq-cyber-27b:latest",
                "stream": True,
            },
        )
        assert res_empty.status_code == 422

        # Invalid role
        res_role = await ac.post(
            "/api/chat",
            headers=headers,
            json={
                "messages": [{"role": "hacker", "content": "malicious role"}],
                "model": "orcasaq-cyber-27b:latest",
                "stream": True,
            },
        )
        assert res_role.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint_under_degraded_conditions(challenger_db):
    """
    When Ollama or DB is unreachable, health endpoint reports status='degraded'
    while STILL maintaining strict 'friday Cyber Pro' branding without leaking internals.
    """
    with patch("routes.health.check_ollama_reachable", return_value=False), \
         patch("routes.health.check_db_reachable", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["ollama_reachable"] is False
        assert data["database_reachable"] is False
        assert data["model"] == "friday Cyber Pro"

        raw_text = res.text.lower()
        for term in FORBIDDEN_TERMS + ["orcasaq"]:
            assert term not in raw_text, f"Term '{term}' exposed in degraded health response"
