"""
FRIDAY AI — FastAPI Application Entry Point
Run with: uvicorn main:app --reload  (from inside the backend/ directory)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.conversations import router as conversations_router
from routes.subscription import router as subscription_router
from services.db import init_db

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.is_development else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("friday")


# ─── Lifespan (startup / shutdown hooks) ──────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise database schema (idempotent: PostgreSQL or SQLite)
    init_db()
    logger.info("═══════════════════════════════════════════════════")
    logger.info("  FRIDAY AI Backend  |  %s", settings.app_env.upper())
    logger.info("  Ollama URL         : %s", settings.ollama_base_url)
    logger.info("  Model              : %s", settings.ollama_model)
    logger.info("  DB                 : %s", "PostgreSQL (Supabase)" if settings.database_url else settings.resolved_db_path)
    logger.info("  Max history turns  : %d", settings.max_history_turns)
    logger.info("  CORS Origins       : %s", settings.cors_origins_list)
    logger.info("═══════════════════════════════════════════════════")

    # Pre-warm model in background so user's first question has 0s load latency
    import asyncio
    from services.ollama import warmup_model, close_http_client
    asyncio.create_task(warmup_model(settings.ollama_model))

    yield

    await close_http_client()
    logger.info("FRIDAY AI backend shutting down.")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FRIDAY AI",
    description="Black Hat Offensive Security Assistant",
    version="2.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Security headers middleware for production
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# CORS — allow the browser to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(subscription_router)
