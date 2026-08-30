from pathlib import Path

import pytest

from seo_audit.config import Settings
from seo_audit.crawler import CrawlResult
from seo_audit.models import AuditCreate, AuditStatus, PageRecord
from memory_repository import MemoryAuditRepository
from seo_audit.url_safety import ValidatedTarget
from seo_audit.workflow import build_audit_graph


class FakeCrawler:
    async def crawl(self, audit_id: str, start_url: str, limit: int) -> CrawlResult:
        page = PageRecord(
            audit_id=audit_id,
            requested_url=start_url,
            final_url=start_url,
            status_code=200,
            depth=0,
            content_type="text/html",
            title="Example",
            canonical=start_url,
            h1=["Example"],
            word_count=350,
            has_viewport=True,
        )
        return CrawlResult(pages=[page], origin="https://example.com")


async def fake_validator(url: str, **_: object) -> ValidatedTarget:
    return ValidatedTarget(url=url, origin="https://example.com")


@pytest.mark.asyncio
async def test_graph_completes_a_queued_audit(tmp_path: Path):
    settings = Settings(report_output_dir=tmp_path / "reports", crawl_delay_seconds=0)
    repository = MemoryAuditRepository()
    repository.initialize()
    audit = repository.create_audit(
        AuditCreate(url="https://example.com", business_description="Example business"),
        crawl_limit=10,
    )
    claimed = repository.claim_next_audit()
    assert claimed and claimed.id == audit.id

    graph = build_audit_graph(
        settings,
        repository,
        crawler=FakeCrawler(),
        target_validator=fake_validator,
    )
    result = await graph.ainvoke({"audit_id": audit.id})

    assert result["report_saved"] is True
    completed = repository.get_audit(audit.id)
    assert completed.status == AuditStatus.COMPLETE
    report = repository.get_report(audit.id)
    assert report is not None
    assert report.pages_crawled == 1
    assert report.site_score is not None
    assert report.generated_with_llm is False
    assert (tmp_path / "reports" / f"{audit.id}.md").exists()
