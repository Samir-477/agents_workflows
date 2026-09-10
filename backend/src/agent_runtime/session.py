from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


DEV_SECRET = "stellar-local-development-session-key"


def _production() -> bool:
    return (os.getenv("STELLAR_ENVIRONMENT") or os.getenv("VERCEL_ENV") or "").casefold() == "production"


def session_subject(value: str | None) -> str | None:
    if not value:
        return None
    configured = os.getenv("STELLAR_SESSION_SECRET")
    if not configured and _production():
        return None
    # Keep existing local test sessions working, but never accept this static
    # cookie when the service is configured as production.
    if not configured and value == "stellar-admin":
        return "local-demo-admin"
    secret = (configured or DEV_SECRET).encode()
    try:
        payload, signature = value.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(secret, payload.encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(signature, expected):
            return None
        padded = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode())
        if not data.get("sub") or float(data.get("exp", 0)) <= time.time():
            return None
        return str(data["sub"])
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None
