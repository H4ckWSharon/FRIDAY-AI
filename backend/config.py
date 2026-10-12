"""
FRIDAY AI — Configuration
Reads settings from the .env file. All secrets stay server-side.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional, Any
import os


# ─── Allowlisted Models Registry ─────────────────────────────────────────────
# Strict allowlist of models available in Ollama.
# Arbitrary client-provided model IDs are rejected at the API boundary.
AVAILABLE_MODELS: list[dict[str, Any]] = [
    {
        "id": "hf.co/mradermacher/Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated-i1-GGUF:Q4_K_M",
        "name": "Friday v1 The Jr Hacker",
        "description": "AI Junior Pentester & Security Mentor",
        "tag": "Jr Hacker (Default)",
        "is_default": True,
    },
    {
        "id": "huihui_ai/baronllm-abliterated:latest",
        "name": "Friday v1 The Advanced Pentester",
        "description": "Advanced Cyber Security & Penetration Testing Engine",
        "tag": "Advanced Pentester",
        "is_default": False,
    },
]

ALLOWED_MODEL_IDS: set[str] = {m["id"] for m in AVAILABLE_MODELS}


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env file."""

    # Ollama connection
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:latest"
    ollama_timeout: float = 120.0

    # Server
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # CORS — browser origins that may talk to this backend
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500,null"

    # Application environment
    app_env: str = "development"

    # Context window management — max user+assistant turn PAIRS to send to Ollama.
    # Keeps token usage bounded on long conversations.
    # System prompt is always included and does NOT count toward this limit.
    max_history_turns: int = 10

    # Database connection URL (PostgreSQL / Supabase / Neon)
    # If set, PostgreSQL is used for persistence. If None/empty, SQLite is used.
    database_url: Optional[str] = None

    # SQLite database path for conversation persistence.
    # Relative paths are resolved from the backend/ directory.
    db_path: str = "friday.db"

    # Firebase Authentication & Admin configuration
    firebase_project_id: str = "friday-ai-27647"
    firebase_service_account_path: Optional[str] = None
    firebase_service_account_json: Optional[str] = None

    # Razorpay Payment Gateway
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a Python list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def resolved_db_path(self) -> str:
        """Resolve db_path relative to the backend directory."""
        if os.path.isabs(self.db_path):
            return self.db_path
        return os.path.join(os.path.dirname(__file__), self.db_path)

    @property
    def resolved_firebase_service_account_path(self) -> Optional[str]:
        """Resolve service account JSON path if provided."""
        if not self.firebase_service_account_path:
            return None
        if os.path.isabs(self.firebase_service_account_path):
            return self.firebase_service_account_path
        return os.path.join(os.path.dirname(__file__), self.firebase_service_account_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()


def get_allowed_model_ids() -> set[str]:
    """Return set of valid model IDs including any custom configured default."""
    settings = get_settings()
    allowed = set(ALLOWED_MODEL_IDS)
    if settings.ollama_model:
        allowed.add(settings.ollama_model)
    return allowed


def get_available_models() -> list[dict[str, Any]]:
    """Return list of models with current default marked accurately."""
    settings = get_settings()
    default_id = settings.ollama_model
    results = []
    for m in AVAILABLE_MODELS:
        item = dict(m)
        item["is_default"] = (item["id"] == default_id)
        results.append(item)
    return results
