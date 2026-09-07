from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class SerpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    target_keyword: str = Field(min_length=2, max_length=300)
    country: str = Field(default="in", pattern=r"^[a-zA-Z]{2}$")
    language: str = Field(default="en", pattern=r"^[a-zA-Z]{2}$")
    result_limit: int = Field(default=10, ge=3, le=10)
    inspect_limit: int = Field(default=5, ge=0, le=10)


class SerpItem(BaseModel):
    position: int = Field(ge=1)
    title: str
    url: str
    snippet: str = ""
    domain: str


class QuestionEvidence(BaseModel):
    question: str
    source_url: str | None = None


class AnswerBoxEvidence(BaseModel):
    title: str | None = None
    answer: str
    source_url: str | None = None


class CompetitorEvidence(BaseModel):
    position: int
    url: str
    title: str
    fetched: bool
    word_count: int | None = None
    headings: list[str] = Field(default_factory=list)
    schema_types: list[str] = Field(default_factory=list)
    fetch_note: str | None = None


class PatternEvidence(BaseModel):
    label: str
    count: int
    source_urls: list[str]


class SerpResult(BaseModel):
    run_id: str
    target_keyword: str
    country: str
    language: str
    observed_at: datetime
    search_intent: Literal["informational", "commercial", "transactional", "navigational", "mixed"]
    intent_rationale: str
    organic_results: list[SerpItem]
    questions: list[QuestionEvidence]
    related_searches: list[str]
    competitors: list[CompetitorEvidence]
    common_headings: list[PatternEvidence]
    common_schema: list[PatternEvidence]
    answer_box: AnswerBoxEvidence | None = None
    topic_patterns: list[PatternEvidence] = Field(default_factory=list)
    median_word_count: int | None = None
    recommendations: list[str]
    warnings: list[str]
    limitations: list[str]
    snapshot_source_run_id: str | None = None


class SerpRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    request: SerpRequest
    status: Literal["queued", "running", "complete", "failed"] = "queued"
    stage: str = "queued"
    progress: int = 0
    result: SerpResult | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
