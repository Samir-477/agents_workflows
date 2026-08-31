from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter


@dataclass(frozen=True, slots=True)
class AgentRegistration:
    """One independently owned agent mounted in the shared deployment."""

    slug: str
    router: APIRouter
    initialize: Callable[[], None]
