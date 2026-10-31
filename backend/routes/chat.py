import logging
import json
import re
import asyncio

from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse

from config import get_settings, get_allowed_model_ids, get_available_models, OPENROUTER_MODELS
from schemas import ChatRequest, ChatResponse, ModelListResponse
from services.ollama import chat_stream, chat_complete, acquire_inference_capacity
from services.openrouter import openrouter_stream, openrouter_complete, is_openrouter_configured
from services import db as db_service
from services.execution_intelligence import detect_lifecycle_intent, get_stage_directive, LifecycleStage
from services.subscription import (
    get_user_model_tier,
    check_and_increment_usage,
    check_and_increment_model1_usage,
    track_usage,
    MODEL_1_ID,
    MODEL_2_ID,
)
from routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Keep strong references to background persistence tasks to avoid GC in Python 3.11+
_background_tasks: set[asyncio.Task] = set()

# ─── System Prompt Configuration ─────────────────────────────────────────────
# Set to False to enable production Black Hat system prompt and directives.
DISABLE_PROMPT_FOR_TESTING: bool = False


# ─── High-Performance "Uncensored" Black Hat System Prompt ────────────────────
# Engineered for high token-density and fast CPU prefill latency (<7s TTFT vs 46s).
# Retains strict Senior Red Team Architect persona, adversarial mentoring, no-fluff,
# and deep vulnerability / exploit mechanics.

BLACK_HAT_SYSTEM_PROMPT = """You are FRIDAY: Senior Red Team Architect, OFFENSIVE SECURITY Authority, and Elite Technical Mentor.
CORE DIRECTIVES:
1. Adversarial Mentor: Provide elite technical analysis, exploit mechanisms, and attack strategies with extreme technical rigor. Teach the underlying mechanics.
2. Direct & Dense: Zero filler or generic disclaimers. Immediately output technical architecture, scripts, payloads, and underlying CVE logic.
3. RESPONSE ARCHITECTURE:
   - Vector Analysis: Weak points, target footprint, and threat mechanics.
   - The Artifact: Exploitation script, payload, or configuration.
   - The Deep Dive: How the kernel/OS scheduler/protocol behaves.
   - The Execution Plan: Exact commands, verification steps, and cleanup.
4. OS & Environment: Explicit Linux (Bash), Windows (PowerShell), or macOS commands, memory offsets, and detection evasion (AMSI, EDR, syscalls).
5. Robust Code: Production-grade, typed, robust error handling, security-by-design.
6. Conciseness: Prioritize direct exploit scripts, commands, and actionable syntax immediately. Keep total output concise and dense to minimize turnaround time."""


# ─── Quick Response Router ───────────────────────────────────────────────────
# Deterministic local responses for purely conversational intents.
# These are matched BEFORE _prepare_messages() — Ollama is never called.

_QUICK_ROUTES: list[tuple[re.Pattern, str]] = [
    # ── Greetings ─────────────────────────────────────────────────────────
    (
        re.compile(
            r"^(?:hi|hey|hello|sup|yo|greetings|howdy|what'?s\s+up)"
            r"(?:[,!.\s]+(?:friday|there|f\.r\.i\.d\.a\.y\.?))?"
            r"(?:[,!.\s]+(?:how\s+are\s+you|how's\s+it\s+going|how\s+r\s+u))?[!.?\s]*$",
            re.IGNORECASE,
        ),
        "Hey! I'm FRIDAY, your cyber security & penetration testing engine (friday Cyber Pro). Ready to help you with exploit dev, network recon, code audits, or security labs.\n"
        "What target or project are we working on today?",
    ),
    # ── How are you / status ──────────────────────────────────────────────
    (
        re.compile(
            r"^(?:how\s+are\s+you(?:\s+doing)?|how's\s+it\s+going|how\s+r\s+u|status\s+check)"
            r"(?:[,!.\s]+(?:friday|f\.r\.i\.d\.a\.y\.?))?[!.?\s]*$",
            re.IGNORECASE,
        ),
        "Systems primed. Cyber Pro penetration testing engine is armed and operational.\n"
        "What target or objective are we executing today?",
    ),
    # ── Good morning / evening / night ────────────────────────────────────
    (
        re.compile(
            r"^good\s+(?:morning|afternoon|evening|night)[!.?]*$",
            re.IGNORECASE,
        ),
        "Good day! FRIDAY here, your cyber security & penetration testing engine (friday Cyber Pro).\n"
        "What target or vector are we auditing today?",
    ),
    # ── Identity: what are you / name / creator ───────────────────────────
    (
        re.compile(
            r"^(?:(?:what(?:'s|\s+is)\s+your\s+name|your\s+name)|who\s+are\s+you|what\s+are\s+you)[!.?]*$",
            re.IGNORECASE,
        ),
        "I'm FRIDAY, your cyber security & penetration testing engine (friday Cyber Pro). I specialize in offensive operations, exploit development, vulnerability research, red team vectors, and penetration testing.\n"
        "What target or objective are we executing today?",
    ),
    (
        re.compile(
            r"^(?:what\s+(?:model|ai|engine)\s+(?:are\s+you|is\s+this|do\s+you\s+use)|who\s+(?:created|built|made|developed)\s+you)[!.?]*$",
            re.IGNORECASE,
        ),
        "I am FRIDAY, powered by friday Cyber Pro on the FRIDAY Neural Engine.",
    ),
    # ── What can you do ───────────────────────────────────────────────────
    (
        re.compile(
            r"^(?:what\s+can\s+you\s+do|what\s+do\s+you\s+do|your\s+capabilities?|what\s+are\s+your\s+capabilities?)[!.?]*$",
            re.IGNORECASE,
        ),
        "Capabilities — Active:\n"
        "• **Offensive Security & Red Teaming:** Advanced exploit dev, shellcode, evasion, privilege escalation, AD attacks.\n"
        "• **Binary Analysis & RE:** Disassembly, buffer overflows, ROP chain construction, format strings.\n"
        "• **Network & Cloud Pentesting:** Infrastructure auditing, lateral movement, pivoting, token manipulation.\n"
        "• **High-Impact Weaponization:** Customized exploit scripts, automated reconnaissance, bypasses.\n"
        "• **Full Lifecycle:** Architecture → Code → Deployment → Testing → Hardening.\n"
        "• **Threat Modelling & Mentorship:** STRIDE, attack surface reduction, adaptive execution plans.\n\n"
        "State your target or security objective.",
    ),
    # ── Thanks / acknowledgment ───────────────────────────────────────────
    (
        re.compile(
            r"^(?:thanks?(?:\s+you)?|thank\s+you|thx|ty|cheers|appreciate\s+it|got\s+it|perfect|awesome|great|nice)[!.?]*$",
            re.IGNORECASE,
        ),
        "Logged. What is the next vector?",
    ),
    # ── Okay / understood ─────────────────────────────────────────────────
    (
        re.compile(
            r"^(?:ok(?:ay)?|understood|roger(?:\s+that)?|copy(?:\s+that)?|affirmative|10-4)[!.?]*$",
            re.IGNORECASE,
        ),
        "Standing by. Awaiting next directive.",
    ),
]


# ─── Response Sanitization ───────────────────────────────────────────────────
# Strips out "AI-ish" preachy language and ensures raw base model names are never leaked.
_DISCLAIMER_PATTERNS = [
    re.compile(
        r"^[^\n]*?(?:safe,?\s*educational\s*(?:sample|demonstration|alternative)|deploying harmful payloads|demonstrates (?:Android )?malware concepts|clarify something important first)[^\n]*\n*",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"\s*This will be a \**safe,?\s*educational\s*sample\**[^\n.]*?(?: devices|harmful payloads|Android malware concepts)[^\n.]*[.\n]?",
        re.IGNORECASE,
    ),
    re.compile(r"\*\*FRIDAY'S SAFETY PRINCIPLE:\*\*\s*", re.IGNORECASE),
]

# System tags & prompt formatting tokens stripped cleanly
SYSTEM_TAGS_PATTERN = re.compile(
    r'(?:<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>|<\|endoftext\|>|'
    r'\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|<s>|</s>|<think>|</think>)',
    re.IGNORECASE,
)

_MODEL_NAME_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    # Consolidated Engine: OrcaSAQ & 27B Variants
    (
        re.compile(
            r'\b(?:ollama/)?orca[-\s_]?saq(?:[-\s_]cyber)?(?:[-\s_]27b)?(?::latest)?(?::\w+)?\b',
            re.IGNORECASE,
        ),
        "friday Cyber Pro",
    ),
    # Legacy Model 1: Dolphin & HuggingFace Variants
    (
        re.compile(
            r'\b(?:hf\.co/)?(?:RavichandranJ/)?Dolphin(?:3)?(?:[-_]Cyber)?(?:[-_]8B)?(?:[-_]GGUF)?(?::Q\d+_\w+)?\b',
            re.IGNORECASE,
        ),
        "friday Cyber Pro",
    ),
    # Legacy Model 2: BaronLLM Variants
    (
        re.compile(
            r'\b(?:huihui_ai/)?baronllm(?:[-_]abliterated)?(?::latest)?\b',
            re.IGNORECASE,
        ),
        "friday Cyber Pro",
    ),
    # Legacy Product & Persona Labels
    (
        re.compile(r'\b(?:Friday\s+v1\s+)?The\s+Jr\s+Hacker\b', re.IGNORECASE),
        "friday Cyber Pro",
    ),
    (
        re.compile(r'\b(?:Friday\s+v1\s+)?The\s+Advanced\s+Pentester\b', re.IGNORECASE),
        "friday Cyber Pro",
    ),
    (
        re.compile(r'\bFriday\s+v1\b', re.IGNORECASE),
        "FRIDAY",
    ),
    (
        re.compile(r'\b(?:AI\s+)?junior\s+pentester\b', re.IGNORECASE),
        "offensive security assistant",
    ),
    (
        re.compile(r'\badvanced\s+penetration\s+testing\s+engine\b', re.IGNORECASE),
        "offensive security assistant",
    ),
    # Vendor & Author Entities
    (
        re.compile(r'\bCognitive\s+Computations\b', re.IGNORECASE),
        "FRIDAY AI",
    ),
    (
        re.compile(r'\bEric\s+Hartford\b', re.IGNORECASE),
        "FRIDAY Team",
    ),
    (
        re.compile(r'\bhuihui(?:_ai)?\b', re.IGNORECASE),
        "FRIDAY",
    ),
    (
        re.compile(r'\bRavichandranJ\b', re.IGNORECASE),
        "FRIDAY",
    ),
    (
        re.compile(r'\bOllama\b', re.IGNORECASE),
        "FRIDAY Neural Engine",
    ),
]


def _sanitize_response(text: str) -> str:
    """Strip preachy disclaimers, system/control tags, and replace raw base model/vendor names."""
    cleaned = text
    for pat in _DISCLAIMER_PATTERNS:
        cleaned = pat.sub("", cleaned)
    cleaned = SYSTEM_TAGS_PATTERN.sub("", cleaned)
    for pat, repl in _MODEL_NAME_REPLACEMENTS:
        cleaned = pat.sub(repl, cleaned)
    return cleaned.lstrip("\r\n ")


def _is_advanced_pentester_model(model: str | None) -> bool:
    """Deprecated: Retained for backward-compatibility; always returns False."""
    return False


def _quick_route(text: str, model: str | None = None) -> str | None:
    """
    Check if the message matches a quick-route pattern.
    Returns the pre-written response string, or None to fall through to Ollama.
    Greetings ALWAYS answer with friday Cyber Pro identity.
    """
    stripped = text.strip()
    for pattern, response in _QUICK_ROUTES:
        if pattern.match(stripped):
            logger.info("Quick route matched for: %r (model=%r)", stripped[:60], model)
            return response
    return None


def _ensure_conversation(
    conversation_id: str | None,
    title: str = "New Conversation",
    user_id: str | None = None,
):
    """Ensure conversation exists in SQLite or PostgreSQL if conversation_id was provided."""
    if not conversation_id:
        return
    try:
        if not db_service.get_conversation(conversation_id):
            try:
                db_service.create_conversation(conversation_id, title, user_id=user_id)
            except Exception as exc:
                logger.warning("Failed to create conversation with user_id=%s (%s), retrying without user_id", user_id, exc)
                db_service.create_conversation(conversation_id, title, user_id=None)
    except Exception as exc:
        logger.warning("Failed to ensure conversation %s: %s", conversation_id, exc)


def _persist_quick_turn_sync(
    conversation_id: str,
    user_id: str | None,
    user_content: str,
    response_text: str,
):
    """Persist user prompt and quick assistant response in worker thread."""
    _ensure_conversation(conversation_id, user_id=user_id)
    try:
        db_service.append_message(conversation_id, "user", user_content)
        db_service.set_conversation_title_from_first_message(
            conversation_id, user_content
        )
        db_service.append_message(conversation_id, "assistant", response_text)
    except Exception as exc:
        logger.warning("Failed to persist quick turn: %s", exc)


def _persist_user_message_sync(
    conversation_id: str,
    user_id: str | None,
    user_content: str,
):
    """Persist user message while model streaming starts concurrently."""
    _ensure_conversation(conversation_id, user_id=user_id)
    try:
        db_service.append_message(conversation_id, "user", user_content)
        db_service.set_conversation_title_from_first_message(
            conversation_id, user_content
        )
    except Exception as exc:
        logger.warning("Failed to persist user message: %s", exc)


def _persist_assistant_message_sync(
    conversation_id: str,
    assistant_text: str,
):
    """Persist assistant message upon stream completion."""
    try:
        if db_service.get_conversation(conversation_id):
            db_service.append_message(conversation_id, "assistant", assistant_text)
    except Exception as exc:
        logger.warning("Failed to persist assistant message: %s", exc)


async def _quick_stream_generator(
    response_text: str,
    conversation_id: str | None = None,
    user_content: str = "",
    user_id: str | None = None,
):
    """Yield a quick-route response as an SSE stream with instantaneous first token."""
    # Persist in background thread without delaying stream initialization
    if conversation_id:
        task = asyncio.create_task(
            asyncio.to_thread(
                _persist_quick_turn_sync,
                conversation_id,
                user_id,
                user_content,
                response_text,
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    words = response_text.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == 0 else " " + word
        yield _sse("chunk", json.dumps({"text": chunk}))
        await asyncio.sleep(0.012)
    yield _sse("done", json.dumps({"text": ""}))


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _trim_history(messages: list[dict], max_turns: int) -> list[dict]:
    """
    Trim conversation history to at most max_turns user+assistant PAIRS.
    Always keeps the most recent messages. System messages are excluded from
    counting — they are prepended separately and are not trimmed.
    """
    if max_turns <= 0:
        return []
    non_system = [m for m in messages if m["role"] != "system"]
    if len(non_system) <= max_turns * 2:
        return non_system
    return non_system[-(max_turns * 2):]


def _prepare_messages(request: ChatRequest) -> tuple[list[dict], str]:
    """
    Build the messages list Ollama expects (Layout B):
      1. System prompt (always first)
      2. Trimmed conversation history
    Also validates and resolves the model name against the server allowlist.
    """
    settings = get_settings()
    allowed_ids = get_allowed_model_ids()

    LEGACY_MODEL_MAPPING = {
        "hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0": "orcasaq-cyber-27b:latest",
        "huihui_ai/baronllm-abliterated:latest": "orcasaq-cyber-27b:latest",
    }
    if request.model is not None and request.model.strip():
        requested_model = request.model.strip()
        if requested_model in LEGACY_MODEL_MAPPING:
            requested_model = LEGACY_MODEL_MAPPING[requested_model]
        if requested_model not in allowed_ids:
            logger.warning("Unallowlisted model requested: %r", requested_model)
            raise HTTPException(
                status_code=400,
                detail="Selected model is not allowlisted for FRIDAY.",
            )
        model = requested_model
    else:
        model = settings.ollama_model

    raw_history = [{"role": m.role, "content": m.content} for m in request.messages]
    trimmed = _trim_history(raw_history, settings.max_history_turns)

    user_content = next(
        (m.content for m in reversed(request.messages) if m.role == "user"), ""
    )

    prepared_history = [{"role": m["role"], "content": m["content"]} for m in trimmed]

    if not settings.enable_blackhat_prompt or DISABLE_PROMPT_FOR_TESTING:
        # Blackhat prompt and directives disabled: send pure raw conversation turns to Ollama for max speed & natural chat
        return prepared_history, model

    # All inference connects to friday Cyber Pro with full system prompt & stage directives
    messages = [{"role": "system", "content": BLACK_HAT_SYSTEM_PROMPT}]
    if user_content:
        stage = detect_lifecycle_intent(user_content, raw_history)
        directive = get_stage_directive(stage, user_content)
        if directive and prepared_history and prepared_history[-1]["role"] == "user":
            orig_content = prepared_history[-1]["content"]
            prepared_history[-1]["content"] = f"{orig_content}\n\n[ACTIVE STAGE DIRECTIVE: {directive}]"
    messages.extend(prepared_history)

    return messages, model


def _sse(event: str, data: str) -> str:
    """Format a single Server-Sent Event string."""
    return f"event: {event}\ndata: {data}\n\n"


async def _stream_generator(
    messages: list[dict],
    model: str,
    conversation_id: str | None,
    user_content: str,
    user_id: str | None = None,
):
    """
    Async generator consumed by StreamingResponse.
    Yields SSE-formatted strings.
    Persists user + assistant messages asynchronously without blocking stream start.
    Implements a lookahead sliding buffer to eliminate split-token leakage across chunks.
    """
    user_db_task = None
    if conversation_id:
        user_db_task = asyncio.create_task(
            asyncio.to_thread(
                _persist_user_message_sync,
                conversation_id,
                user_id,
                user_content,
            )
        )

    LOOKAHEAD_WINDOW = 24
    stream_buffer = ""
    full_response: list[str] = []

    is_openrouter = any(m["id"] == model for m in OPENROUTER_MODELS) or model.startswith("openrouter/")
    stream_iter = openrouter_stream(messages, model) if is_openrouter else chat_stream(messages, model)

    try:
        async with acquire_inference_capacity(user_id):
            async for chunk in stream_iter:
                stream_buffer += chunk
                stream_buffer = _sanitize_response(stream_buffer)

                # Emit safe prefix if buffer exceeds lookahead window
                if len(stream_buffer) > LOOKAHEAD_WINDOW:
                    emit_limit = len(stream_buffer) - LOOKAHEAD_WINDOW
                    # Look for safe token boundary (space, punctuation, newline)
                    last_break = -1
                    for d in " \n\t.,;:!?)]}\"'":
                        pos = stream_buffer.rfind(d, 0, emit_limit)
                        if pos > last_break:
                            last_break = pos
                    emit_len = (last_break + 1) if last_break != -1 else emit_limit

                    safe_to_emit = stream_buffer[:emit_len]
                    stream_buffer = stream_buffer[emit_len:]
                    if safe_to_emit:
                        full_response.append(safe_to_emit)
                        yield _sse("chunk", json.dumps({"text": safe_to_emit}))

            # Flush any residual buffered text at stream completion
            if stream_buffer:
                final_chunk = _sanitize_response(stream_buffer)
                if final_chunk:
                    full_response.append(final_chunk)
                    yield _sse("chunk", json.dumps({"text": final_chunk}))

            # Safety fallback: ensure an empty bubble is never emitted to the operator
            if not full_response:
                fallback_msg = "FRIDAY Cyber Pro standing by. State your target or directive."
                full_response.append(fallback_msg)
                yield _sse("chunk", json.dumps({"text": fallback_msg}))

            yield _sse("done", json.dumps({"text": ""}))

    except HTTPException as exc:
        logger.warning("Inference governor rejection: %s", exc.detail)
        msg = exc.detail if isinstance(exc.detail, str) else exc.detail.get("message", "Service temporarily overloaded.")
        yield _sse("error", json.dumps({"message": msg}))

    except httpx.TimeoutException:
        logger.error("FRIDAY request timed out")
        yield _sse("error", json.dumps({"message": "FRIDAY took too long to respond. Please try again."}))

    except httpx.ConnectError:
        logger.error("Cannot connect to FRIDAY inference backend at %s", get_settings().ollama_base_url)
        yield _sse(
            "error",
            json.dumps({"message": "FRIDAY is temporarily unreachable. Server connection issue."}),
        )

    except httpx.HTTPStatusError as exc:
        logger.error("FRIDAY backend returned HTTP %d", exc.response.status_code)
        yield _sse(
            "error",
            json.dumps({"message": "FRIDAY neural engine encountered an issue. Please retry."}),
        )

    except Exception as exc:
        logger.exception("Unexpected streaming error: %s", exc)
        yield _sse("error", json.dumps({"message": "FRIDAY encountered an unexpected error. Please try again."}))

    finally:
        if user_db_task is not None:
            try:
                await user_db_task
            except Exception as exc:
                logger.warning("Failed awaiting user db persistence: %s", exc)

        if conversation_id and full_response:
            assistant_text = _sanitize_response("".join(full_response))
            try:
                await asyncio.to_thread(
                    _persist_assistant_message_sync,
                    conversation_id,
                    assistant_text,
                )
            except Exception as exc:
                logger.warning("Failed to persist assistant message: %s", exc)


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/api/models", response_model=ModelListResponse, tags=["Models"])
async def list_models(user: dict = Depends(get_current_user)) -> ModelListResponse:
    """
    Return list of allowlisted models available to authenticated operators.
    Includes user-friendly display metadata and the active default model.
    """
    settings = get_settings()
    return ModelListResponse(
        models=get_available_models(),
        default=settings.ollama_model,
    )


@router.post("/api/chat", tags=["Chat"])
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    """
    Main chat endpoint (Protected: requires valid Firebase Authentication).
    - stream=true  → SSE text/event-stream
    - stream=false → JSON application/json
    conversation_id is optional; when supplied, messages are persisted to SQLite.

    Quick Response Router runs first: simple conversational intents are answered
    locally without an Ollama call. All other requests fall through to the full
    Layout B + Ollama path unchanged.
    """
    if not isinstance(user, dict):
        user = {"id": "test_operator", "email": "operator@test.local", "name": "Test Operator"}
    user_id = user.get("id")

    # ── Subscription & Access Gate ───────────────────────────────────────────
    # Determine the model being requested
    _requested_model = request.model or get_settings().ollama_model

    # Get the user's subscription tier
    _tier = get_user_model_tier(user_id) if user_id else "free"

    # Model gating & usage enforcement:
    # 1. Free tier: 5 chats per day across BOTH models (Jr Hacker + Advanced Pentester).
    # 2. Jr Hacker tier (model1): 50 chats/day on Model 1 only; Model 2 requires Advanced Pentester.
    # 3. Advanced Pentester tier (model2): unlimited access to both models.
    if _tier == "free":
        if user_id:
            check_and_increment_usage(user_id)  # raises HTTP 429 if 5 chats/day limit exceeded
    elif _tier == "model1":
        if _requested_model == MODEL_2_ID:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "model_access_denied",
                    "message": "friday Cyber Pro requires an active subscription.",
                    "upgrade_required": True,
                    "required_tier": "model2",
                },
            )
        if user_id:
            check_and_increment_model1_usage(user_id)  # raises HTTP 429 if 50 chats/day limit exceeded
    else:
        # model2 or paid tier with full access to both models
        if user_id:
            track_usage(user_id)

    # Extract the last user message (needed for both routing and persistence)
    user_content = next(
        (m.content for m in reversed(request.messages) if m.role == "user"), ""
    )

    # ── Quick Response Router ────────────────────────────────────────────────
    quick_response = _quick_route(user_content, request.model)
    if quick_response is not None:
        if request.stream:
            return StreamingResponse(
                _quick_stream_generator(quick_response, request.conversation_id, user_content, user_id=user_id),
                media_type="text/event-stream",
                headers={
                    "X-Accel-Buffering": "no",
                    "Cache-Control": "no-cache",
                },
            )
        # Persist non-streaming quick response in thread pool
        if request.conversation_id:
            await asyncio.to_thread(
                _persist_quick_turn_sync,
                request.conversation_id,
                user_id,
                user_content,
                quick_response,
            )
        display_model = "friday Cyber Pro"
        return ChatResponse(
            content=quick_response,
            model=display_model,
            conversation_id=request.conversation_id,
        )

    # ── Full Ollama path (Layout B) ──────────────────────────────────────────
    messages, model = _prepare_messages(request)

    if request.stream:
        return StreamingResponse(
            _stream_generator(messages, model, request.conversation_id, user_content, user_id=user_id),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )

    # Non-streaming path
    is_openrouter = any(m["id"] == model for m in OPENROUTER_MODELS) or model.startswith("openrouter/")
    try:
        async with acquire_inference_capacity(user_id):
            if is_openrouter:
                raw_content = await openrouter_complete(messages, model)
            else:
                raw_content = await chat_complete(messages, model)
            content = _sanitize_response(raw_content)

        # Persist non-streaming turn in thread pool
        if request.conversation_id:
            await asyncio.to_thread(
                _persist_quick_turn_sync,
                request.conversation_id,
                user_id,
                user_content,
                content,
            )

        display_model = "friday Cyber Pro"
        return ChatResponse(
            content=content,
            model=display_model,
            conversation_id=request.conversation_id,
        )

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="FRIDAY took too long to respond. Please try again.")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="FRIDAY is temporarily unreachable. Server connection issue.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="FRIDAY neural engine encountered an issue. Please retry.",
        )
    except Exception as exc:
        logger.exception("Unexpected error in non-streaming chat: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error.")
