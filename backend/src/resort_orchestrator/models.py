from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class OrchestratorStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


# One stage per child agent, in run order, plus the bracketing steps. The UI can
# show this list directly as a progress checklist.
STAGES: tuple[str, ...] = (
    "queued",
    "reading_page",
    "seo_audit",
    "ai_visibility",
    "internal_linking",
    "serp_competitor",
    "keyword_cluster",
    "metadata",
    "schema_markup",
    "content_brief",
    "local_seo",
    "content_optimizer",
    "assembling_report",
    "complete",
    "failed",
)


class OrchestratorCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    page_url: str = Field(min_length=4, max_length=2048)
    # Real business decisions, not page facts. Left blank, the run still executes
    # every agent — Content Brief and Content Optimizer fall back to a clearly
    # labelled default rather than being skipped.
    audience: str | None = Field(default=None, max_length=800)
    business_goal: str | None = Field(default=None, max_length=1500)

    @field_validator("page_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("page_url must be an absolute http(s) URL")
        return value


class AgentOutcome(BaseModel):
    """One child agent's result, as far as the orchestrator is concerned.

    `run_id` lets a caller reopen that agent's own full result through its own
    existing API — the orchestrator never duplicates that detail, only the
    summary needed to write the managerial report.
    """

    agent: str
    run_id: str | None = None
    status: str = "skipped"
    summary: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class OrchestratorRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    page_url: str
    audience: str | None = None
    business_goal: str | None = None
    derived_keyword: str | None = None
    status: OrchestratorStatus = OrchestratorStatus.QUEUED
    stage: str = "queued"
    progress: int = Field(default=0, ge=0, le=100)
    outcomes: dict[str, AgentOutcome] = Field(default_factory=dict)
    report: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class OrchestratorResponse(BaseModel):
    run: OrchestratorRecord
    result_available: bool = False


class OrchestratorSummary(BaseModel):
    id: str
    page_url: str
    status: OrchestratorStatus
    stage: str
    progress: int
    result_available: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class OrchestratorHistoryResponse(BaseModel):
    items: list[OrchestratorSummary]
    total: int
    limit: int
    offset: int
