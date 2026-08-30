from pathlib import Path

import pytest

from seo_audit.config import Settings
from seo_audit.crawler import CrawlResult
from seo_audit.models import AuditCreate, AuditStatus
from memory_repository import MemoryAuditRepository
from seo_audit.url_safety import ValidatedTarget
from seo_audit.workflow import build_audit_graph


class RobotsBlockedCrawler:
    async def crawl(self, audit_id: str, start_url: str, limit: int) -> CrawlResult:
        return CrawlResult(
            pages=[],
            origin="https://example.com",
            warnings=[
                "robots.txt disallowed 1 discovered URL(s) for the audit user-agent.",
                "robots.txt disallowed the redirected start URL: https://example.com/",
            ],
        )


async def fake_validator(url: str, **_: object) -> ValidatedTarget:
    return ValidatedTarget(url=url, origin="https://example.com")


@pytest.mark.asyncio
async def test_robots_block_produces_limited_report_without_score(tmp_path: Path):
    settings = Settings(report_output_dir=tmp_path / "reports")
    repository = MemoryAuditRepository()
    repository.initialize()
    audit = repository.create_audit(AuditCreate(url="https://example.com/"), 10)
    repository.claim_next_audit()
    graph = build_audit_graph(
        settings,
        repository,
        crawler=RobotsBlockedCrawler(),
        target_validator=fake_validator,
    )

    await graph.ainvoke({"audit_id": audit.id})

    completed = repository.get_audit(audit.id)
    report = repository.get_report(audit.id)
    assert completed.status == AuditStatus.COMPLETE
    assert report is not None
    assert report.pages_crawled == 0
    assert report.site_score is None
    assert [item.rule_id for item in report.findings] == ["audit_blocked_by_robots"]
