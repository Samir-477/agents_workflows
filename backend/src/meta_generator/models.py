from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class GenerationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class GenerationStage(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    GENERATING = "generating"
    VALIDATING = "validating"
    DEDUPLICATING = "deduplicating"
    RECOMMENDING = "recommending"
    COMPLETE = "complete"
    FAILED = "failed"


class LengthStatus(StrEnum):
    SHORT = "short"
    GOOD = "good"
    LONG = "long"


class MetadataGenerationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prompt: str = Field(min_length=20, max_length=20_000)


class ParsedPageBrief(BaseModel):
    page_key: str = Field(min_length=1, max_length=120)
    page_name: str = Field(min_length=1, max_length=200)
    page_type: str = Field(min_length=1, max_length=80)
    topic: str = Field(min_length=1, max_length=500)
    primary_keyword: str | None = Field(default=None, max_length=200)
    keyword_source: Literal["provided", "inferred", "not_supplied"] = "not_supplied"
    secondary_terms: list[str] = Field(default_factory=list, max_length=12)
    audience: str | None = Field(default=None, max_length=500)
    search_intent: str = Field(min_length=1, max_length=100)
    brand: str | None = Field(default=None, max_length=120)
    language: str = Field(default="English", max_length=80)
    verified_facts: list[str] = Field(default_factory=list, max_length=30)
    missing_context: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("secondary_terms", "verified_facts", "missing_context")
    @classmethod
    def unique_strings(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class ParsedGenerationBrief(BaseModel):
    pages: list[ParsedPageBrief] = Field(min_length=1, max_length=10)
    shared_brand_guidance: str | None = Field(default=None, max_length=1000)
    warnings: list[str] = Field(default_factory=list, max_length=30)


class DraftMetadataOption(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    intent: str = Field(min_length=1, max_length=100)
    angle: str = Field(min_length=1, max_length=100)
    rationale: str = Field(min_length=1, max_length=500)


class DraftPageMetadata(BaseModel):
    page_key: str = Field(min_length=1, max_length=120)
    titles: list[DraftMetadataOption] = Field(min_length=4, max_length=4)
    descriptions: list[DraftMetadataOption] = Field(min_length=3, max_length=3)
    brand_guidance: str = Field(min_length=1, max_length=700)


class DraftGenerationResult(BaseModel):
    pages: list[DraftPageMetadata] = Field(min_length=1, max_length=10)


class MetadataOption(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    character_count: int = Field(ge=0)
    length_status: LengthStatus
    intent: str
    angle: str
    rationale: str
    score: float = 0
    recommended: bool = False
    issues: list[str] = Field(default_factory=list)


class PageMetadataResult(BaseModel):
    page_key: str
    page_name: str
    page_type: str
    search_intent: str
    primary_keyword: str | None = None
    keyword_source: Literal["provided", "inferred", "not_supplied"]
    titles: list[MetadataOption]
    descriptions: list[MetadataOption]
    recommended_title_id: str
    recommended_description_id: str
    brand_guidance: str
    warnings: list[str] = Field(default_factory=list)


class MetadataGenerationResult(BaseModel):
    generation_id: str
    pages: list[PageMetadataResult]
    batch_warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class MetadataGenerationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str
    status: GenerationStatus = GenerationStatus.QUEUED
    stage: GenerationStage = GenerationStage.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    parsed_brief: ParsedGenerationBrief | None = None
    result: MetadataGenerationResult | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MetadataGenerationResponse(BaseModel):
    generation: MetadataGenerationRecord
    result_available: bool = False


class MetadataGenerationSummary(BaseModel):
    id: str
    prompt_preview: str
    status: GenerationStatus
    stage: GenerationStage
    progress: int
    page_count: int
    result_available: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class MetadataGenerationHistoryResponse(BaseModel):
    items: list[MetadataGenerationSummary]
    total: int
    limit: int
    offset: int
