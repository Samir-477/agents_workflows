"""Vercel's FastAPI entrypoint when `backend/` is the project root."""

from seo_audit.api import app

__all__ = ["app"]
