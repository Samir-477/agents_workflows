from __future__ import annotations

import asyncio
import re

from content_optimizer.analysis import ContentInput, analyze_content
from seo_audit.crawler import SiteCrawler


def _markdown_headings(text: str) -> list[tuple[str, str]]:
    return [
        (f"h{len(match.group(1))}", match.group(2).strip())
        for match in re.finditer(r"^\s*(#{1,3})\s+(.+?)\s*$", text, re.MULTILINE)
    ]


async def run_content_optimizer(
    settings, repository, run_id: str, *, crawler=None, serp_repository=None,
    content_brief_repository=None,
):
    run = repository.get(run_id)
    crawler = crawler or SiteCrawler(settings)
    warnings = []
    try:
        async with asyncio.timeout(100):
            if run.request.content_url:
                repository.update(run_id, stage="fetching_page", progress=15)
                async with asyncio.timeout(60):
                    crawl = await crawler.crawl(run_id, run.request.content_url, 1)
                page = crawl.pages[0] if crawl.pages else None
                if page is None or page.fetch_error or page.status_code != 200 or not page.main_text:
                    raise ValueError("The page did not return inspectable HTML content.")
                content = ContentInput(
                    mode="url", text=page.main_text, url=page.final_url,
                    title=page.title, meta_description=page.meta_description,
                    headings=[(item.level, item.text) for item in page.headings],
                    internal_links=len(page.internal_links), external_links=len(page.external_links),
                    images_total=page.images_total, images_missing_alt=page.images_missing_alt,
                    images_empty_alt=page.images_empty_alt, schema_types=page.schema_types,
                    json_ld_errors=page.json_ld_errors,
                    truncated=page.main_text_truncated,
                )
                warnings.extend(crawl.warnings)
            else:
                repository.update(run_id, stage="reading_text", progress=20)
                content = ContentInput(
                    mode="text", text=run.request.content_text or "",
                    title=run.request.page_title, meta_description=run.request.meta_description,
                    headings=_markdown_headings(run.request.content_text or ""),
                )

            repository.update(run_id, stage="loading_research", progress=48)
            research = None
            if run.request.research_run_id:
                try:
                    candidate = serp_repository.get(run.request.research_run_id) if serp_repository else None
                    if candidate and candidate.result:
                        research = candidate.result
                    else:
                        warnings.append("The selected SERP research was not complete, so comparative checks were skipped.")
                except Exception:
                    warnings.append("The selected SERP research could not be loaded, so comparative checks were skipped.")
            brief = None
            if run.request.content_brief_id:
                try:
                    candidate = content_brief_repository.get_generation(run.request.content_brief_id) if content_brief_repository else None
                    if candidate and candidate.result:
                        brief = candidate.result
                    else:
                        warnings.append("The selected content brief was not complete, so brief coverage checks were skipped.")
                except Exception:
                    warnings.append("The selected content brief could not be loaded, so brief coverage checks were skipped.")

            repository.update(run_id, stage="analyzing", progress=72)
            result = analyze_content(run, content, research=research, brief=brief, warnings=warnings)
            repository.update(run_id, stage="finalizing", progress=92)
            repository.save_result(result)
    except (Exception, asyncio.CancelledError):
        repository.update(
            run_id, status="failed", stage="failed", progress=100,
            error="Content optimization could not finish. Check the supplied content or URL and retry.",
        )
