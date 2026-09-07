from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContentOptimizerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content_url: str | None = Field(default=None, max_length=2048)
    content_text: str | None = Field(default=None, max_length=100_000)
    page_title: str | None = Field(default=None, max_length=300)
    meta_description: str | None = Field(default=None, max_length=500)
    target_keyword: str = Field(min_length=2, max_length=300)
    secondary_keywords: list[str] = Field(default_factory=list, max_length=30)
    audience: str = Field(min_length=2, max_length=800)
    research_run_id: str | None = None
    content_brief_id: str | None = None

    @field_validator("content_url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("content_url must be an absolute http(s) URL")
        return value

    @field_validator("secondary_keywords")
    @classmethod
    def unique_keywords(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item for item in value if item))

    @model_validator(mode="after")
    def exactly_one_source(self) -> "ContentOptimizerRequest":
        if bool(self.content_url) == bool(self.content_text):
            raise ValueError("Provide exactly one of content_url or content_text")
        if self.content_text is not None and len(self.content_text) < 50:
            raise ValueError("content_text must contain at least 50 characters")
        return self


class OptimizerEvidence(BaseModel):
    id: str
    label: str
    observed: str
    source_url: str | None = None
    source_type: Literal["page", "supplied_text", "serp", "brief"]


class OptimizerAssessment(BaseModel):
    key: str
    label: str
    status: Literal["good", "review", "not_assessed"]
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)


class OptimizerAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    priority: Literal["critical", "high", "medium", "low"]
    category: str
    issue: str
    affected_section: str
    observed_text: str
    proposed_action: str
    confidence: Literal["high", "medium", "low"]
    effort: Literal["small", "medium", "large"]
    impact_rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


class ContentOptimizerResult(BaseModel):
    run_id: str
    source_mode: Literal["url", "text"]
    source_url: str | None = None
    target_keyword: str
    audience: str
    word_count: int
    overall_score: int | None = Field(default=None, ge=0, le=100)
    assessed_checks: int
    total_checks: int
    assessments: list[OptimizerAssessment]
    actions: list[OptimizerAction]
    evidence: list[OptimizerEvidence]
    research_run_id: str | None = None
    content_brief_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class ContentOptimizerRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    request: ContentOptimizerRequest
    status: Literal["queued", "running", "complete", "failed"] = "queued"
    stage: str = "queued"
    progress: int = 0
    result: ContentOptimizerResult | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
