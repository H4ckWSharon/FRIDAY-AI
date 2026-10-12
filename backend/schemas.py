"""
FRIDAY AI — Pydantic Schemas
Defines the shape of every request and response that crosses the API boundary.
Using Pydantic means FastAPI validates inputs automatically before our code runs.
"""

from pydantic import BaseModel, Field
from typing import Literal


# ─── Chat Request ───────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    """A single turn in the conversation history."""
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """
    Sent by the browser to POST /api/chat.
    'messages' is the full conversation so far (oldest first).
    'conversation_id' links this request to a stored conversation for persistence.
    """
    messages: list[ChatMessage] = Field(..., min_length=1)
    conversation_id: str | None = Field(
        default=None,
        description="UUID of the conversation to persist messages to. "
                    "If omitted, messages are not persisted.",
    )
    model: str | None = Field(
        default=None,
        description="Override the default model. Leave null to use server default.",
    )
    stream: bool = Field(
        default=True,
        description="If true, response is a streaming SSE. If false, returns JSON.",
    )


# ─── Chat Response (non-streaming only) ─────────────────────────────────────

class ChatResponse(BaseModel):
    """Returned by POST /api/chat when stream=false."""
    role: Literal["assistant"] = "assistant"
    content: str
    model: str
    conversation_id: str | None = None


# ─── Health ─────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    ollama_reachable: bool
    model: str
    version: str = "1.0.0"


# ─── Models ─────────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    tag: str
    is_default: bool = False


class ModelListResponse(BaseModel):
    models: list[ModelInfo]
    default: str
