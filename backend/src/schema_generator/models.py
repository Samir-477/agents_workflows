from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class SchemaGenerationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class SchemaGenerationStage(StrEnum):
    QUEUED = "queued"
    INTERPRETING = "interpreting"
    COMPILING = "compiling"
    VALIDATING = "validating"
    RECOMMENDING = "recommending"
    COMPLETE = "complete"
    FAILED = "failed"


SchemaType = Literal[
    "Organization",
    "LocalBusiness",
    "MedicalBusiness",
    "Product",
    "Article",
    "FAQPage",
    "Event",
    "SoftwareApplication",
]


class SchemaGenerationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    prompt: str = Field(min_length=20, max_length=20_000)


class SchemaEntityDraft(BaseModel):
    schema_type: SchemaType
    name: str = Field(min_length=1, max_length=300)
    properties: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(min_length=1, max_length=1_200)
    visible_evidence: list[str] = Field(default_factory=list, max_length=30)
    placement_scope: Literal["page-specific", "site-wide"] = "page-specific"

    @field_validator("visible_evidence")
    @classmethod
    def unique_evidence(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class ParsedSchemaBrief(BaseModel):
    page_name: str = Field(min_length=1, max_length=300)
    page_url: str | None = Field(default=None, max_length=2_000)
    page_type: str = Field(min_length=1, max_length=120)
    entities: list[SchemaEntityDraft] = Field(min_length=1, max_length=12)
    missing_context: list[str] = Field(default_factory=list, max_length=30)
    mismatches: list[str] = Field(default_factory=list, max_length=30)
    assumptions: list[str] = Field(default_factory=list, max_length=30)


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning", "note"]
    code: str
    message: str
    schema_type: str | None = None


class SchemaBlockResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    schema_type: SchemaType
    name: str
    json_ld: dict[str, Any]
    rationale: str
    placement_scope: Literal["page-specific", "site-wide"]
    placement_guidance: str
    visible_evidence: list[str] = Field(default_factory=list)
    missing_properties: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    publish_ready: bool = False


class SchemaGenerationResult(BaseModel):
    generation_id: str
    page_name: str
    page_url: str | None = None
    page_type: str
    script: str
    graph: dict[str, Any]
    blocks: list[SchemaBlockResult]
    warnings: list[str] = Field(default_factory=list)
    validation_summary: str
    publish_ready: bool = False
    blocking_issue_count: int = 0
    generated_at: datetime = Field(default_factory=utc_now)


class SchemaGenerationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str
    status: SchemaGenerationStatus = SchemaGenerationStatus.QUEUED
    stage: SchemaGenerationStage = SchemaGenerationStage.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    parsed_brief: ParsedSchemaBrief | None = None
    result: SchemaGenerationResult | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SchemaGenerationResponse(BaseModel):
    generation: SchemaGenerationRecord
    result_available: bool = False


class SchemaGenerationSummary(BaseModel):
    id: str
    prompt_preview: str
    status: SchemaGenerationStatus
    stage: SchemaGenerationStage
    progress: int
    schema_types: list[str]
    result_available: bool
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class SchemaGenerationHistoryResponse(BaseModel):
    items: list[SchemaGenerationSummary]
    total: int
    limit: int
    offset: int
