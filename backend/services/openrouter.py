"""
FRIDAY AI — OpenRouter Service (High-Performance Cloud GPU Inference)
Enables ultra-fast (80-120 tokens/sec) uncensored model inference
via enterprise Nvidia H100/A100 clusters.
"""

import json
import logging
from typing import AsyncIterator, Optional
import httpx

from config import get_settings

logger = logging.getLogger(__name__)

# Reusable HTTP client for OpenRouter connection pooling
_openrouter_client: Optional[httpx.AsyncClient] = None


def get_openrouter_client() -> httpx.AsyncClient:
    """Return pooled HTTP client for OpenRouter API requests."""
    global _openrouter_client
    if _openrouter_client is None or _openrouter_client.is_closed:
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=120.0,
        )
        _openrouter_client = httpx.AsyncClient(timeout=120.0, limits=limits)
    return _openrouter_client


async def close_openrouter_client():
    """Gracefully close the OpenRouter HTTP client on shutdown."""
    global _openrouter_client
    if _openrouter_client is not None and not _openrouter_client.is_closed:
        await _openrouter_client.aclose()
        _openrouter_client = None


def is_openrouter_configured() -> bool:
    """Return True if an OpenRouter API key has been provided in settings."""
    settings = get_settings()
    return bool(settings.openrouter_api_key and settings.openrouter_api_key.strip())


async def openrouter_stream(
    messages: list[dict],
    model: str,
) -> AsyncIterator[str]:
    """
    Stream chat completion tokens from OpenRouter API.
    Yields plain text chunks as they arrive.
    """
    settings = get_settings()
    if not is_openrouter_configured():
        yield "OpenRouter API key is not configured. Please add OPENROUTER_API_KEY to your server .env file."
        return

    # Clean messages for standard OpenAI format (role: system, user, assistant)
    cleaned_messages = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role in ("system", "user", "assistant") and content:
            cleaned_messages.append({"role": role, "content": content})

    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key.strip()}",
        "HTTP-Referer": "https://friday-ai.vercel.app",
        "X-Title": "FRIDAY Cyber AI",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": cleaned_messages,
        "stream": True,
        "temperature": 0.6,
        "max_tokens": 1500,
    }

    logger.info("Streaming OpenRouter | model=%s | turns=%d", model, len(cleaned_messages))

    client = get_openrouter_client()
    async with client.stream(
        "POST",
        url,
        headers=headers,
        json=payload,
        timeout=120.0,
    ) as response:
        if response.status_code != 200:
            error_body = await response.aread()
            logger.error("OpenRouter error HTTP %d: %s", response.status_code, error_body.decode(errors="replace"))
            yield f"OpenRouter API returned HTTP {response.status_code}. Please verify your API key or model availability."
            return

        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        # Normal response content
                        text = delta.get("content", "")
                        # Reasoning content fallback for R1 / thinking models
                        if not text:
                            text = delta.get("reasoning_content", "") or delta.get("reasoning", "")
                        if text:
                            yield text
                except json.JSONDecodeError:
                    continue


async def openrouter_complete(
    messages: list[dict],
    model: str,
) -> str:
    """Non-streaming variant for OpenRouter completions."""
    parts = []
    async for chunk in openrouter_stream(messages, model):
        parts.append(chunk)
    return "".join(parts)

