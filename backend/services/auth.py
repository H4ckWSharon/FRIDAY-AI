"""
FRIDAY AI — Authentication & Security Service (Firebase Google Authentication)
Implements:
  - Secure Firebase Admin SDK initialization supporting:
      1. Raw service account JSON string via FIREBASE_SERVICE_ACCOUNT_JSON
      2. Service account JSON file via FIREBASE_SERVICE_ACCOUNT_PATH
      3. Google Cloud Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS)
      4. Project-ID initialization for cryptographic ID token verification
  - Cryptographic verification of Firebase ID tokens (JWT) using Google public x509 certs
  - Firebase UID extraction as the permanent, stable operator identity
  - Zero-exposure logging: raw tokens and sensitive credentials are never logged
"""

import os
import json
import time
import logging
from typing import Optional, Callable
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials as firebase_credentials

from config import get_settings

logger = logging.getLogger(__name__)

# Singleton Firebase Admin App instance
_firebase_app: Optional[firebase_admin.App] = None

# Optional test hook for unit testing token verification in offline / mock test runs
_mock_token_verifier: Optional[Callable[[str], Optional[dict]]] = None

# In-memory token cache: token -> (expiry_timestamp, user_dict)
_TOKEN_CACHE: dict[str, tuple[float, dict]] = {}
_shared_http_request = None


def _get_http_request():
    global _shared_http_request
    if _shared_http_request is None:
        try:
            import requests
            import google.auth.transport.requests

            session = requests.Session()
            _shared_http_request = google.auth.transport.requests.Request(session=session)
        except Exception:
            _shared_http_request = None
    return _shared_http_request


def set_mock_token_verifier(verifier: Optional[Callable[[str], Optional[dict]]]) -> None:
    """Set or clear a custom token verifier for automated test suites."""
    global _mock_token_verifier
    _mock_token_verifier = verifier


def get_firebase_app() -> firebase_admin.App:
    """
    Initialize or return the existing Firebase Admin App instance.
    Follows a secure credential-resolution hierarchy:
      1. Environment JSON (FIREBASE_SERVICE_ACCOUNT_JSON)
      2. File on disk (FIREBASE_SERVICE_ACCOUNT_PATH)
      3. Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS)
      4. Project ID (projectId option for public cert verification)
    """
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    # Check if default app or named app was already created
    if len(firebase_admin._apps) > 0:
        for app_name, app_inst in firebase_admin._apps.items():
            if app_inst:
                _firebase_app = app_inst
                return _firebase_app

    settings = get_settings()
    app_name = "friday-ai"

    # Strategy 1: Raw JSON string in environment (ideal for container/cloud deployment)
    if settings.firebase_service_account_json:
        try:
            cert_dict = json.loads(settings.firebase_service_account_json)
            cred = firebase_credentials.Certificate(cert_dict)
            _firebase_app = firebase_admin.initialize_app(cred, name=app_name)
            logger.info("Firebase Admin initialized via FIREBASE_SERVICE_ACCOUNT_JSON")
            return _firebase_app
        except Exception as exc:
            logger.error("Failed to initialize Firebase Admin with FIREBASE_SERVICE_ACCOUNT_JSON: %s", exc)

    # Strategy 2: File on disk outside public web root
    sa_path = settings.resolved_firebase_service_account_path
    if sa_path and os.path.isfile(sa_path):
        try:
            cred = firebase_credentials.Certificate(sa_path)
            _firebase_app = firebase_admin.initialize_app(cred, name=app_name)
            logger.info("Firebase Admin initialized via service account file")
            return _firebase_app
        except Exception as exc:
            logger.error("Failed to initialize Firebase Admin with service account file %s: %s", sa_path, exc)

    # Strategy 3: Standard Google Cloud Application Default Credentials
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            cred = firebase_credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(
                cred,
                options={"projectId": settings.firebase_project_id},
                name=app_name,
            )
            logger.info("Firebase Admin initialized via ApplicationDefault")
            return _firebase_app
        except Exception as exc:
            logger.error("Failed to initialize Firebase Admin via ApplicationDefault: %s", exc)

    # Strategy 4: Project-ID initialization (Google x509 public key token verification)
    try:
        _firebase_app = firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project_id},
            name=app_name,
        )
        logger.info("Firebase Admin initialized with projectId: %s", settings.firebase_project_id)
        return _firebase_app
    except Exception as exc:
        logger.error("Failed to initialize Firebase Admin app: %s", exc)
        raise


def verify_firebase_token(id_token: str) -> Optional[dict]:
    """
    Cryptographically verify a Firebase ID token.
    Extracts and returns:
      - uid: stable Firebase user identifier
      - email: user's email address
      - name: user's display name
      - picture: user's avatar URL
      - email_verified: boolean
    Returns None if verification fails (expired, invalid signature, malformed).
    Uses in-memory TTL caching to eliminate network round-trip overhead on subsequent requests.
    NEVER logs the raw ID token.
    """
    if not id_token or not isinstance(id_token, str):
        return None

    # Check if a mock verifier is registered (for offline test suites)
    if _mock_token_verifier is not None:
        try:
            return _mock_token_verifier(id_token)
        except Exception as exc:
            logger.warning("Mock token verifier returned failure: %s", exc)
            return None

    token = id_token.strip()
    if not token:
        return None

    now_ts = time.time()

    # Fast in-memory cache hit (sub-millisecond return)
    if token in _TOKEN_CACHE:
        exp_ts, cached_user = _TOKEN_CACHE[token]
        if exp_ts > now_ts:
            return cached_user

    settings = get_settings()
    # Safe development/local testing fallback: only active when APP_ENV=development
    if settings.is_development and token.startswith("dev-token:"):
        parts = token.split(":")
        dev_uid = parts[1] if len(parts) > 1 and parts[1] else "dev-operator-001"
        dev_email = parts[2] if len(parts) > 2 and parts[2] else "operator@friday.local"
        dev_name = parts[3] if len(parts) > 3 and parts[3] else "Operator 0x1"
        user_data = {
            "uid": str(dev_uid),
            "email": dev_email.strip().lower(),
            "name": dev_name,
            "picture": None,
            "email_verified": True,
            "firebase_claims": {"uid": dev_uid, "email": dev_email, "auth_provider": "development_mock"},
        }
        _TOKEN_CACHE[token] = (now_ts + 1800, user_data)
        return user_data

    decoded = None

    # Check if service account credentials are explicitly provided.
    # If not, skip Strategy A to avoid the 3-second EC2/GCE metadata service timeout.
    has_sa = bool(
        settings.firebase_service_account_json
        or (settings.resolved_firebase_service_account_path and os.path.isfile(settings.resolved_firebase_service_account_path))
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )

    if has_sa:
        try:
            app = get_firebase_app()
            decoded = firebase_auth.verify_id_token(token, app=app, check_revoked=False)
        except firebase_auth.ExpiredIdTokenError:
            logger.warning("Firebase ID token verification failed: token has expired")
            return None
        except firebase_auth.RevokedIdTokenError:
            logger.warning("Firebase ID token verification failed: token has been revoked")
            return None
        except firebase_auth.InvalidIdTokenError:
            logger.warning("Firebase ID token verification failed: invalid token signature")
            return None
        except Exception as exc:
            logger.info("Firebase Admin verification deferred to public cert verifier: %s", exc)

    # Strategy B: Cryptographic verification via Google Public x509 Certs (no private key required)
    if not decoded:
        try:
            import google.oauth2.id_token
            http_req = _get_http_request()
            if http_req is None:
                import google.auth.transport.requests
                http_req = google.auth.transport.requests.Request()

            decoded = google.oauth2.id_token.verify_firebase_token(
                token,
                http_req,
                audience=settings.firebase_project_id,
            )
        except Exception as exc:
            logger.warning("Google public cert token verification failed: %s", exc)
            return None

    if not decoded:
        return None

    uid = decoded.get("uid") or decoded.get("sub") or decoded.get("user_id")
    if not uid:
        logger.warning("Firebase token missing uid claim")
        return None

    email = decoded.get("email")
    name = decoded.get("name") or (email.split("@")[0].capitalize() if email else "Operator")
    picture = decoded.get("picture")

    user_data = {
        "uid": str(uid),
        "email": email.strip().lower() if email else None,
        "name": name,
        "picture": picture,
        "email_verified": bool(decoded.get("email_verified", False)),
        "firebase_claims": decoded,
    }

    # Cache token until expiration (or up to 30 minutes)
    exp = decoded.get("exp")
    try:
        exp_ts = float(exp) if exp else (now_ts + 1800)
    except Exception:
        exp_ts = now_ts + 1800
    _TOKEN_CACHE[token] = (min(exp_ts, now_ts + 1800), user_data)

    return user_data
