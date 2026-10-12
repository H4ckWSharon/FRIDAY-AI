"""
FRIDAY AI — Ollama Service
All communication with the Ollama server lives here.
The rest of the app never calls Ollama directly; it always goes through this module.
"""

import logging
import json
import asyncio
from typing import AsyncIterator, Optional
from contextlib import asynccontextmanager

import httpx
from fastapi import HTTPException

from config import get_settings

logger = logging.getLogger(__name__)

# ─── Inference Capacity Governor ─────────────────────────────────────────────
_inference_semaphore: Optional[asyncio.Semaphore] = None
_user_active_inferences: dict[str, int] = {}
_waiting_count: int = 0
_governor_lock = asyncio.Lock()


def get_inference_semaphore() -> asyncio.Semaphore:
    global _inference_semaphore
    if _inference_semaphore is None:
        settings = get_settings()
        _inference_semaphore = asyncio.Semaphore(settings.max_concurrent_inferences)
    return _inference_semaphore


@asynccontextmanager
async def acquire_inference_capacity(user_id: Optional[str] = None):
    """
    Guarantees bounded CPU inference capacity, prevents server starvation,
    enforces per-user generation concurrency, and provides instant backpressure.
    """
    global _waiting_count
    settings = get_settings()
    uid = user_id or "anonymous"

    async with _governor_lock:
        active_for_user = _user_active_inferences.get(uid, 0)
        if active_for_user >= settings.max_user_concurrent_inferences:
            raise HTTPException(
                status_code=429,
                detail="You have another active generation in progress. Please wait for it to complete.",
            )

        sem = get_inference_semaphore()
        if _waiting_count >= settings.max_inference_queue:
            raise HTTPException(
                status_code=503,
                detail="FRIDAY neural engine is currently operating at peak capacity. Please retry shortly.",
                headers={"Retry-After": "5"},
            )
        _waiting_count += 1

    try:
        await sem.acquire()
    except Exception:
        async with _governor_lock:
            _waiting_count = max(0, _waiting_count - 1)
        raise

    async with _governor_lock:
        _waiting_count = max(0, _waiting_count - 1)
        _user_active_inferences[uid] = _user_active_inferences.get(uid, 0) + 1

    try:
        yield
    finally:
        sem.release()
        async with _governor_lock:
            current = _user_active_inferences.get(uid, 1) - 1
            if current <= 0:
                _user_active_inferences.pop(uid, None)
            else:
                _user_active_inferences[uid] = current


# ─── Shared HTTP Client ──────────────────────────────────────────────────────
_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """
    Return a shared httpx.AsyncClient with connection pooling.
    Reusing connections through the SSH tunnel cuts round-trip handshake latency.
    """
    global _client
    if _client is None or _client.is_closed:
        settings = get_settings()
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=300.0,
        )
        _client = httpx.AsyncClient(timeout=settings.ollama_timeout, limits=limits)
    return _client


async def close_http_client():
    """Close the shared HTTP client gracefully on shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None


# ─── Internal helpers ────────────────────────────────────────────────────────

def _ollama_url(path: str) -> str:
    """Build a full Ollama API URL from a relative path."""
    base = get_settings().ollama_base_url.rstrip("/")
    return f"{base}{path}"


def _build_payload(messages: list[dict], model: str, stream: bool) -> dict:
    """Construct the JSON body for Ollama's /api/chat endpoint."""
    return {
        "model": model,
        "messages": messages,
        "stream": stream,
        "keep_alive": -1,  # Keep model permanently in VRAM, eliminating 20s+ cold reloads
        "options": {
            # Tuned sampling parameters for faster, sharper, and bounded generation
            "temperature": 0.6,
            "top_p": 0.9,
            "top_k": 40,
            "num_predict": 2048,
        },
    }


# ─── Public API ─────────────────────────────────────────────────────────────

async def check_ollama_reachable() -> bool:
    """
    Return True if Ollama is responding at its base URL.
    Used by the /health endpoint.
    """
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(_ollama_url("/api/tags"))
            return response.status_code == 200
    except Exception as exc:
        logger.warning("Ollama health check failed: %s", exc)
        return False


async def warmup_model(model: str) -> bool:
    """
    Send a minimal 1-token query to warm up the model and keep it resident in VRAM.
    Fired on backend startup in background so the user never experiences cold-start lag.
    """
    try:
        client = get_http_client()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False,
            "keep_alive": -1,
            "options": {"num_predict": 1},
        }
        res = await client.post(_ollama_url("/api/chat"), json=payload, timeout=30.0)
        logger.info("Ollama model warmup completed: status=%d", res.status_code)
        return res.status_code == 200
    except Exception as exc:
        logger.warning("Ollama model warmup skipped/failed: %s", exc)
        return False


async def chat_stream(
    messages: list[dict],
    model: str,
) -> AsyncIterator[str]:
    """
    Send a chat request to Ollama and yield response text chunks as they arrive.

    Each yielded value is a plain text chunk (not JSON) — the route layer wraps
    these into SSE format before sending to the browser.

    Raises:
        httpx.TimeoutException  — if Ollama takes too long to start responding
        httpx.HTTPStatusError   — if Ollama returns a non-2xx status
        Exception               — other network failures
    """
    payload = _build_payload(messages, model, stream=True)

    logger.info(
        "Streaming chat | model=%s | turns=%d", model, len(messages)
    )

    client = get_http_client()
    async with client.stream(
        "POST",
        _ollama_url("/api/chat"),
        json=payload,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("Non-JSON line from Ollama: %r", line)
                continue

            # Ollama streams one JSON object per line.
            # The text content lives at chunk["message"]["content"].
            text = chunk.get("message", {}).get("content", "")
            if text:
                yield text

            # "done": true signals end of stream
            if chunk.get("done"):
                break


async def chat_complete(
    messages: list[dict],
    model: str,
) -> str:
    """
    Non-streaming variant. Collects all chunks and returns the full response.
    Used when stream=false is requested.
    """
    parts: list[str] = []
    async for chunk in chat_stream(messages, model):
        parts.append(chunk)
    return "".join(parts)
