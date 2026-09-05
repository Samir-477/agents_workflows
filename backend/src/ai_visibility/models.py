from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class VisibilityStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class VisibilityStage(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    CRAWLING = "crawling"
    ANALYZING = "analyzing"
    SCORING = "scoring"
    COMPLETE = "complete"
    FAILED = "failed"


Dimension = Literal["discoverability", "machine_readability", "entity_clarity", "citability"]
Severity = Literal["critical", "important", "opportunity"]
Confidence = Literal["high", "medium", "low"]
PolicyStatus = Literal["allowed", "blocked", "not_declared"]


class VisibilityCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    url: str = Field(min_length=4, max_length=2048)
    business_name: str | None = Field(default=None, max_length=200)
    product_name: str | None = Field(default=None, max_length=200)
    audit_goal: str | None = Field(default=None, max_length=1000)
    important_urls: list[str] = Field(default_factory=list, max_length=20)
    crawl_limit: int | None = Field(default=None, ge=1, le=100)

    @field_validator("important_urls")
    @classmethod
    def unique_urls(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class BotPolicy(BaseModel):
    user_agent: str
    status: PolicyStatus
    evidence: str


class DimensionScore(BaseModel):
    dimension: Dimension
    score: int = Field(ge=0, le=100)
    summary: str
    deductions: list[str] = Field(default_factory=list)


class VisibilityFinding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    dimension: Dimension
    severity: Severity
    confidence: Confidence
    title: str
    observation: str
    why_it_matters: str
    recommendation: str
    affected_urls: list[str]
    evidence: list[str]
    priority_score: int = Field(ge=0, le=100)


class PageVisibilitySummary(BaseModel):
    url: str
    title: str
    score: int = Field(ge=0, le=100)
    word_count: int
    schema_types: list[str]
    question_sections: int
    findings: int


class VisibilityResult(BaseModel):
    audit_id: str
    requested_url: str
    normalized_origin: str
    pages_crawled: int
    discovered_url_count: int
    coverage_complete: bool
    overall_score: int = Field(ge=0, le=100)
    dimensions: list[DimensionScore]
    bot_policies: list[BotPolicy]
    findings: list[VisibilityFinding]
    pages: list[PageVisibilitySummary]
    methodology: str
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class VisibilityRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    requested_url: str
    normalized_origin: str | None = None
    business_name: str | None = None
    product_name: str | None = None
    audit_goal: str | None = None
    important_urls: list[str] = Field(default_factory=list)
    crawl_limit: int = 10
    status: VisibilityStatus = VisibilityStatus.QUEUED
    stage: VisibilityStage = VisibilityStage.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    result: VisibilityResult | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class VisibilityResponse(BaseModel):
    audit: VisibilityRecord
    result_available: bool = False


class VisibilitySummary(BaseModel):
    id: str
    url: str
    status: VisibilityStatus
    stage: VisibilityStage
    progress: int
    overall_score: int | None = None
    page_count: int = 0
    finding_count: int = 0
    result_available: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class VisibilityHistoryResponse(BaseModel):
    items: list[VisibilitySummary]
    total: int
    limit: int
    offset: int
