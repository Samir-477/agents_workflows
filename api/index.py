"""Vercel entrypoint for Stellar's FastAPI backend."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))

from seo_audit.api import create_app  # noqa: E402

app = create_app()

__all__ = ["app"]
