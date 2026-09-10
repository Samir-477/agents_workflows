import base64
import hashlib
import hmac
import json
import time

from agent_runtime.session import session_subject


def signed_token(secret: str, subject: str, expires: float) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"sub": subject, "exp": expires}, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return payload + "." + signature


def test_production_rejects_the_legacy_static_cookie(monkeypatch):
    monkeypatch.setenv("STELLAR_ENVIRONMENT", "production")
    monkeypatch.delenv("STELLAR_SESSION_SECRET", raising=False)
    assert session_subject("stellar-admin") is None


def test_signed_session_requires_valid_signature_and_future_expiry(monkeypatch):
    monkeypatch.setenv("STELLAR_ENVIRONMENT", "production")
    monkeypatch.setenv("STELLAR_SESSION_SECRET", "a-long-test-secret-that-is-not-production")
    valid = signed_token("a-long-test-secret-that-is-not-production", "owner-a", time.time() + 60)
    expired = signed_token("a-long-test-secret-that-is-not-production", "owner-a", time.time() - 1)
    assert session_subject(valid) == "owner-a"
    assert session_subject(valid + "tampered") is None
    assert session_subject(expired) is None
