import asyncio
from fastapi import APIRouter
from schemas import HealthResponse
from services.ollama import check_ollama_reachable
from services.db import check_db_reachable
from config import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
@router.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Returns the operational status of the backend, Ollama connection, and database.
    Safe to call from a browser or load balancer without authentication.
    """
    settings = get_settings()
    ollama_ok = await check_ollama_reachable()
    db_ok = await asyncio.to_thread(check_db_reachable)

    overall_ok = ollama_ok and db_ok
    return HealthResponse(
        status="ok" if overall_ok else "degraded",
        ollama_reachable=ollama_ok,
        database_reachable=db_ok,
        model=settings.ollama_model,
        version="2.0.0",
    )
