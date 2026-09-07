from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LocalRequest(Model):
    prompt: str = Field(min_length=20, max_length=12000)
    existing_urls: list[HttpUrl] = Field(default_factory=list, max_length=20)
    lookup_maps: bool = False


class Location(Model):
    area: str = Field(min_length=2, max_length=160)
    kind: Literal["physical", "service_area", "planned", "unknown"]
    address: str = Field(default="", max_length=500)
    phone: str = Field(default="", max_length=80)
    hours: str = Field(default="", max_length=300)
    local_proof: list[str] = Field(default_factory=list, max_length=5)


class Profile(Model):
    business_name: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=80)
    hours: str = Field(default="", max_length=300)
    services: list[str] = Field(min_length=1, max_length=8)
    differentiators: list[str] = Field(default_factory=list, max_length=8)
    locations: list[Location] = Field(min_length=1, max_length=3)
    missing_information: list[str] = Field(default_factory=list, max_length=20)
    exceeds_page_limit: bool = False


class Section(Model):
    heading: str = Field(min_length=2, max_length=160)
    body: str = Field(min_length=10, max_length=1800)


class FAQ(Model):
    question: str = Field(min_length=5, max_length=250)
    answer: str = Field(min_length=5, max_length=600)


class CopyCore(Model):
    """Page copy without the FAQ block.

    The draft is requested in two calls because one combined response exceeds the
    per-request output allowance of smaller provider plans.
    """

    title: str = Field(min_length=5, max_length=120)
    meta_description: str = Field(min_length=10, max_length=300)
    headline: str = Field(min_length=5, max_length=200)
    introduction: str = Field(min_length=20, max_length=1800)
    sections: list[Section] = Field(min_length=2, max_length=5)
    call_to_action: str = Field(min_length=5, max_length=300)


class FAQSet(Model):
    faqs: list[FAQ] = Field(min_length=3, max_length=8)


class CopyDraft(Model):
    title: str = Field(min_length=5, max_length=120)
    meta_description: str = Field(min_length=10, max_length=300)
    headline: str = Field(min_length=5, max_length=200)
    introduction: str = Field(min_length=20, max_length=1800)
    sections: list[Section] = Field(min_length=2, max_length=5)
    faqs: list[FAQ] = Field(min_length=3, max_length=8)
    call_to_action: str = Field(min_length=5, max_length=300)


class Page(Model):
    area: str
    kind: str
    suggested_slug: str
    content: CopyDraft
    business_details: dict[str, str]
    json_ld: dict
    title_characters: int
    description_characters: int
    call_url: str | None = None
    directions_url: str | None = None
    existing_link_candidates: list[str] = Field(default_factory=list)
    proposed_sibling_slugs: list[str] = Field(default_factory=list)
    review_tasks: list[str] = Field(default_factory=list)


class LocalResult(Model):
    profile: Profile
    pages: list[Page]
    warnings: list[str]
    maps_candidates: list[dict[str, str]] = Field(default_factory=list)
    status: Literal["needs_review"] = "needs_review"
    limitations: list[str] = Field(default_factory=lambda: [
        "Copy and schema are drafts based on your supplied facts, not independently verified business claims.",
        "Listing candidates from OpenStreetMap are unconfirmed references; no third-party listing content or reviews are used in generated copy.",
        "Review facts, local evidence and structured data before publishing. No pages or forms are published by this pipeline.",
    ])


class LocalRun(Model):
    id: str = Field(default_factory=lambda: str(uuid4()))
    request: LocalRequest
    status: Literal["queued", "running", "complete", "failed"] = "queued"
    stage: str = "queued"
    progress: int = 0
    result: LocalResult | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
