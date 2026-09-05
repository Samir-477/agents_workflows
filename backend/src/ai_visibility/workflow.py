from __future__ import annotations

from ai_visibility.analysis import analyze_visibility
from ai_visibility.models import VisibilityStage, VisibilityStatus
from seo_audit.crawler import SiteCrawler
from seo_audit.url_safety import validate_public_target


async def run_visibility_audit(settings, repository, audit_id: str, crawler=None):
    crawler = crawler or SiteCrawler(settings)
    run = repository.get_audit(audit_id)
    try:
        repository.update_audit(audit_id, stage=VisibilityStage.VALIDATING, progress=8)
        target = await validate_public_target(run.requested_url, allow_private_networks=settings.allow_private_networks)
        repository.update_audit(audit_id, normalized_origin=target.origin)
        repository.update_audit(audit_id, stage=VisibilityStage.CRAWLING, progress=25)
        crawl = await crawler.crawl(audit_id, target.url, run.crawl_limit)
        repository.update_audit(audit_id, stage=VisibilityStage.ANALYZING, progress=65, warnings=crawl.warnings)
        result = analyze_visibility(crawl, repository.get_audit(audit_id))
        repository.update_audit(audit_id, stage=VisibilityStage.SCORING, progress=90)
        repository.save_result(result)
    except Exception as exc:
        repository.update_audit(audit_id, status=VisibilityStatus.FAILED, stage=VisibilityStage.FAILED, progress=100, error=str(exc))
    return repository.get_audit(audit_id)
