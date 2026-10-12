"""
FRIDAY AI — Health Route
GET /health — tells the frontend (and any monitoring) whether the backend
and Ollama are both reachable.
"""

from fastapi import APIRouter
from schemas import HealthResponse
from services.ollama import check_ollama_reachable
from config import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
@router.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Returns the operational status of the backend and its Ollama connection.
    Safe to call from a browser without authentication.
    """
    settings = get_settings()
    ollama_ok = await check_ollama_reachable()

    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama_reachable=ollama_ok,
        model=settings.ollama_model,
    )
