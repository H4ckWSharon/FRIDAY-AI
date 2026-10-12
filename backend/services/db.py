"""
FRIDAY AI — SQLite Persistence Service
Stores user accounts, conversation metadata, and messages using Python's built-in sqlite3.
No additional dependencies. WAL mode keeps concurrent reads safe.

Schema
------
users
  id            TEXT  PRIMARY KEY  (UUID or 'usr_...')
  email         TEXT  UNIQUE NOT NULL
  name          TEXT  NOT NULL
  avatar        TEXT
  password_hash TEXT               (PBKDF2-HMAC-SHA256, null for OAuth)
  provider      TEXT  NOT NULL     ('local' | 'google')
  created_at    TEXT  NOT NULL     (ISO-8601 UTC)

conversations
  id          TEXT  PRIMARY KEY  (UUID, assigned by client or generated here)
  user_id     TEXT               (REFERENCES users(id) ON DELETE CASCADE)
  title       TEXT               (derived from first user message, truncated)
  created_at  TEXT               (ISO-8601 UTC)
  updated_at  TEXT               (ISO-8601 UTC)

messages
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  conv_id     TEXT    NOT NULL  REFERENCES conversations(id) ON DELETE CASCADE
  role        TEXT    NOT NULL  ('user' | 'assistant' | 'system')
  content     TEXT    NOT NULL
  created_at  TEXT    NOT NULL  (ISO-8601 UTC)
"""

import os
import sqlite3
import uuid
import logging
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Any, Generator, Optional

try:
    import psycopg2
    from psycopg2 import pool as pg_pool
    from psycopg2.extras import RealDictCursor
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False

from config import get_settings

logger = logging.getLogger(__name__)


# ─── Dual Database Adapters ───────────────────────────────────────────────────

_pg_connection_pool: Optional[Any] = None


def is_postgres() -> bool:
    """Return True if a PostgreSQL connection string is configured."""
    url = os.environ.get("DATABASE_URL")
    if url is None:
        url = get_settings().database_url
    return bool(url and url.strip().startswith(("postgres://", "postgresql://")))


class PgCursorAdapter:
    """Adapts psycopg2 cursor to match sqlite3 cursor conventions."""
    def __init__(self, cur):
        self._cur = cur
        self.lastrowid = None

    @property
    def rowcount(self):
        return self._cur.rowcount

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in row.items()}

    def fetchall(self):
        rows = self._cur.fetchall()
        return [{k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in row.items()} for row in rows]

    def __iter__(self):
        for row in self._cur:
            yield {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in row.items()}


class PgConnectionAdapter:
    """Adapts a psycopg2 connection to match sqlite3 connection conventions."""
    def __init__(self, pg_conn, pool=None):
        self._conn = pg_conn
        self._pool = pool

    def execute(self, sql: str, params: tuple = ()):
        # Ignore SQLite specific pragmas
        if sql.strip().upper().startswith("PRAGMA"):
            class DummyCursor:
                rowcount = 0
                lastrowid = None
                def fetchone(self): return None
                def fetchall(self): return []
            return DummyCursor()

        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        converted_sql = sql.replace("?", "%s")

        # Capture lastrowid for INSERT INTO messages
        if "INSERT INTO messages" in converted_sql and "RETURNING" not in converted_sql.upper():
            converted_sql = converted_sql.rstrip("; ") + " RETURNING id;"
            cur.execute(converted_sql, params)
            adapter = PgCursorAdapter(cur)
            row = cur.fetchone()
            if row:
                adapter.lastrowid = row["id"]
            return adapter

        cur.execute(converted_sql, params)
        return PgCursorAdapter(cur)

    def executescript(self, script: str):
        with self._conn.cursor() as cur:
            cur.execute(script)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._pool:
            try:
                self._pool.putconn(self._conn)
            except Exception:
                pass
        else:
            self._conn.close()


def _get_pg_pool() -> Any:
    global _pg_connection_pool
    if not _PSYCOPG2_AVAILABLE:
        raise RuntimeError("psycopg2 is required for PostgreSQL connections. Install with: pip install psycopg2-binary")
    if _pg_connection_pool is None:
        url = get_settings().database_url
        _pg_connection_pool = pg_pool.ThreadedConnectionPool(minconn=1, maxconn=15, dsn=url)
    return _pg_connection_pool


# ─── Connection ───────────────────────────────────────────────────────────────

def _connect() -> Any:
    if is_postgres():
        try:
            pool = _get_pg_pool()
            raw_conn = pool.getconn()
            return PgConnectionAdapter(raw_conn, pool=pool)
        except Exception as exc:
            logger.warning("PostgreSQL connection error: %s. Falling back to local SQLite.", exc)

    # SQLite fallback
    db_path = get_settings().resolved_db_path
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db() -> Generator[Any, None, None]:
    """Yield a connection and commit/rollback automatically."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Initialise schema ────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't already exist and apply migrations. Safe to call multiple times."""
    if is_postgres():
        try:
            with get_db() as conn:
                if isinstance(conn, PgConnectionAdapter):
                    conn.executescript("""
                        CREATE TABLE IF NOT EXISTS users (
                            id            TEXT PRIMARY KEY,
                            email         TEXT UNIQUE NOT NULL,
                            name          TEXT NOT NULL,
                            avatar        TEXT,
                            password_hash TEXT,
                            provider      TEXT NOT NULL DEFAULT 'google',
                            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );

                        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

                        CREATE TABLE IF NOT EXISTS conversations (
                            id         TEXT PRIMARY KEY,
                            user_id    TEXT,
                            title      TEXT NOT NULL DEFAULT 'New Conversation',
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE
                        );

                        CREATE TABLE IF NOT EXISTS messages (
                            id         BIGSERIAL PRIMARY KEY,
                            conv_id    TEXT NOT NULL,
                            role       TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                            content    TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            FOREIGN KEY (conv_id) REFERENCES conversations(id) ON DELETE CASCADE
                        );

                        CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
                        CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conv_id);

                        CREATE TABLE IF NOT EXISTS subscriptions (
                            id                  TEXT PRIMARY KEY,
                            user_id             TEXT NOT NULL REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE,
                            plan_id             TEXT NOT NULL,
                            status              TEXT NOT NULL DEFAULT 'active',
                            model_tier          TEXT NOT NULL DEFAULT 'free',
                            razorpay_order_id   TEXT,
                            razorpay_payment_id TEXT,
                            razorpay_sub_id     TEXT,
                            starts_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            expires_at          TIMESTAMPTZ,
                            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );

                        CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
                        CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

                        CREATE TABLE IF NOT EXISTS daily_usage (
                            id      BIGSERIAL PRIMARY KEY,
                            user_id TEXT NOT NULL REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE,
                            date    TEXT NOT NULL,
                            count   INTEGER NOT NULL DEFAULT 0,
                            UNIQUE(user_id, date)
                        );

                        CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON daily_usage(user_id, date);
                    """)
                    logger.info("PostgreSQL database initialized on Supabase.")
                    return
        except Exception as exc:
            logger.warning("PostgreSQL init_db failed: %s. Falling back to SQLite initialization.", exc)

    # SQLite initialization
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                name          TEXT NOT NULL,
                avatar        TEXT,
                password_hash TEXT,
                provider      TEXT NOT NULL DEFAULT 'local',
                created_at    TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                user_id    TEXT,
                title      TEXT NOT NULL DEFAULT 'New Conversation',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                conv_id    TEXT    NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                FOREIGN KEY (conv_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv_id ON messages(conv_id);

            CREATE TABLE IF NOT EXISTS subscriptions (
                id                  TEXT PRIMARY KEY,
                user_id             TEXT NOT NULL,
                plan_id             TEXT NOT NULL,
                status              TEXT NOT NULL DEFAULT 'active',
                model_tier          TEXT NOT NULL DEFAULT 'free',
                razorpay_order_id   TEXT,
                razorpay_payment_id TEXT,
                razorpay_sub_id     TEXT,
                starts_at           TEXT NOT NULL,
                expires_at          TEXT,
                created_at          TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
            CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

            CREATE TABLE IF NOT EXISTS daily_usage (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date    TEXT NOT NULL,
                count   INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, date)
            );

            CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON daily_usage(user_id, date);
        """)

        # Migration: ensure user_id column exists if table existed previously without it
        try:
            cols = [row["name"] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()]
            if "user_id" not in cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
        except Exception as exc:
            logger.debug("Migration check note: %s", exc)

    logger.info("Database initialised at %s", get_settings().resolved_db_path)


# ─── Utilities ────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_title(first_user_content: str, max_len: int = 60) -> str:
    """Derive a readable title from the first user message."""
    clean = first_user_content.strip().replace("\n", " ")
    return clean[:max_len] + ("…" if len(clean) > max_len else "")


# ─── User CRUD ────────────────────────────────────────────────────────────────

def create_user(
    email: str,
    name: str,
    password_hash: Optional[str] = None,
    avatar: Optional[str] = None,
    provider: str = "local",
    user_id: Optional[str] = None,
) -> dict:
    """Create a new user. Returns dict representation of the user."""
    if not user_id:
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
    now = _now()
    normalized_email = email.strip().lower()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO users (id, email, name, avatar, password_hash, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, normalized_email, name.strip(), avatar, password_hash, provider, now),
        )
    return {
        "id": user_id,
        "email": normalized_email,
        "name": name.strip(),
        "avatar": avatar,
        "provider": provider,
        "created_at": now,
    }


def upsert_firebase_user(
    user_id: str,
    email: str,
    name: str,
    avatar: Optional[str] = None,
    provider: str = "google-firebase",
) -> dict:
    """
    Safely retrieve, update, or create a Firebase authenticated user.
    Handles email uniqueness conflicts by migrating legacy local user records
    to the verified Firebase UID as the stable identity.
    """
    normalized_email = email.strip().lower()
    clean_name = name.strip() if name else (normalized_email.split("@")[0].capitalize() if normalized_email else "Operator")
    now = _now()
    with get_db() as conn:
        # 1. Existing user with exact Firebase UID
        by_id = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if by_id:
            user_dict = dict(by_id)
            new_name = clean_name if clean_name else user_dict["name"]
            new_avatar = avatar if avatar is not None else user_dict["avatar"]
            if user_dict["name"] != new_name or user_dict["avatar"] != new_avatar or user_dict["provider"] != provider:
                conn.execute(
                    "UPDATE users SET name = ?, avatar = ?, provider = ? WHERE id = ?",
                    (new_name, new_avatar, provider, user_id),
                )
                user_dict["name"] = new_name
                user_dict["avatar"] = new_avatar
                user_dict["provider"] = provider
            return user_dict

        # 2. Existing user with the same email (e.g. legacy local account)
        by_email = conn.execute("SELECT * FROM users WHERE email = ?", (normalized_email,)).fetchone()
        if by_email:
            old_id = by_email["id"]
            new_name = clean_name if clean_name else by_email["name"]
            new_avatar = avatar if avatar is not None else by_email["avatar"]

            if old_id != user_id:
                try:
                    if is_postgres():
                        conn.execute(
                            "UPDATE users SET id = ?, name = ?, avatar = ?, provider = ? WHERE email = ?",
                            (user_id, new_name, new_avatar, provider, normalized_email),
                        )
                    else:
                        conn.execute("PRAGMA foreign_keys = OFF")
                        conn.execute("UPDATE conversations SET user_id = ? WHERE user_id = ?", (user_id, old_id))
                        conn.execute("UPDATE daily_usage SET user_id = ? WHERE user_id = ?", (user_id, old_id))
                        conn.execute("UPDATE subscriptions SET user_id = ? WHERE user_id = ?", (user_id, old_id))
                        conn.execute(
                            "UPDATE users SET id = ?, name = ?, avatar = ?, provider = ? WHERE email = ?",
                            (user_id, new_name, new_avatar, provider, normalized_email),
                        )
                        conn.execute("PRAGMA foreign_keys = ON")
                    migrated = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                    if migrated:
                        return dict(migrated)
                except Exception as exc:
                    logger.warning("Could not re-point user id from %s to %s (%s). Preserving existing user record.", old_id, user_id, exc)
                    conn.execute(
                        "UPDATE users SET name = ?, avatar = ?, provider = ? WHERE email = ?",
                        (new_name, new_avatar, provider, normalized_email),
                    )
                    preserved = conn.execute("SELECT * FROM users WHERE id = ?", (old_id,)).fetchone()
                    if preserved:
                        return dict(preserved)
            else:
                conn.execute(
                    "UPDATE users SET name = ?, avatar = ?, provider = ? WHERE id = ?",
                    (new_name, new_avatar, provider, user_id),
                )
                updated = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                if updated:
                    return dict(updated)

        # 3. Fresh user creation
        conn.execute(
            """
            INSERT INTO users (id, email, name, avatar, password_hash, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, normalized_email, clean_name, avatar, None, provider, now),
        )
        created = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(created)


def get_user_by_email(email: str) -> Optional[dict]:
    """Retrieve user by normalized email."""
    if not email:
        return None
    normalized_email = email.strip().lower()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (normalized_email,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Retrieve user by user_id."""
    if not user_id:
        return None
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def update_user_profile(user_id: str, name: Optional[str] = None, avatar: Optional[str] = None) -> Optional[dict]:
    """Update display name or avatar."""
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return None
        new_name = name.strip() if name else user["name"]
        new_avatar = avatar if avatar is not None else user["avatar"]
        conn.execute(
            "UPDATE users SET name = ?, avatar = ? WHERE id = ?",
            (new_name, new_avatar, user_id),
        )
        updated = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(updated) if updated else None


# ─── Conversation CRUD ───────────────────────────────────────────────────────

def create_conversation(
    conv_id: Optional[str] = None,
    title: str = "New Conversation",
    user_id: Optional[str] = None,
) -> dict:
    """Create a new conversation record, optionally linked to a user. Returns row dict."""
    if not conv_id:
        conv_id = str(uuid.uuid4())
    now = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conv_id, user_id, title, now, now),
        )
    return {
        "id": conv_id,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }


def check_db_reachable() -> bool:
    """Return True if the database is operational and responds to a ping query."""
    try:
        with get_db() as conn:
            row = conn.execute("SELECT 1 as alive").fetchone()
            return bool(row)
    except Exception as exc:
        logger.warning("Database health check ping failed: %s", exc)
        return False


def get_conversation(conv_id: str, user_id: Optional[str] = None) -> Optional[dict]:
    """Return a conversation row or None if not found or unauthorized."""
    with get_db() as conn:
        if user_id:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                (conv_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conv_id,)
            ).fetchone()
    return dict(row) if row else None


def list_conversations(limit: int = 100, user_id: Optional[str] = None) -> list[dict]:
    """Return conversations ordered by most recently updated."""
    with get_db() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def update_conversation_title(conv_id: str, title: str, user_id: Optional[str] = None) -> bool:
    """Update conversation title. Returns True if a row was updated."""
    with get_db() as conn:
        if user_id:
            cursor = conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (title, _now(), conv_id, user_id),
            )
        else:
            cursor = conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, _now(), conv_id),
            )
    return cursor.rowcount > 0


def delete_conversation(conv_id: str, user_id: Optional[str] = None) -> bool:
    """Delete a conversation and all its messages (CASCADE). Returns True if deleted."""
    with get_db() as conn:
        if user_id:
            cursor = conn.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?",
                (conv_id, user_id),
            )
        else:
            cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    return cursor.rowcount > 0


def touch_conversation(conv_id: str) -> None:
    """Update updated_at timestamp. Called after a message is appended."""
    with get_db() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_now(), conv_id),
        )


# ─── Message CRUD ────────────────────────────────────────────────────────────

def append_message(conv_id: str, role: str, content: str) -> int:
    """
    Append a message to a conversation. Returns the new message ID.
    Also touches the conversation's updated_at.
    """
    now = _now()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (conv_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, now),
        )
        msg_id = cursor.lastrowid
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id),
        )
    return msg_id


def get_messages(conv_id: str) -> list[dict]:
    """Return all messages for a conversation in chronological order."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conv_id = ? ORDER BY id ASC",
            (conv_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def set_conversation_title_from_first_message(conv_id: str, first_content: str) -> None:
    """Derive and save a title from the first user message if title is still default."""
    with get_db() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND title = 'New Conversation'",
            (_derive_title(first_content), _now(), conv_id),
        )


# ─── Subscription CRUD ────────────────────────────────────────────────────────

def get_active_subscription(user_id: str) -> Optional[dict]:
    """Return the user's current active subscription, or None if free tier."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM subscriptions
               WHERE user_id = ? AND status = 'active'
               AND (expires_at IS NULL OR expires_at > ?)
               ORDER BY created_at DESC LIMIT 1""",
            (user_id, _now()),
        ).fetchone()
    return dict(row) if row else None


def _ensure_user_exists(conn, user_id: str) -> None:
    """Ensure a user record exists to satisfy foreign key relationships."""
    try:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            conn.execute(
                """INSERT INTO users (id, email, name, provider, created_at)
                   VALUES (?, ?, ?, 'local', ?)""",
                (user_id, f"{user_id}@friday.sec", user_id, _now()),
            )
    except Exception as exc:
        logger.debug("Auto-ensuring user %s: %s", user_id, exc)


def create_subscription(
    user_id: str,
    plan_id: str,
    model_tier: str,
    expires_at: Optional[str],
    razorpay_order_id: Optional[str] = None,
    razorpay_payment_id: Optional[str] = None,
) -> dict:
    """Create (or replace) an active subscription for a user. Deactivates old subs first."""
    sub_id = f"sub_{uuid.uuid4().hex[:16]}"
    now = _now()
    with get_db() as conn:
        _ensure_user_exists(conn, user_id)
        # Expire any previously active subscription for this user
        conn.execute(
            "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        conn.execute(
            """INSERT INTO subscriptions
               (id, user_id, plan_id, status, model_tier,
                razorpay_order_id, razorpay_payment_id,
                starts_at, expires_at, created_at)
               VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)""",
            (sub_id, user_id, plan_id, model_tier,
             razorpay_order_id, razorpay_payment_id,
             now, expires_at, now),
        )
    return {
        "id": sub_id, "user_id": user_id, "plan_id": plan_id,
        "model_tier": model_tier, "status": "active",
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "starts_at": now, "expires_at": expires_at, "created_at": now,
    }


# ─── Daily Usage CRUD ────────────────────────────────────────────────────────

def get_daily_usage(user_id: str, date: str) -> int:
    """Return today's message count for a user (0 if no record)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT count FROM daily_usage WHERE user_id = ? AND date = ?",
            (user_id, date),
        ).fetchone()
    return int(row["count"]) if row else 0


def increment_daily_usage(user_id: str, date: str) -> int:
    """
    Atomically increment the daily message count for a user.
    Returns the NEW count after incrementing.
    Uses INSERT OR REPLACE to handle first-message-of-day.
    """
    with get_db() as conn:
        _ensure_user_exists(conn, user_id)
        conn.execute(
            """INSERT INTO daily_usage (user_id, date, count) VALUES (?, ?, 1)
               ON CONFLICT(user_id, date) DO UPDATE SET count = daily_usage.count + 1""",
            (user_id, date),
        )
        row = conn.execute(
            "SELECT count FROM daily_usage WHERE user_id = ? AND date = ?",
            (user_id, date),
        ).fetchone()
    return int(row["count"]) if row else 1

