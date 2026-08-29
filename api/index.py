"""Unified Vercel entrypoint for the FastAPI backend."""

import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[1] / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from seo_audit.api import app  # noqa: E402

__all__ = ["app"]
