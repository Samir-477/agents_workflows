from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from internal_linking.analysis import analyze_crawl, compile_recommendations
from internal_linking.api import create_internal_link_router
from internal_linking.models import InternalLinkCreate, LinkRefinementSet
from internal_linking.storage import MemoryInternalLinkRepository
from seo_audit.config import Settings
from seo_audit.crawler import CrawlResult
from seo_audit.models import ContentSection, LinkRecord, PageRecord
from seo_audit.url_safety import ValidatedTarget


def page(path: str, title: str, links: list[LinkRecord] | None = None) -> PageRecord:
    url = f"https://example.com{path}"
    return PageRecord(
        audit_id="audit", requested_url=url, final_url=url, status_code=200,
        title=title, h1=[title], internal_links=links or [],
        link_occurrences=links or [],
        content_sections=[ContentSection(heading=title, text=f"Practical guidance about {title} for small businesses.")],
    )


def test_partial_crawl_labels_zero_inbound_as_candidate_and_detects_weak_anchor():
    pricing = page("/pricing", "CRM pricing plans")
    guide = page("/guide", "CRM buying guide", [LinkRecord(
        url=pricing.final_url, anchor_text="click here", placement="content",
        section_heading="Compare CRM plans", context_text="Compare CRM plans for your team.",
    )])
    hidden = page("/integrations", "CRM integrations")
    result = analyze_crawl(
        CrawlResult(
            pages=[page("/", "CRM software", [LinkRecord(url=guide.final_url, anchor_text="CRM guide")]), guide, pricing, hidden],
            origin="https://example.com", coverage_complete=False,
        ),
        [pricing.final_url],
    )
    summaries = {item.url: item for item in result.pages}
    assert summaries[hidden.final_url].orphan_status == "candidate"
    assert summaries[pricing.final_url].orphan_status == "not_orphan"
    assert any(item.recommendation_type == "weak_anchor" and item.current_anchor == "click here" for item in result.candidates)


def test_complete_crawl_can_confirm_orphan_and_never_recommends_an_existing_pair():
    target = page("/services", "Payroll services")
    source = page("/guide", "Payroll guide")
    home = page("/", "Payroll company", [LinkRecord(url=source.final_url, anchor_text="Payroll guide")])
    analysis = analyze_crawl(
        CrawlResult(
            pages=[home, source, target], origin="https://example.com",
            sitemap_urls=[home.final_url, source.final_url, target.final_url], coverage_complete=True,
        ),
        [target.final_url],
    )
    assert next(item for item in analysis.pages if item.url == target.final_url).orphan_status == "confirmed"
    assert any(item.target_url == target.final_url and item.recommendation_type == "orphan" for item in analysis.candidates)
    assert not any(item.source_url == home.final_url and item.target_url == source.final_url for item in analysis.candidates)


def test_invalid_ai_anchor_is_replaced_by_deterministic_target_title():
    target = page("/pricing", "CRM pricing plans")
    source = page("/guide", "CRM buying guide")
    candidate = analyze_crawl(
        CrawlResult(pages=[page("/", "CRM"), source, target], origin="https://example.com", coverage_complete=True),
        [target.final_url],
    ).candidates[0]
    recommendations = compile_recommendations([candidate], [])
    assert recommendations[0].anchor_options == [candidate.target_title]
    assert recommendations[0].score_factors


class FakeCrawler:
    async def crawl(self, audit_id: str, start_url: str, limit: int):
        target = page("/pricing", "CRM pricing")
        return CrawlResult(
            pages=[page("/", "CRM software"), page("/guide", "CRM pricing guide"), target],
            origin="https://example.com", discovered_urls=["https://example.com/", target.final_url],
            coverage_complete=True,
        )


class FakeRefiner:
    async def refine(self, candidates, business_description=None, audit_goal=None):
        return LinkRefinementSet(refinements=[])


def test_api_create_process_result_delete_cycle(monkeypatch):
    async def validate(url: str, *, allow_private_networks: bool = False):
        return ValidatedTarget(url="https://example.com/", origin="https://example.com")

    monkeypatch.setattr("internal_linking.workflow.validate_public_target", validate)
    repository = MemoryInternalLinkRepository()
    app = FastAPI()
    app.include_router(create_internal_link_router(
        Settings(), repository, crawler=FakeCrawler(), refiner=FakeRefiner()
    ))
    with TestClient(app) as client:
        created = client.post("/api/agents/internal-linking/audits", json={"url": "https://example.com", "crawl_limit": 10})
        assert created.status_code == 202
        audit_id = created.json()["audit"]["id"]
        processed = client.post(f"/api/agents/internal-linking/audits/{audit_id}/process")
        assert processed.status_code == 200
        result = client.get(f"/api/agents/internal-linking/audits/{audit_id}/result")
        assert result.status_code == 200
        assert result.json()["coverage_complete"] is True
        assert result.json()["recommendations"]
        assert client.delete(f"/api/agents/internal-linking/audits/{audit_id}").status_code == 204
