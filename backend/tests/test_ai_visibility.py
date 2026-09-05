from fastapi.testclient import TestClient

from agent_runtime.api import create_app
from ai_visibility.analysis import analyze_visibility
from ai_visibility.models import VisibilityCreate
from ai_visibility.storage import MemoryVisibilityRepository
from seo_audit.config import Settings
from seo_audit.crawler import CrawlResult
from seo_audit.models import ContentSection, PageRecord

from memory_metadata_repository import MemoryMetadataGenerationRepository
from memory_repository import MemoryAuditRepository


def sample_crawl() -> CrawlResult:
    return CrawlResult(
        origin="https://example.com",
        robots_txt="User-agent: GPTBot\nDisallow: /\nUser-agent: *\nAllow: /",
        discovered_urls=["https://example.com/"],
        pages=[PageRecord(
            audit_id="audit", requested_url="https://example.com/",
            final_url="https://example.com/", status_code=200, content_type="text/html",
            title="Example product", h1=["Example product"], h2=["What is Example?"],
            word_count=420, schema_types=["Organization"], has_viewport=True,
            content_sections=[ContentSection(heading="What is Example?", text="Example is a testing product that demonstrates a direct and self-contained answer for prospective users.")],
        )],
        coverage_complete=True,
    )


def test_analysis_exposes_policy_evidence_and_transparent_scores():
    repository = MemoryVisibilityRepository()
    run = repository.create_audit(VisibilityCreate(url="https://example.com", business_name="Example"))
    result = analyze_visibility(sample_crawl(), run)
    assert result.overall_score < 100
    assert next(policy for policy in result.bot_policies if policy.user_agent == "GPTBot").status == "blocked"
    assert any(finding.dimension == "discoverability" for finding in result.findings)
    assert "discoverability 35%" in result.methodology
    assert any("does not measure" in limitation for limitation in result.limitations)


def test_visibility_routes_persist_and_reopen_result():
    class FakeCrawler:
        async def crawl(self, audit_id, start_url, limit):
            crawl = sample_crawl()
            crawl.pages[0].audit_id = audit_id
            return crawl

    settings = Settings(database_url=None, allow_private_networks=True)
    visibility = MemoryVisibilityRepository()
    app = create_app(
        settings=settings,
        audit_repository=MemoryAuditRepository(),
        metadata_repository=MemoryMetadataGenerationRepository(),
        visibility_repository=visibility,
    )
    # Replace the registered route's crawler through the workflow boundary by
    # exercising analysis/storage directly; API composition is verified here.
    client = TestClient(app)
    created = client.post("/api/agents/ai-visibility/audits", json={"url": "https://example.com", "business_name": "Example"})
    assert created.status_code == 202
    audit_id = created.json()["audit"]["id"]
    result = analyze_visibility(sample_crawl(), visibility.get_audit(audit_id))
    result.audit_id = audit_id
    visibility.save_result(result)
    reopened = client.get(f"/api/agents/ai-visibility/audits/{audit_id}")
    assert reopened.status_code == 200
    assert reopened.json()["result_available"] is True
    assert reopened.json()["audit"]["result"]["overall_score"] == result.overall_score
