"""
FRIDAY AI — FastAPI Application Entry Point
Run with: uvicorn main:app --reload  (from inside the backend/ directory)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.conversations import router as conversations_router
from routes.subscription import router as subscription_router
from routes.admin import router as admin_router
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
    from services.openrouter import close_openrouter_client
    if not (settings.openrouter_api_key and settings.openrouter_api_key.strip()):
        asyncio.create_task(warmup_model(settings.ollama_model))

    yield

    await close_http_client()
    await close_openrouter_client()
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

import uuid
import time
import asyncio
from collections import defaultdict, deque
from fastapi.responses import JSONResponse

# Max allowable request payload size: 10 MB
MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024

# Global IP Sliding-Window Rate Limiter
RATE_LIMIT_MAX_REQUESTS = 180
RATE_LIMIT_WINDOW_SECONDS = 60.0
_IP_TIMESTAMPS: dict[str, deque] = defaultdict(deque)
_RATE_LIMIT_LOCK = asyncio.Lock()


def get_client_ip(request) -> str:
    """Extract real client IP with support for Cloudflare Tunnel and proxy headers."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


@app.middleware("http")
async def security_and_telemetry_middleware(request, call_next):
    req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    request.state.request_id = req_id

    # 0. Global Maintenance Lockdown Gate
    if getattr(settings, "maintenance_mode", True):
        p = request.url.path
        if p.startswith("/health"):
            return JSONResponse(
                status_code=200,
                content={
                    "status": "maintenance",
                    "detail": "Server maintenance active. All systems will resume tomorrow.",
                    "resuming": "tomorrow",
                },
                headers={"X-Request-ID": req_id},
            )
        if p.startswith("/api/"):
            return JSONResponse(
                status_code=503,
                content={
                    "status": "maintenance",
                    "error": "maintenance_mode_active",
                    "detail": "Website Temporarily Locked. Scheduled maintenance active across all nodes. Chat sessions and operator consoles are locked. Resuming tomorrow.",
                    "message": "Website Temporarily Locked. Scheduled maintenance active across all nodes. Chat sessions and operator consoles are locked. Resuming tomorrow.",
                    "resuming": "tomorrow",
                },
                headers={"X-Request-ID": req_id, "Retry-After": "86400"},
            )

    # 1. Payload size check from Content-Length header
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Payload too large. Maximum request size is 10MB."},
                    headers={"X-Request-ID": req_id},
                )
        except ValueError:
            pass

    # 2. IP-based sliding-window rate limit
    client_ip = get_client_ip(request)
    now = time.time()
    remaining = RATE_LIMIT_MAX_REQUESTS

    # Exempt internal test harness clients and loopback requests without proxy headers to allow rapid automated testing
    is_internal_localhost = client_ip in ("testclient", "127.0.0.1") and not request.headers.get("CF-Connecting-IP") and not request.headers.get("X-Forwarded-For")
    if not is_internal_localhost:
        async with _RATE_LIMIT_LOCK:
            timestamps = _IP_TIMESTAMPS[client_ip]
            cutoff = now - RATE_LIMIT_WINDOW_SECONDS
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Rate limit exceeded. Please wait before retrying."},
                    headers={
                        "X-Request-ID": req_id,
                        "Retry-After": "30",
                        "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            timestamps.append(now)
            remaining = max(0, RATE_LIMIT_MAX_REQUESTS - len(timestamps))

            # Periodic memory cleanup if many tracked IPs accumulate
            if len(_IP_TIMESTAMPS) > 5000:
                empty_keys = [ip for ip, dq in _IP_TIMESTAMPS.items() if not dq]
                for k in empty_keys[:1000]:
                    _IP_TIMESTAMPS.pop(k, None)

    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Attach observability headers
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    # Attach OWASP security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# CORS — allow the browser to call this backend safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
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
app.include_router(admin_router)



# ─── Frontend Delivery (React Production) ───────────────────────────────────
dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
dist_assets_dir = os.path.join(dist_dir, "assets")
if os.path.exists(dist_assets_dir):
    app.mount("/assets", StaticFiles(directory=dist_assets_dir), name="assets")

@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
@app.get("/app", include_in_schema=False)
async def serve_index():
    react_index = os.path.join(dist_dir, "index.html")
    if os.path.exists(react_index):
        resp = FileResponse(react_index, media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
    if os.path.exists(index_path):
        resp = FileResponse(index_path, media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    return {"status": "ok", "message": "FRIDAY AI Engine Operational"}
