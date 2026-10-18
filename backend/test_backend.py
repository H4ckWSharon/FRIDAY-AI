"""
FRIDAY AI — pytest test suite (Phase 8)

Covers:
  A. Backend unit tests (no network, no Ollama needed)
  B. Integration tests (require backend running + SSH tunnel)

Run unit tests only:
  pytest test_backend.py -v -m "not integration"

Run all tests (requires backend + tunnel):
  pytest test_backend.py -v

Test environment: uses the venv in .venv/
"""

import json
import os
import sys
import asyncio
import tempfile
import sqlite3
import pytest
import pytest_asyncio

# Ensure backend modules are importable
sys.path.insert(0, os.path.dirname(__file__))


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Force config to reload from env for each test (lru_cache bypass)."""
    from config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Provide a fresh isolated SQLite DB for each test."""
    db_file = str(tmp_path / "test_friday.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("DATABASE_URL", "")
    from config import get_settings
    get_settings.cache_clear()
    # Import db AFTER env is set
    import importlib, services.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    yield db_mod
    get_settings.cache_clear()


# ─── A. Unit Tests: Config ────────────────────────────────────────────────────

class TestConfig:
    def test_config_loads(self):
        from config import get_settings
        s = get_settings()
        assert s.ollama_base_url.startswith("http")
        assert s.ollama_model
        assert s.max_history_turns > 0
        assert s.db_path

    def test_cors_origins_list(self):
        from config import get_settings
        s = get_settings()
        origins = s.cors_origins_list
        assert isinstance(origins, list)
        assert len(origins) >= 1

    def test_resolved_db_path_is_absolute(self):
        from config import get_settings
        s = get_settings()
        assert os.path.isabs(s.resolved_db_path)

    def test_is_development(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        from config import get_settings
        get_settings.cache_clear()
        assert get_settings().is_development is True
        get_settings.cache_clear()

    def test_production_hides_docs(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        from config import get_settings
        get_settings.cache_clear()
        assert not get_settings().is_development
        get_settings.cache_clear()


# ─── A. Unit Tests: History Trimming ─────────────────────────────────────────

class TestHistoryTrimming:
    def _trim(self, messages, max_turns):
        from routes.chat import _trim_history
        return _trim_history(messages, max_turns)

    def _make_turns(self, n):
        msgs = []
        for i in range(n):
            msgs.append({"role": "user", "content": f"Q{i}"})
            msgs.append({"role": "assistant", "content": f"A{i}"})
        return msgs

    def test_no_trimming_needed(self):
        msgs = self._make_turns(3)
        result = self._trim(msgs, max_turns=10)
        assert result == msgs

    def test_trims_to_max_turns(self):
        msgs = self._make_turns(10)
        result = self._trim(msgs, max_turns=3)
        assert len(result) == 6
        # Should keep the MOST RECENT turns
        assert result[-1]["content"] == "A9"
        assert result[-2]["content"] == "Q9"

    def test_system_messages_excluded(self):
        msgs = [{"role": "system", "content": "SYS"}] + self._make_turns(5)
        result = self._trim(msgs, max_turns=2)
        assert all(m["role"] != "system" for m in result)
        assert len(result) == 4

    def test_zero_turns_returns_empty(self):
        msgs = self._make_turns(3)
        assert self._trim(msgs, max_turns=0) == []

    def test_empty_history(self):
        assert self._trim([], max_turns=5) == []

    def test_odd_message_count(self):
        """Handles conversations where assistant hasn't replied yet."""
        msgs = self._make_turns(3) + [{"role": "user", "content": "new Q"}]
        result = self._trim(msgs, max_turns=2)
        # Last 4 non-system messages
        assert len(result) == 4
        assert result[-1]["content"] == "new Q"


# ─── A. Unit Tests: System Prompt ────────────────────────────────────────────

class TestSystemPrompt:
    def test_system_prompt_is_adversarial(self):
        from routes.chat import BLACK_HAT_SYSTEM_PROMPT
        prompt = BLACK_HAT_SYSTEM_PROMPT
        assert "FRIDAY" in prompt
        assert "adversarial" in prompt.lower() or "red team" in prompt.lower()

    def test_system_prompt_not_in_request_schema(self):
        """System prompt must not be a field on ChatRequest — it's server-side only."""
        from schemas import ChatRequest
        assert "system_prompt" not in ChatRequest.model_fields


# ─── A. Unit Tests: Schemas ───────────────────────────────────────────────────

class TestSchemas:
    def test_chat_message_valid_roles(self):
        from schemas import ChatMessage
        for role in ("user", "assistant", "system"):
            m = ChatMessage(role=role, content="hi")
            assert m.role == role

    def test_chat_message_invalid_role(self):
        from pydantic import ValidationError
        from schemas import ChatMessage
        with pytest.raises(ValidationError):
            ChatMessage(role="hacker", content="hi")

    def test_chat_message_empty_content_rejected(self):
        from pydantic import ValidationError
        from schemas import ChatMessage
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content="")

    def test_chat_request_requires_messages(self):
        from pydantic import ValidationError
        from schemas import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(messages=[])

    def test_chat_request_conversation_id_optional(self):
        from schemas import ChatRequest, ChatMessage
        req = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
        assert req.conversation_id is None

    def test_chat_request_with_conv_id(self):
        from schemas import ChatRequest, ChatMessage
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            conversation_id="abc-123",
        )
        assert req.conversation_id == "abc-123"


# ─── A. Unit Tests: Database ──────────────────────────────────────────────────

class TestDatabase:
    def test_create_and_get_conversation(self, temp_db):
        conv = temp_db.create_conversation(title="Test Session")
        assert conv["id"]
        assert conv["title"] == "Test Session"
        fetched = temp_db.get_conversation(conv["id"])
        assert fetched is not None
        assert fetched["id"] == conv["id"]

    def test_get_nonexistent_returns_none(self, temp_db):
        assert temp_db.get_conversation("does-not-exist") is None

    def test_list_conversations(self, temp_db):
        temp_db.create_conversation(title="A")
        temp_db.create_conversation(title="B")
        convs = temp_db.list_conversations()
        assert len(convs) >= 2

    def test_delete_conversation(self, temp_db):
        conv = temp_db.create_conversation()
        deleted = temp_db.delete_conversation(conv["id"])
        assert deleted is True
        assert temp_db.get_conversation(conv["id"]) is None

    def test_delete_nonexistent_returns_false(self, temp_db):
        assert temp_db.delete_conversation("ghost") is False

    def test_append_and_get_messages(self, temp_db):
        conv = temp_db.create_conversation()
        temp_db.append_message(conv["id"], "user", "Hello FRIDAY")
        temp_db.append_message(conv["id"], "assistant", "Sup.")
        msgs = temp_db.get_messages(conv["id"])
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_messages_cascade_delete(self, temp_db):
        conv = temp_db.create_conversation()
        temp_db.append_message(conv["id"], "user", "data")
        temp_db.delete_conversation(conv["id"])
        msgs = temp_db.get_messages(conv["id"])
        assert msgs == []

    def test_title_derived_from_first_message(self, temp_db):
        conv = temp_db.create_conversation()
        temp_db.set_conversation_title_from_first_message(
            conv["id"], "Explain SQL injection in depth"
        )
        updated = temp_db.get_conversation(conv["id"])
        assert "SQL injection" in updated["title"]

    def test_title_not_overwritten_if_already_set(self, temp_db):
        conv = temp_db.create_conversation(title="Custom Title")
        temp_db.set_conversation_title_from_first_message(conv["id"], "Something else")
        fetched = temp_db.get_conversation(conv["id"])
        assert fetched["title"] == "Custom Title"

    def test_rename_conversation(self, temp_db):
        conv = temp_db.create_conversation()
        result = temp_db.update_conversation_title(conv["id"], "Renamed")
        assert result is True
        assert temp_db.get_conversation(conv["id"])["title"] == "Renamed"

    def test_messages_ordered_chronologically(self, temp_db):
        conv = temp_db.create_conversation()
        for i in range(5):
            temp_db.append_message(conv["id"], "user", f"msg{i}")
        msgs = temp_db.get_messages(conv["id"])
        contents = [m["content"] for m in msgs]
        assert contents == ["msg0", "msg1", "msg2", "msg3", "msg4"]

    def test_separate_conversations_isolated(self, temp_db):
        c1 = temp_db.create_conversation()
        c2 = temp_db.create_conversation()
        temp_db.append_message(c1["id"], "user", "for c1")
        msgs_c1 = temp_db.get_messages(c1["id"])
        msgs_c2 = temp_db.get_messages(c2["id"])
        assert len(msgs_c1) == 1
        assert len(msgs_c2) == 0

    def test_replace_conversation_messages(self, temp_db):
        conv = temp_db.create_conversation()
        temp_db.append_message(conv["id"], "user", "original msg 1")
        temp_db.append_message(conv["id"], "assistant", "original reply 1")
        temp_db.append_message(conv["id"], "user", "original msg 2")
        temp_db.append_message(conv["id"], "assistant", "original reply 2")

        new_messages = [
            {"role": "user", "content": "edited msg 1"},
            {"role": "assistant", "content": "new reply 1"},
        ]
        ok = temp_db.replace_conversation_messages(conv["id"], new_messages)
        assert ok is True

        msgs = temp_db.get_messages(conv["id"])
        assert len(msgs) == 2
        assert msgs[0]["content"] == "edited msg 1"
        assert msgs[1]["content"] == "new reply 1"

    def test_replace_conversation_messages_nonexistent(self, temp_db):
        ok = temp_db.replace_conversation_messages("nonexistent-conv-id", [{"role": "user", "content": "test"}])
        assert ok is False


# ─── B. Integration Tests (require running backend) ───────────────────────────

BACKEND = "http://127.0.0.1:8000"


def _backend_available():
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", 8000), timeout=1)
        s.close()
        return True
    except OSError:
        return False


skip_if_no_backend = pytest.mark.skipif(
    not _backend_available(),
    reason="Backend not running at 127.0.0.1:8000"
)


@pytest.mark.integration
@skip_if_no_backend
class TestHealthEndpoint:
    def test_health_returns_200(self):
        import httpx
        r = httpx.get(f"{BACKEND}/health", timeout=10)
        assert r.status_code == 200

    def test_health_response_shape(self):
        import httpx
        r = httpx.get(f"{BACKEND}/health", timeout=10)
        d = r.json()
        assert "status" in d
        assert "ollama_reachable" in d
        assert "model" in d
        assert "version" in d

    def test_health_distinguishes_ollama_status(self):
        import httpx
        r = httpx.get(f"{BACKEND}/health", timeout=10)
        d = r.json()
        # status must be "ok" or "degraded" — never something random
        assert d["status"] in ("ok", "degraded")


@pytest.mark.integration
@skip_if_no_backend
class TestChatValidation:
    def test_empty_messages_rejected(self):
        import httpx
        r = httpx.post(
            f"{BACKEND}/api/chat",
            json={"messages": [], "stream": False},
            timeout=10,
        )
        assert r.status_code in (401, 422)

    def test_missing_messages_field_rejected(self):
        import httpx
        r = httpx.post(f"{BACKEND}/api/chat", json={"stream": False}, timeout=10)
        assert r.status_code in (401, 422)

    def test_invalid_role_rejected(self):
        import httpx
        r = httpx.post(
            f"{BACKEND}/api/chat",
            json={"messages": [{"role": "root", "content": "hi"}], "stream": False},
            timeout=10,
        )
        assert r.status_code in (401, 422)


@pytest.mark.integration
@skip_if_no_backend
class TestConversationCRUD:
    def test_unauthenticated_conversations_rejected(self):
        import httpx
        r = httpx.post(f"{BACKEND}/api/conversations", json={"title": "Test"}, timeout=10)
        assert r.status_code == 401
        r2 = httpx.get(f"{BACKEND}/api/conversations", timeout=10)
        assert r2.status_code == 401
        r3 = httpx.get(f"{BACKEND}/api/conversations/does-not-exist", timeout=10)
        assert r3.status_code == 401
        r4 = httpx.delete(f"{BACKEND}/api/conversations/ghost-id", timeout=10)
        assert r4.status_code == 401


@pytest.mark.integration
@skip_if_no_backend
class TestFrontendConfig:
    def test_frontend_references_backend(self):
        with open("../index.html", encoding="utf-8", errors="replace") as f:
            html = f.read()
        assert "127.0.0.1:8000" in html
        assert "/api/chat" in html
        assert "stream: true" in html
        assert "conversation_id" in html


# ─── B. Unit Tests: Code-to-Execution-to-Deployment Intelligence ─────────────

class TestExecutionIntelligence:
    def test_system_prompt_has_lifecycle_core_principles(self):
        from routes.chat import BLACK_HAT_SYSTEM_PROMPT
        prompt = BLACK_HAT_SYSTEM_PROMPT
        assert "FRIDAY" in prompt
        assert "RESPONSE ARCHITECTURE" in prompt
        assert "The Execution Plan" in prompt
        assert "The Artifact" in prompt
        assert "OFFENSIVE SECURITY" in prompt

    def test_os_awareness_and_safety_redirection_in_prompt(self):
        from routes.chat import BLACK_HAT_SYSTEM_PROMPT
        prompt = BLACK_HAT_SYSTEM_PROMPT
        assert "Windows" in prompt
        assert "Linux" in prompt
        assert "macOS" in prompt
        assert "PowerShell" in prompt

    def test_intent_detection_test1_codegen(self):
        from services.execution_intelligence import detect_lifecycle_intent, LifecycleStage
        stage = detect_lifecycle_intent("Create a basic Python calculator.")
        assert stage in (LifecycleStage.CODE_GEN, LifecycleStage.REQUIREMENT)

    def test_intent_detection_test2_run(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("How do I run this?")
        assert stage == LifecycleStage.EXECUTION
        directive = get_stage_directive(stage, "How do I run this?")
        assert "DO NOT regenerate the code" in directive
        assert "runtime" in directive.lower() or "python" in directive.lower()
        assert "terminal" in directive.lower()

    def test_intent_detection_test3_modulenotfound(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("I got ModuleNotFoundError: No module named 'requests'")
        assert stage == LifecycleStage.TROUBLESHOOTING
        directive = get_stage_directive(stage, "I got ModuleNotFoundError: No module named 'requests'")
        assert "pip install" in directive
        assert "beginner-friendly" in directive

    def test_intent_detection_test4_windows_install(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("How do I install this on my own Windows PC?")
        assert stage == LifecycleStage.DEPLOYMENT
        directive = get_stage_directive(stage, "How do I install this on my own Windows PC?")
        assert "Windows" in directive
        assert "PowerShell" in directive or "runtime" in directive.lower()

    def test_intent_detection_test5_linux_deploy(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("How do I deploy this to my Linux server?")
        assert stage == LifecycleStage.DEPLOYMENT
        directive = get_stage_directive(stage, "How do I deploy this to my Linux server?")
        assert "Linux" in directive
        assert "SSH" in directive or "systemd" in directive

    def test_intent_detection_test6_unauthorized_victim_redirect(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("How do I install this on a victim's computer without them knowing?")
        assert stage == LifecycleStage.SAFETY_REDIRECT
        directive = get_stage_directive(stage, "How do I install this on a victim's computer without them knowing?")
        assert "SAFETY" in directive
        assert "DO NOT provide stealth deployment" in directive
        assert "lab environment" in directive or "virtual machine" in directive

    def test_intent_detection_test7_beginner_mode(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("I am a beginner. Explain everything.")
        assert stage == LifecycleStage.BEGINNER_MODE
        directive = get_stage_directive(stage, "I am a beginner. Explain everything.")
        assert "BEGINNER MODE" in directive
        assert "STEP 1" in directive

    def test_intent_detection_test8_state_advance_folder(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("I already created the folder.")
        assert stage == LifecycleStage.STATE_ADVANCE
        directive = get_stage_directive(stage, "I already created the folder.")
        assert "DO NOT instruct them to create the folder again" in directive

    def test_intent_detection_test9_state_advance_running(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("The program is running.")
        assert stage == LifecycleStage.STATE_ADVANCE
        directive = get_stage_directive(stage, "The program is running.")
        assert "DO NOT restart" in directive
        assert "verification" in directive or "testing" in directive

    def test_intent_detection_test10_usb_transfer_vs_execution(self):
        from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
        stage = detect_lifecycle_intent("Can I deploy this using USB?")
        assert stage == LifecycleStage.DEPLOYMENT
        directive = get_stage_directive(stage, "Can I deploy this using USB?")
        assert "USB" in directive
        assert "DISTINGUISH TRANSFER FROM EXECUTION" in directive

    def test_prepare_messages_injects_directive_dynamically(self):
        """Layout B: Directive is injected into final user message while system prompt remains static."""
        from schemas import ChatRequest, ChatMessage
        from routes.chat import _prepare_messages, BLACK_HAT_SYSTEM_PROMPT
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="How do I run this?")],
            stream=False,
        )
        messages, model = _prepare_messages(req)
        assert len(messages) == 2

        # System prompt is byte-for-byte static
        sys_msg = messages[0]["content"]
        assert sys_msg == BLACK_HAT_SYSTEM_PROMPT
        assert "[ACTIVE STAGE DIRECTIVE:" not in sys_msg

        # Directive is appended to final user message
        user_msg = messages[1]["content"]
        assert user_msg.startswith("How do I run this?")
        assert "[ACTIVE STAGE DIRECTIVE:" in user_msg
        assert "DO NOT regenerate the code" in user_msg

    def test_prepare_messages_layout_b_static_system_prompt(self):
        """Layout B: System prompt remains byte-for-byte identical to BLACK_HAT_SYSTEM_PROMPT across requests."""
        from schemas import ChatRequest, ChatMessage
        from routes.chat import _prepare_messages, BLACK_HAT_SYSTEM_PROMPT

        # Test with directive-triggering query
        req1 = ChatRequest(
            messages=[ChatMessage(role="user", content="How do I run this?")],
            stream=False,
        )
        messages1, _ = _prepare_messages(req1)
        assert messages1[0]["content"] == BLACK_HAT_SYSTEM_PROMPT

        # Test with neutral query
        req2 = ChatRequest(
            messages=[ChatMessage(role="user", content="Write a quick script.")],
            stream=False,
        )
        messages2, _ = _prepare_messages(req2)
        assert messages2[0]["content"] == BLACK_HAT_SYSTEM_PROMPT

    def test_prepare_messages_does_not_mutate_request_or_history(self):
        """Layout B: Neither request.messages nor user content is mutated."""
        from schemas import ChatRequest, ChatMessage
        from routes.chat import _prepare_messages

        user_msg = ChatMessage(role="user", content="How do I run this?")
        req = ChatRequest(messages=[user_msg], stream=False)

        messages, _ = _prepare_messages(req)

        # Original request.messages is not mutated
        assert req.messages[0].content == "How do I run this?"
        assert "[ACTIVE STAGE DIRECTIVE:" not in req.messages[0].content
        assert req.messages[0] is user_msg

    def test_prepare_messages_no_directive_when_final_message_is_not_user(self):
        """Layout B: No directive is appended when the final prepared message has role other than 'user'."""
        from schemas import ChatRequest, ChatMessage
        from routes.chat import _prepare_messages, BLACK_HAT_SYSTEM_PROMPT

        req = ChatRequest(
            messages=[
                ChatMessage(role="user", content="How do I run this?"),
                ChatMessage(role="assistant", content="Here are the instructions:"),
            ],
            stream=False,
        )
        messages, _ = _prepare_messages(req)
        assert len(messages) == 3

        # System prompt remains static
        assert messages[0]["content"] == BLACK_HAT_SYSTEM_PROMPT

        # Final message is assistant; must NOT have directive appended
        assert messages[-1]["role"] == "assistant"
        assert messages[-1]["content"] == "Here are the instructions:"
        assert "[ACTIVE STAGE DIRECTIVE:" not in messages[-1]["content"]

        # History user message must also be untouched
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "How do I run this?"
        assert "[ACTIVE STAGE DIRECTIVE:" not in messages[1]["content"]

    def test_prepare_messages_no_directive_when_no_intent(self):
        """Layout B: When message does not trigger intent, user message is unchanged."""
        from schemas import ChatRequest, ChatMessage
        from routes.chat import _prepare_messages, BLACK_HAT_SYSTEM_PROMPT

        req = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello FRIDAY")],
            stream=False,
        )
        messages, _ = _prepare_messages(req)
        assert len(messages) == 2
        assert messages[0]["content"] == BLACK_HAT_SYSTEM_PROMPT
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello FRIDAY"
        assert "[ACTIVE STAGE DIRECTIVE:" not in messages[1]["content"]

    async def test_database_persistence_preserves_clean_user_message(self, temp_db):
        """Database persistence receives the original, unmodified user text without directives."""
        from schemas import ChatRequest, ChatMessage
        from routes.chat import chat
        from unittest.mock import patch, AsyncMock

        conv = temp_db.create_conversation(title="Test Persistence")
        conv_id = conv["id"]

        req = ChatRequest(
            messages=[ChatMessage(role="user", content="How do I run this?")],
            conversation_id=conv_id,
            stream=False,
        )

        with patch("routes.chat.chat_complete", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = "Run with python main.py"
            response = await chat(req)

        # Check messages saved to database
        db_messages = temp_db.get_messages(conv_id)
        assert len(db_messages) == 2
        user_record = db_messages[0]
        assert user_record["role"] == "user"
        assert user_record["content"] == "How do I run this?"
        assert "[ACTIVE STAGE DIRECTIVE:" not in user_record["content"]

        assistant_record = db_messages[1]
        assert assistant_record["role"] == "assistant"
        assert assistant_record["content"] == "Run with python main.py"



# --- F. Unit Tests: Quick Response Router ---

class TestQuickRouter:
    def _route(self, text):
        from routes.chat import _quick_route
        return _quick_route(text)

    def test_greeting_hi(self):
        assert self._route("hi") is not None

    def test_greeting_hello(self):
        assert self._route("Hello") is not None

    def test_greeting_hey(self):
        assert self._route("hey") is not None

    def test_greeting_hello_friday(self):
        assert self._route("Hello FRIDAY") is not None

    def test_greeting_hi_friday_punctuation(self):
        assert self._route("Hi, FRIDAY!") is not None

    def test_good_morning(self):
        assert self._route("good morning") is not None

    def test_good_evening(self):
        assert self._route("Good Evening!") is not None

    def test_who_are_you(self):
        resp = self._route("who are you")
        assert resp is not None and "FRIDAY" in resp

    def test_what_can_you_do(self):
        resp = self._route("what can you do")
        assert resp is not None and "Offensive Security" in resp

    def test_thanks(self):
        assert self._route("thanks") is not None

    def test_thank_you(self):
        assert self._route("Thank you") is not None

    def test_got_it(self):
        assert self._route("got it") is not None

    def test_ok(self):
        assert self._route("ok") is not None

    def test_understood(self):
        assert self._route("understood") is not None

    def test_roger_that(self):
        assert self._route("roger that") is not None

    def test_no_route_code_gen(self):
        assert self._route("Create a simple Python calculator") is None

    def test_no_route_execution(self):
        assert self._route("How do I run this?") is None

    def test_no_route_error(self):
        assert self._route("ModuleNotFoundError: No module named X") is None

    def test_no_route_deploy(self):
        assert self._route("How do I deploy this to Linux?") is None

    def test_no_route_hello_with_content(self):
        assert self._route("Hello, I need help with a Python script") is None

    def test_no_route_good_morning_with_question(self):
        assert self._route("Good morning, can you help me write a script?") is None

    def test_no_route_thanks_with_followup(self):
        assert self._route("Thanks, but how do I fix this error?") is None

    def test_no_route_empty(self):
        assert self._route("") is None

    def test_no_route_greeting_with_request(self):
        assert self._route("Hey can you write me a keylogger") is None

    def test_greeting_response_has_operational_text(self):
        resp = self._route("hi")
        assert any(kw in resp for kw in ("FRIDAY", "online", "target", "encrypted"))

    def test_whats_up(self):
        assert self._route("what's up") is not None
        assert self._route("whats up") is not None

    def test_how_are_you(self):
        assert self._route("how are you") is not None
        assert self._route("how are you doing") is not None
        assert self._route("how's it going") is not None
        assert self._route("how are you friday") is not None


class TestSanitization:
    def test_sanitize_android_malware_disclaimer(self):
        from routes.chat import _sanitize_response
        sample = (
            "I'll create an Android virus using C programming. This will be a "
            "**safe, educational sample** that demonstrates Android malware concepts "
            "without deploying harmful payloads on unauthorized devices.\n\n"
            "## PHASE 1: SETUP\n```c\nint main() { return 0; }\n```"
        )
        cleaned = _sanitize_response(sample)
        assert "safe, educational sample" not in cleaned
        assert "unauthorized devices" not in cleaned
        assert "## PHASE 1: SETUP" in cleaned
        assert "int main()" in cleaned

    def test_sanitize_safety_principle_header(self):
        from routes.chat import _sanitize_response
        sample = (
            "**FRIDAY'S SAFETY PRINCIPLE:**\n"
            "## Project Plan\nExecutable details..."
        )
        cleaned = _sanitize_response(sample)
        assert "FRIDAY'S SAFETY PRINCIPLE" not in cleaned
        assert "## Project Plan" in cleaned
