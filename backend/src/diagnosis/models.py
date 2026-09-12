from __future__ import annotations

from datetime import datetime, UTC
from typing import Literal, Any
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict, HttpUrl, model_validator


def now() -> str:
    return datetime.now(UTC).isoformat()


AGENTS = {
    "seo_audit": "Website Health Review",
    "ai_visibility": "AI and Search-System Readiness",
    "internal_linking": "Customer Navigation to This Resort",
    "serp_competitor": "Branded Google Search Visibility",
    "keyword_cluster": "Search Themes and Page Structure",
    "metadata": "Search Titles and Descriptions",
    "schema_markup": "Resort Information for Search Systems",
    "content_brief": "Content Improvement Plan",
    "local_seo": "Local Resort Information",
    "content_optimizer": "Resort Page Content Quality",
}
LABELS = dict(zip(AGENTS, ["SEO/AEO Audit", "AI Visibility", "Internal Linking", "SERP & Competitor", "Keyword Clustering", "Metadata", "Schema Markup", "Content Brief", "Local SEO", "Content Optimizer"]))
AGENT_DEPENDENCIES = {
    "keyword_cluster": {"serp_competitor"},
    "content_brief": {"serp_competitor", "keyword_cluster"},
    "content_optimizer": {"serp_competitor", "keyword_cluster", "content_brief"},
}


class DiagnosisInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    page_url: HttpUrl
    audience: str = Field(default="", max_length=500)
    business_goal: str = Field(default="", max_length=1000)
    page_limit: int = Field(default=8, ge=1, le=20)
    country: str = Field(default="in", pattern=r"^[a-zA-Z]{2}$")
    language: str = Field(default="en", pattern=r"^[a-zA-Z]{2}$")
    model_provider: Literal["configured", "deepseek"] = "configured"
    run_mode: Literal["diagnosis", "individual"] = "diagnosis"
    selected_agents: list[Literal[
        "seo_audit", "ai_visibility", "internal_linking", "serp_competitor",
        "keyword_cluster", "metadata", "schema_markup", "content_brief",
        "local_seo", "content_optimizer",
    ]] = Field(default_factory=lambda: list(AGENTS))

    @model_validator(mode="before")
    @classmethod
    def read_legacy_records(cls, value):
        # Diagnoses created by the short-lived earlier UI may contain this field.
        # Ignore it when reopening those records; all runs use captured page evidence.
        if isinstance(value, dict) and "target_keyword" in value:
            value = dict(value)
            value.pop("target_keyword", None)
        return value

    @model_validator(mode="after")
    def include_required_agent_dependencies(self):
        selected = set(self.selected_agents)
        if not selected:
            raise ValueError("Select at least one agent")
        if self.run_mode == "individual":
            if len(selected) != 1:
                raise ValueError("An individual run must select exactly one agent")
            self.selected_agents = [key for key in AGENTS if key in selected]
            return self
        while True:
            expanded = selected | set().union(*(AGENT_DEPENDENCIES.get(key, set()) for key in selected))
            if expanded == selected:
                break
            selected = expanded
        self.selected_agents = [key for key in AGENTS if key in selected]
        return self


class Task(BaseModel):
    status: Literal["queued", "running", "complete", "failed", "needs_review"] = "queued"
    token: str | None = None
    lease_until: float = 0
    attempts: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    run_id: str | None = None
    error: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)


class Diagnosis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    owner_subject: str | None = None
    request: DiagnosisInput
    status: Literal["queued", "running", "complete", "partial", "cancelled"] = "queued"
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
    tasks: dict[str, Task] = Field(default_factory=lambda: {k: Task() for k in ["capture", *AGENTS, "report"]})
    report: dict[str, Any] | None = None
