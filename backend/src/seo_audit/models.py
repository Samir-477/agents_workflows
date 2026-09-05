from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class AuditStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class AuditStage(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    CRAWLING = "crawling"
    AUDITING = "auditing"
    SCORING = "scoring"
    REPORTING = "reporting"
    COMPLETE = "complete"
    FAILED = "failed"


class Severity(StrEnum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    MINOR = "minor"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AuditCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: str = Field(min_length=4, max_length=2048)
    business_description: str | None = Field(default=None, max_length=3000)
    audit_reason: str | None = Field(default=None, max_length=2000)
    important_urls: list[str] = Field(default_factory=list, max_length=20)
    crawl_limit: int | None = Field(default=None, ge=1, le=100)

    @field_validator("important_urls")
    @classmethod
    def unique_important_urls(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class AuditRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    requested_url: str
    normalized_origin: str | None = None
    business_description: str | None = None
    audit_reason: str | None = None
    important_urls: list[str] = Field(default_factory=list)
    crawl_limit: int = 50
    status: AuditStatus = AuditStatus.QUEUED
    stage: AuditStage = AuditStage.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class LinkRecord(BaseModel):
    url: str
    anchor_text: str = ""
    placement: Literal["content", "navigation", "footer", "other"] = "other"
    section_heading: str | None = None
    context_text: str | None = None


class ContentSection(BaseModel):
    heading: str | None = None
    text: str


class PageRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    audit_id: str
    requested_url: str
    final_url: str
    status_code: int | None = None
    depth: int = 0
    content_type: str | None = None
    title: str | None = None
    meta_description: str | None = None
    canonical: str | None = None
    robots_directives: list[str] = Field(default_factory=list)
    h1: list[str] = Field(default_factory=list)
    h2: list[str] = Field(default_factory=list)
    word_count: int = 0
    internal_links: list[LinkRecord] = Field(default_factory=list)
    link_occurrences: list[LinkRecord] = Field(default_factory=list)
    content_sections: list[ContentSection] = Field(default_factory=list)
    images_total: int = 0
    images_missing_alt: int = 0
    schema_types: list[str] = Field(default_factory=list)
    has_viewport: bool = False
    content_hash: str | None = None
    fetch_error: str | None = None


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    audit_id: str
    rule_id: str
    title: str
    severity: Severity
    confidence: Confidence
    evidence: str
    why_it_matters: str
    recommendation: str
    affected_urls: list[str]
    score: float = 0


class FindingReport(BaseModel):
    rule_id: str
    title: str
    severity: Severity
    confidence: Confidence
    score: float
    affected_urls: list[str]
    evidence: str
    why_it_matters: str
    recommendation: str


class AuditReport(BaseModel):
    audit_id: str
    requested_url: str
    executive_summary: str
    site_score: int | None = Field(default=None, ge=0, le=100)
    pages_crawled: int
    severity_counts: dict[str, int]
    quick_wins: list[str]
    findings: list[FindingReport]
    limitations: list[str]
    generated_with_llm: bool = False
    generated_at: datetime = Field(default_factory=utc_now)


class AuditResponse(BaseModel):
    audit: AuditRecord
    pages_crawled: int = 0
    findings_count: int = 0
    report_available: bool = False


class AuditHistoryResponse(BaseModel):
    items: list[AuditResponse]
    total: int
    limit: int
    offset: int


class ReportNarrative(BaseModel):
    executive_summary: str = Field(min_length=20, max_length=1500)
    quick_win_rule_ids: list[str] = Field(default_factory=list, max_length=8)


JsonObject = dict[str, Any]
