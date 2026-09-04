from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class KeywordClusterStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class KeywordClusterStage(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    CLUSTERING = "clustering"
    CONSOLIDATING = "consolidating"
    PLANNING = "planning"
    VALIDATING = "validating"
    COMPLETE = "complete"
    FAILED = "failed"


SearchIntent = Literal["informational", "commercial", "transactional", "navigational", "mixed"]
PageRole = Literal["pillar", "supporting"]
RecommendationConfidence = Literal["high", "medium", "low"]


class KeywordClusterCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    keywords: str = Field(min_length=3, max_length=60_000)

    @model_validator(mode="after")
    def enough_keywords(self) -> "KeywordClusterCreate":
        lines = [line for line in self.keywords.splitlines() if line.strip()]
        if len(lines) < 3:
            raise ValueError("Paste at least three keywords, one per line")
        if len(lines) > 500:
            raise ValueError("The current version accepts up to 500 keyword rows per run")
        return self


class KeywordItem(BaseModel):
    keyword: str = Field(min_length=1, max_length=300)
    volume: int | None = Field(default=None, ge=0)


class CandidateCluster(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    intent: SearchIntent
    primary_keyword: str = Field(min_length=1, max_length=300)
    keywords: list[str] = Field(min_length=1, max_length=150)
    reasoning: str = Field(min_length=1, max_length=800)
    recommended_page_type: str = Field(min_length=1, max_length=100)

    @field_validator("keywords")
    @classmethod
    def unique_keywords(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class CandidateClusterSet(BaseModel):
    clusters: list[CandidateCluster] = Field(min_length=1, max_length=80)


class ConsolidatedCluster(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    pillar_name: str = Field(min_length=1, max_length=160)
    role: PageRole
    intent: SearchIntent
    primary_keyword: str = Field(min_length=1, max_length=300)
    keywords: list[str] = Field(min_length=1, max_length=500)
    reasoning: str = Field(min_length=1, max_length=1_000)
    recommended_page_type: str = Field(min_length=1, max_length=100)
    suggested_title: str = Field(min_length=1, max_length=180)
    build_priority: int = Field(ge=1, le=100)

    @field_validator("keywords")
    @classmethod
    def unique_keywords(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class ConsolidatedClusterSet(BaseModel):
    clusters: list[ConsolidatedCluster] = Field(min_length=1, max_length=80)
    strategy_summary: str = Field(min_length=1, max_length=2_000)
    assumptions: list[str] = Field(default_factory=list, max_length=30)


class KeywordClusterResultItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    pillar_name: str
    role: PageRole
    intent: SearchIntent
    primary_keyword: str
    keywords: list[KeywordItem]
    reasoning: str
    recommended_page_type: str
    suggested_title: str
    suggested_slug: str
    build_priority: int
    total_volume: int | None = None
    confidence: RecommendationConfidence = "medium"
    priority_factors: list[str] = Field(default_factory=list)


class PillarPlan(BaseModel):
    name: str
    primary_keyword: str
    suggested_title: str
    suggested_slug: str
    cluster_ids: list[str]
    supporting_page_ids: list[str]
    intent: SearchIntent
    build_priority: int
    total_volume: int | None = None
    recommendation_status: Literal["established", "candidate"] = "candidate"
    rationale: str = "Review this topic hub against the current site and available demand data."


class InternalLinkRecommendation(BaseModel):
    source_cluster_id: str
    target_cluster_id: str
    source_slug: str
    target_slug: str
    anchor_text: str
    reason: str


class KeywordClusterResult(BaseModel):
    generation_id: str
    input_count: int
    unique_keyword_count: int
    duplicate_count: int
    clusters: list[KeywordClusterResultItem]
    pillars: list[PillarPlan]
    internal_links: list[InternalLinkRecommendation]
    strategy_summary: str
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class KeywordClusterRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    raw_keywords: str
    status: KeywordClusterStatus = KeywordClusterStatus.QUEUED
    stage: KeywordClusterStage = KeywordClusterStage.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    parsed_keywords: list[KeywordItem] = Field(default_factory=list)
    result: KeywordClusterResult | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class KeywordClusterResponse(BaseModel):
    generation: KeywordClusterRecord
    result_available: bool = False


class KeywordClusterSummary(BaseModel):
    id: str
    keyword_preview: str
    status: KeywordClusterStatus
    stage: KeywordClusterStage
    progress: int
    keyword_count: int
    cluster_count: int
    pillar_count: int
    result_available: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class KeywordClusterHistoryResponse(BaseModel):
    items: list[KeywordClusterSummary]
    total: int
    limit: int
    offset: int
