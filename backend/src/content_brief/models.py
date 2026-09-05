from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContentBriefStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class ContentBriefStage(StrEnum):
    QUEUED = "queued"
    NORMALIZING = "normalizing"
    PLANNING = "planning"
    VALIDATING = "validating"
    REPAIRING = "repairing"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    FAILED = "failed"


SearchIntent = Literal[
    "informational", "commercial", "transactional", "navigational", "mixed"
]
IntentConfidence = Literal["high", "medium", "low"]
ContentMode = Literal["new", "rewrite"]
HeadingLevel = Literal["H2", "H3"]


class ContentBriefCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    target_keyword: str = Field(min_length=2, max_length=300)
    audience: str = Field(min_length=2, max_length=800)
    secondary_keywords: list[str] = Field(default_factory=list, max_length=30)
    angle: str | None = Field(default=None, max_length=1_500)
    business_goal: str | None = Field(default=None, max_length=1_500)
    product_context: str | None = Field(default=None, max_length=2_000)
    existing_urls: list[str] = Field(default_factory=list, max_length=30)
    source_notes: str | None = Field(default=None, max_length=8_000)
    content_mode: ContentMode = "new"

    @field_validator("secondary_keywords")
    @classmethod
    def unique_keywords(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @field_validator("existing_urls")
    @classmethod
    def valid_urls(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(item.strip().rstrip("/") for item in value if item.strip()))
        for item in cleaned:
            parsed = urlsplit(item)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("Existing pages must be absolute http(s) URLs")
        return cleaned


class OutlineSection(BaseModel):
    heading_level: HeadingLevel
    heading: str = Field(min_length=2, max_length=180)
    purpose: str = Field(min_length=10, max_length=800)
    talking_points: list[str] = Field(min_length=1, max_length=10)
    questions_answered: list[str] = Field(default_factory=list, max_length=6)
    suggested_words: int = Field(ge=50, le=1_500)

    @field_validator("talking_points", "questions_answered")
    @classmethod
    def unique_items(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class CoverageItem(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    item_type: Literal["topic", "entity", "concept", "standard", "tool"]
    why_include: str = Field(min_length=5, max_length=500)
    source: Literal["provided", "inferred"] = "inferred"


class FAQItem(BaseModel):
    question: str = Field(min_length=5, max_length=300)
    answer_guidance: str = Field(min_length=10, max_length=600)
    source: Literal["provided", "inferred"] = "inferred"


class BriefLinkRecommendation(BaseModel):
    target_url: str = Field(min_length=8, max_length=2_048)
    anchor_direction: str = Field(min_length=2, max_length=120)
    placement_heading: str = Field(min_length=2, max_length=180)
    reason: str = Field(min_length=10, max_length=600)


class ConversionNote(BaseModel):
    call_to_action: str = Field(min_length=2, max_length=240)
    placement_heading: str = Field(min_length=2, max_length=180)
    rationale: str = Field(min_length=10, max_length=600)


class ContentBriefDraft(BaseModel):
    suggested_title: str = Field(min_length=5, max_length=180)
    search_intent: SearchIntent
    intent_confidence: IntentConfidence
    intent_rationale: str = Field(min_length=20, max_length=1_000)
    reader_job: str = Field(min_length=10, max_length=800)
    recommended_format: str = Field(min_length=2, max_length=120)
    tone_and_voice: list[str] = Field(min_length=1, max_length=8)
    target_word_count_min: int = Field(ge=400, le=5_000)
    target_word_count_max: int = Field(ge=600, le=6_000)
    introduction_guidance: str = Field(min_length=20, max_length=1_000)
    outline: list[OutlineSection] = Field(min_length=3, max_length=18)
    coverage: list[CoverageItem] = Field(min_length=3, max_length=40)
    faqs: list[FAQItem] = Field(default_factory=list, max_length=10)
    internal_links: list[BriefLinkRecommendation] = Field(default_factory=list, max_length=30)
    conversion_notes: list[ConversionNote] = Field(default_factory=list, max_length=8)
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    writer_checks: list[str] = Field(min_length=3, max_length=20)

    @model_validator(mode="after")
    def valid_word_range(self) -> "ContentBriefDraft":
        if self.target_word_count_min >= self.target_word_count_max:
            raise ValueError("target_word_count_min must be lower than target_word_count_max")
        return self


class BriefValidationIssue(BaseModel):
    severity: Literal["error", "warning", "note"]
    code: str
    message: str


class ContentBriefResult(BaseModel):
    generation_id: str
    target_keyword: str
    audience: str
    content_mode: ContentMode
    brief: ContentBriefDraft
    quality_score: int = Field(ge=0, le=100)
    ready_for_handoff: bool
    issues: list[BriefValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_limitations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class ContentBriefRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    request: ContentBriefCreate
    status: ContentBriefStatus = ContentBriefStatus.QUEUED
    stage: ContentBriefStage = ContentBriefStage.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    draft: ContentBriefDraft | None = None
    result: ContentBriefResult | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ContentBriefResponse(BaseModel):
    generation: ContentBriefRecord
    result_available: bool = False


class ContentBriefSummary(BaseModel):
    id: str
    target_keyword: str
    audience: str
    status: ContentBriefStatus
    stage: ContentBriefStage
    progress: int
    ready_for_handoff: bool | None = None
    result_available: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class ContentBriefHistoryResponse(BaseModel):
    items: list[ContentBriefSummary]
    total: int
    limit: int
    offset: int
