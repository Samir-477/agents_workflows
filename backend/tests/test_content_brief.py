from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_brief.api import create_content_brief_router
from content_brief.models import ContentBriefCreate, ContentBriefDraft
from content_brief.storage import MemoryContentBriefRepository
from content_brief.validation import validate_brief
from seo_audit.config import Settings


def valid_draft(**updates) -> ContentBriefDraft:
    payload = {
        "suggested_title": "Remote team onboarding checklist for growing companies",
        "search_intent": "informational",
        "intent_confidence": "medium",
        "intent_rationale": "The query asks for a practical checklist that helps a team complete an onboarding process.",
        "reader_job": "Build a repeatable remote onboarding process without missing essential steps.",
        "recommended_format": "Practical checklist guide",
        "tone_and_voice": ["clear", "practical"],
        "target_word_count_min": 1200,
        "target_word_count_max": 1800,
        "introduction_guidance": "Define the outcome quickly, set expectations, and move the reader into the checklist.",
        "outline": [
            {"heading_level": "H2", "heading": "Remote team onboarding checklist", "purpose": "Give the reader the complete sequence at a glance.", "talking_points": ["State owners and deadlines", "Make every step actionable"], "questions_answered": [], "suggested_words": 400},
            {"heading_level": "H2", "heading": "Before the new hire starts", "purpose": "Cover preparation that prevents first-day delays.", "talking_points": ["Accounts and equipment", "Manager preparation"], "questions_answered": [], "suggested_words": 400},
            {"heading_level": "H2", "heading": "The first week and first month", "purpose": "Sequence the early milestones and feedback loops.", "talking_points": ["First-week milestones", "Thirty-day review"], "questions_answered": [], "suggested_words": 500},
        ],
        "coverage": [
            {"name": "equipment", "item_type": "topic", "why_include": "Remote workers need the correct setup before day one.", "source": "inferred"},
            {"name": "account access", "item_type": "concept", "why_include": "Access delays are a common operational dependency.", "source": "inferred"},
            {"name": "manager check-ins", "item_type": "concept", "why_include": "Check-ins make responsibilities and feedback explicit.", "source": "inferred"},
        ],
        "faqs": [{"question": "How long should remote onboarding take?", "answer_guidance": "Explain that timing varies, then provide practical milestones.", "source": "inferred"}],
        "internal_links": [],
        "conversion_notes": [],
        "assumptions": ["The reader manages a distributed team."],
        "writer_checks": ["Verify every factual claim.", "Review internal links before handoff.", "Confirm that each checklist item has an owner."],
    }
    payload.update(updates)
    return ContentBriefDraft.model_validate(payload)


def test_validation_keeps_grounded_links_and_removes_invented_links():
    request = ContentBriefCreate(
        target_keyword="remote team onboarding checklist",
        audience="HR managers at growing companies",
        existing_urls=["https://example.com/hr-guide"],
    )
    draft = valid_draft(internal_links=[
        {"target_url": "https://example.com/hr-guide", "anchor_direction": "remote hiring guide", "placement_heading": "Before the new hire starts", "reason": "The supplied guide gives readers related hiring context."},
        {"target_url": "https://example.com/invented", "anchor_direction": "invented page", "placement_heading": "Before the new hire starts", "reason": "This target was not supplied and must be removed."},
    ])
    outcome = validate_brief("brief-1", request, draft)
    assert [item.target_url for item in outcome.result.brief.internal_links] == ["https://example.com/hr-guide"]
    assert any(issue.code == "invented-internal-url" for issue in outcome.result.issues)
    assert outcome.result.ready_for_handoff is False


class FakeGenerator:
    def __init__(self):
        self.calls = 0

    async def generate(self, request, *, repair_instructions=None, previous_draft=None):
        self.calls += 1
        if self.calls == 1:
            return valid_draft(outline=[
                {"heading_level": "H3", "heading": "Details", "purpose": "This starts at the wrong heading level for testing.", "talking_points": ["One point"], "questions_answered": [], "suggested_words": 400},
                {"heading_level": "H2", "heading": "Remote team onboarding checklist", "purpose": "Give the reader the full sequence for onboarding.", "talking_points": ["Sequence"], "questions_answered": [], "suggested_words": 400},
                {"heading_level": "H2", "heading": "Final review", "purpose": "Close the process with a structured review step.", "talking_points": ["Review"], "questions_answered": [], "suggested_words": 400},
            ])
        assert repair_instructions
        assert previous_draft
        return valid_draft()


def test_api_runs_one_repair_pass_and_persists_writer_ready_result():
    repository = MemoryContentBriefRepository()
    generator = FakeGenerator()
    app = FastAPI()
    app.include_router(create_content_brief_router(Settings(), repository, generator=generator))

    with TestClient(app) as client:
        created = client.post("/api/agents/content-brief/generations", json={
            "target_keyword": "remote team onboarding checklist",
            "audience": "HR managers at growing companies",
        })
        assert created.status_code == 202
        generation_id = created.json()["generation"]["id"]
        processed = client.post(f"/api/agents/content-brief/generations/{generation_id}/process")
        result = client.get(f"/api/agents/content-brief/generations/{generation_id}/result")
        history = client.get("/api/agents/content-brief/generations")

    assert processed.status_code == 200
    assert processed.json()["generation"]["status"] == "complete"
    assert result.status_code == 200
    assert result.json()["ready_for_handoff"] is True
    assert result.json()["quality_score"] >= 90
    assert history.json()["total"] == 1
    assert generator.calls == 2


class FailedRepairGenerator:
    async def generate(self, request, *, repair_instructions=None, previous_draft=None):
        if repair_instructions:
            raise RuntimeError("provider throttled the optional repair")
        return valid_draft(outline=[
            {"heading_level": "H3", "heading": "Details", "purpose": "This starts at the wrong heading level for testing.", "talking_points": ["One point"], "questions_answered": [], "suggested_words": 400},
            {"heading_level": "H2", "heading": "Remote team onboarding checklist", "purpose": "Give the reader the complete onboarding sequence.", "talking_points": ["Sequence"], "questions_answered": [], "suggested_words": 400},
            {"heading_level": "H2", "heading": "Final review", "purpose": "Close the process with a structured review step.", "talking_points": ["Review"], "questions_answered": [], "suggested_words": 400},
        ])


def test_failed_optional_repair_saves_review_draft_instead_of_failing_run():
    repository = MemoryContentBriefRepository()
    app = FastAPI()
    app.include_router(create_content_brief_router(Settings(), repository, generator=FailedRepairGenerator()))
    with TestClient(app) as client:
        created = client.post("/api/agents/content-brief/generations", json={
            "target_keyword": "remote team onboarding checklist",
            "audience": "HR managers",
        }).json()
        generation_id = created["generation"]["id"]
        processed = client.post(f"/api/agents/content-brief/generations/{generation_id}/process")
    assert processed.json()["generation"]["status"] == "complete"
    assert processed.json()["generation"]["result"]["ready_for_handoff"] is False
    assert "optional repair pass" in processed.json()["generation"]["result"]["warnings"][0]
