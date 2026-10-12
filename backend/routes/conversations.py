"""
FRIDAY AI — Conversation History Routes
GET    /api/conversations          — list conversations for current user (latest first)
POST   /api/conversations          — create a new conversation for current user
GET    /api/conversations/{id}     — get a conversation with its messages
PATCH  /api/conversations/{id}     — rename a conversation
DELETE /api/conversations/{id}     — delete a conversation and all messages
"""

import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field

from routes.auth import get_current_user
from services.db import (
    create_conversation,
    get_conversation,
    list_conversations,
    update_conversation_title,
    delete_conversation,
    get_messages,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


# ─── Request / Response models ────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    id: str | None = Field(default=None, description="Optional client-supplied UUID")
    title: str = Field(default="New Conversation", max_length=120)


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)


def _get_conversation_with_messages_sync(conv_id: str, user_id: str | None) -> dict | None:
    """Retrieve conversation and its full message list in a single worker thread."""
    conv = get_conversation(conv_id, user_id=user_id)
    if not conv:
        return None
    messages = get_messages(conv_id)
    return {**conv, "messages": messages}


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("")
async def list_convs(user: dict = Depends(get_current_user)):
    """List conversations ordered by most recently updated, scoped to current operator."""
    user_id = user["id"] if isinstance(user, dict) else None
    return await asyncio.to_thread(list_conversations, 100, user_id)


@router.post("", status_code=201)
async def create_conv(body: ConversationCreate, user: dict = Depends(get_current_user)):
    """Create a new conversation. Scoped to the current operator."""
    user_id = user["id"] if isinstance(user, dict) else None
    return await asyncio.to_thread(create_conversation, body.id, body.title, user_id)


@router.get("/{conv_id}")
async def get_conv(conv_id: str, user: dict = Depends(get_current_user)):
    """Return a conversation and its full message history."""
    user_id = user["id"] if isinstance(user, dict) else None
    conv_data = await asyncio.to_thread(_get_conversation_with_messages_sync, conv_id, user_id)
    if not conv_data:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conv_data


@router.patch("/{conv_id}")
async def rename_conv(conv_id: str, body: ConversationRename, user: dict = Depends(get_current_user)):
    """Rename a conversation."""
    user_id = user["id"] if isinstance(user, dict) else None
    existing = await asyncio.to_thread(get_conversation, conv_id, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    await asyncio.to_thread(update_conversation_title, conv_id, body.title, user_id)
    return {"id": conv_id, "title": body.title}


@router.delete("/{conv_id}", status_code=204)
async def delete_conv(conv_id: str, user: dict = Depends(get_current_user)):
    """Delete a conversation and all its messages."""
    user_id = user["id"] if isinstance(user, dict) else None
    deleted = await asyncio.to_thread(delete_conversation, conv_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")

