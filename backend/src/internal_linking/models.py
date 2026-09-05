from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class InternalLinkStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class InternalLinkStage(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    CRAWLING = "crawling"
    MAPPING = "mapping"
    ANALYZING = "analyzing"
    REFINING = "refining"
    VALIDATING_RESULTS = "validating_results"
    COMPLETE = "complete"
    FAILED = "failed"


RecommendationType = Literal[
    "orphan", "orphan_candidate", "underlinked_important", "contextual_gap", "weak_anchor"
]
PriorityTier = Literal["critical", "important", "opportunity"]
Confidence = Literal["high", "medium", "low"]
OrphanStatus = Literal["confirmed", "candidate", "not_orphan"]


class InternalLinkCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    url: str = Field(min_length=3, max_length=2_048)
    business_description: str | None = Field(default=None, max_length=2_000)
    audit_goal: str | None = Field(default=None, max_length=1_000)
    important_urls: list[str] = Field(default_factory=list, max_length=20)
    crawl_limit: int | None = Field(default=None, ge=1, le=100)

    @field_validator("important_urls")
    @classmethod
    def unique_important_urls(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class PageLinkSummary(BaseModel):
    url: str
    title: str
    depth: int
    page_role: str
    inbound_sources: int
    contextual_inbound_sources: int
    outbound_targets: int
    contextual_outbound_targets: int
    important: bool
    orphan_status: OrphanStatus


class LinkCandidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    recommendation_type: RecommendationType
    source_url: str
    source_title: str
    target_url: str
    target_title: str
    current_anchor: str | None = None
    section_heading: str | None = None
    context_snippet: str | None = None
    topical_score: float = Field(ge=0, le=1)
    target_importance: int = Field(ge=0, le=20)
    source_is_contextual: bool = False


class LinkRefinement(BaseModel):
    candidate_id: str
    anchor_options: list[str] = Field(default_factory=list, min_length=1, max_length=3)
    placement_note: str = Field(min_length=1, max_length=500)
    reasoning: str = Field(min_length=1, max_length=700)


class LinkRefinementSet(BaseModel):
    refinements: list[LinkRefinement] = Field(default_factory=list, max_length=30)


class InternalLinkRecommendation(BaseModel):
    id: str
    recommendation_type: RecommendationType
    priority_score: int = Field(ge=0, le=100)
    priority_tier: PriorityTier
    confidence: Confidence
    source_url: str
    source_title: str
    target_url: str
    target_title: str
    current_anchor: str | None = None
    anchor_options: list[str]
    placement_heading: str | None = None
    placement_snippet: str | None = None
    placement_note: str
    reasoning: str
    evidence: list[str]
    score_factors: list[str]


class InternalLinkResult(BaseModel):
    audit_id: str
    requested_url: str
    normalized_origin: str
    pages_crawled: int
    discovered_url_count: int
    coverage_complete: bool
    observed_edge_count: int
    contextual_edge_count: int
    confirmed_orphan_count: int
    orphan_candidate_count: int
    weak_anchor_count: int
    recommendations: list[InternalLinkRecommendation]
    pages: list[PageLinkSummary]
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generated_with_llm: bool = False
    generated_at: datetime = Field(default_factory=utc_now)


class InternalLinkRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    requested_url: str
    normalized_origin: str | None = None
    business_description: str | None = None
    audit_goal: str | None = None
    important_urls: list[str] = Field(default_factory=list)
    crawl_limit: int
    status: InternalLinkStatus = InternalLinkStatus.QUEUED
    stage: InternalLinkStage = InternalLinkStage.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    result: InternalLinkResult | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InternalLinkResponse(BaseModel):
    audit: InternalLinkRecord
    result_available: bool = False


class InternalLinkSummary(BaseModel):
    id: str
    url: str
    status: InternalLinkStatus
    stage: InternalLinkStage
    progress: int
    page_count: int
    recommendation_count: int
    result_available: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class InternalLinkHistoryResponse(BaseModel):
    items: list[InternalLinkSummary]
    total: int
    limit: int
    offset: int
