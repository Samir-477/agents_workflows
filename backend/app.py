"""FastAPI entrypoint for local use and the backend Vercel project."""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from agent_runtime.api import create_app  # noqa: E402

app = create_app()

__all__ = ["app"]
