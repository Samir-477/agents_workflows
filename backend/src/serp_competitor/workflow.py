from __future__ import annotations

import asyncio

from serp_competitor.analysis import compile_result
from serp_competitor.client import SerperClient
from serp_competitor.models import CompetitorEvidence
from seo_audit.crawler import SiteCrawler


async def run_serp_analysis(settings, repository, run_id: str, *, client=None, crawler=None):
    run = repository.get(run_id)
    client = client or SerperClient(settings.serper_api_key)
    crawler = crawler or SiteCrawler(settings)
    try:
        async with asyncio.timeout(260):
            cached = repository.find_fresh_result(run.request)
            if cached is not None:
                repository.update(run_id, stage="reusing_snapshot", progress=80)
                result = compile_result(
                    run,
                    cached.result.organic_results[: run.request.result_limit],
                    cached.result.questions,
                    cached.result.related_searches,
                    cached.result.answer_box,
                    cached.result.observed_at,
                    cached.result.competitors[: run.request.inspect_limit],
                    snapshot_source_run_id=cached.id,
                )
                repository.save_result(result)
                return
            repository.update(run_id, stage="searching", progress=12)
            organic, questions, related, answer_box, observed_at = await client.search(run.request)
            repository.update(run_id, stage="inspecting", progress=35)
            competitors = []
            selected = organic[: run.request.inspect_limit]
            for index, item in enumerate(selected):
                try:
                    async with asyncio.timeout(30):
                        crawl = await crawler.crawl(f"{run_id}:{item.position}", item.url, 1)
                    page = crawl.pages[0] if crawl.pages else None
                    if not page or page.fetch_error or page.status_code != 200:
                        raise ValueError("No clean HTML page was available.")
                    competitors.append(CompetitorEvidence(
                        position=item.position, url=item.url, title=page.title or item.title,
                        fetched=True, word_count=page.word_count,
                        headings=[heading.text for heading in page.headings[:40]],
                        schema_types=page.schema_types,
                        fetch_note=("Main text was truncated to the evidence limit." if page.main_text_truncated else None),
                    ))
                except Exception:
                    competitors.append(CompetitorEvidence(
                        position=item.position, url=item.url, title=item.title,
                        fetched=False,
                        fetch_note="The page could not be inspected within the safe request and crawl limits.",
                    ))
                repository.update(
                    run_id,
                    stage="inspecting",
                    progress=35 + round(40 * (index + 1) / max(1, len(selected))),
                )
            repository.update(run_id, stage="analyzing", progress=84)
            result = compile_result(
                run, organic, questions, related, answer_box, observed_at, competitors
            )
            repository.save_result(result)
    except (Exception, asyncio.CancelledError):
        repository.update(
            run_id,
            status="failed",
            stage="failed",
            progress=100,
            error="SERP analysis could not finish. Check the Serper key or quota and retry.",
        )
