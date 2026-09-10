"""Run all ten agents against one resort page URL, in dependency order.

Each child agent keeps its own repository, its own validation, its own honesty
rules exactly as built. This module's only job is: derive what a URL-only input
cannot supply (a keyword, a set of facts), create a normal run in each agent's
own system, and record what happened. One agent failing does not stop the rest —
every agent gets a real attempt and its own outcome, always.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ai_visibility.models import VisibilityCreate
from ai_visibility.storage import VisibilityRepository
from ai_visibility.workflow import run_visibility_audit
from content_brief.generation import ContentBriefGenerator
from content_brief.models import ContentBriefCreate
from content_brief.storage import ContentBriefRepository
from content_brief.workflow import build_content_brief_graph
from content_optimizer.models import ContentOptimizerRequest
from content_optimizer.storage import ContentOptimizerRepository
from content_optimizer.workflow import run_content_optimizer
from internal_linking.generation import InternalLinkRefiner
from internal_linking.models import InternalLinkCreate
from internal_linking.storage import InternalLinkRepository
from internal_linking.workflow import build_internal_link_graph
from keyword_cluster.generation import KeywordClusterGenerator
from keyword_cluster.models import KeywordClusterCreate
from keyword_cluster.storage import KeywordClusterRepository
from keyword_cluster.workflow import build_keyword_cluster_graph
from local_seo.generation import LocalGenerator
from local_seo.models import LocalRequest
from local_seo.pipeline import generate_run as run_local_seo_pipeline
from local_seo.storage import LocalRepository
from meta_generator.generation import MetadataGenerator
from meta_generator.models import MetadataGenerationCreate
from meta_generator.storage import MetadataGenerationRepository
from meta_generator.workflow import build_metadata_graph
from resort_orchestrator.context import build_fact_narrative, derive_keyword_from_url, fetch_page_facts
from resort_orchestrator.models import AgentOutcome, OrchestratorRecord
from resort_orchestrator.storage import MemoryOrchestratorRepository, OrchestratorRepository
from schema_generator.generation import SchemaInterpreter
from schema_generator.models import SchemaGenerationCreate
from schema_generator.storage import SchemaGenerationRepository
from schema_generator.workflow import build_schema_graph
from seo_audit.config import Settings
from seo_audit.crawler import SiteCrawler
from seo_audit.models import AuditCreate
from seo_audit.reporting import ReportWriter
from seo_audit.storage import AuditRepository
from seo_audit.workflow import build_audit_graph
from serp_competitor.models import SerpRequest
from serp_competitor.storage import SerpRepository
from serp_competitor.workflow import run_serp_analysis

logger = logging.getLogger(__name__)

_DEFAULT_AUDIENCE = "Travellers researching this destination"
_DEFAULT_GOAL = "Help visitors evaluate this property and decide whether to book"
_LLM_STAGE_PACE_SECONDS = 18


class Dependencies:
    """Every child agent's repository/generator, constructed once in agent_runtime.

    The orchestrator never builds its own copies — it reuses exactly the same
    instances the rest of the app uses, so provider settings, database
    connections and everything else stay identical to a manually-run agent.
    """

    def __init__(
        self, *, settings: Settings, crawler: SiteCrawler,
        audit_repository: AuditRepository, report_writer: ReportWriter,
        visibility_repository: VisibilityRepository,
        internal_link_repository: InternalLinkRepository, internal_link_refiner: InternalLinkRefiner,
        serp_repository: SerpRepository,
        keyword_cluster_repository: KeywordClusterRepository, keyword_cluster_generator: KeywordClusterGenerator,
        metadata_repository: MetadataGenerationRepository, metadata_generator: MetadataGenerator,
        schema_repository: SchemaGenerationRepository, schema_interpreter: SchemaInterpreter,
        content_brief_repository: ContentBriefRepository, content_brief_generator: ContentBriefGenerator,
        local_repository: LocalRepository, local_generator: LocalGenerator,
        content_optimizer_repository: ContentOptimizerRepository,
    ) -> None:
        self.settings = settings
        self.crawler = crawler
        self.audit_repository = audit_repository
        self.report_writer = report_writer
        self.visibility_repository = visibility_repository
        self.internal_link_repository = internal_link_repository
        self.internal_link_refiner = internal_link_refiner
        self.serp_repository = serp_repository
        self.keyword_cluster_repository = keyword_cluster_repository
        self.keyword_cluster_generator = keyword_cluster_generator
        self.metadata_repository = metadata_repository
        self.metadata_generator = metadata_generator
        self.schema_repository = schema_repository
        self.schema_interpreter = schema_interpreter
        self.content_brief_repository = content_brief_repository
        self.content_brief_generator = content_brief_generator
        self.local_repository = local_repository
        self.local_generator = local_generator
        self.content_optimizer_repository = content_optimizer_repository


async def _safe(agent: str, coro) -> AgentOutcome:
    """Never let one agent's exception take down the other nine."""
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 - genuinely must not propagate
        logger.warning("resort orchestrator: %s failed: %s", agent, exc)
        return AgentOutcome(agent=agent, status="failed", error=str(exc))


async def _run_seo_audit(deps: Dependencies, page_url: str) -> AgentOutcome:
    run = deps.audit_repository.create_audit(
        AuditCreate(url=page_url, business_description="Resort orchestrator: single-page diagnosis.", crawl_limit=1),
        crawl_limit=1,
    )
    await build_audit_graph(deps.settings, deps.audit_repository, crawler=deps.crawler, report_writer=deps.report_writer).ainvoke(
        {"audit_id": run.id}
    )
    final = deps.audit_repository.get_audit(run.id)
    if final.status.value == "failed":
        return AgentOutcome(agent="seo_audit", run_id=run.id, status="failed", error=final.error)
    report = deps.audit_repository.get_report(run.id)
    summary = {
        "site_score": report.site_score,
        "severity_counts": report.severity_counts,
        "top_findings": [f.title for f in report.findings[:5]],
    }
    return AgentOutcome(agent="seo_audit", run_id=run.id, status="complete", summary=summary)


async def _run_ai_visibility(deps: Dependencies, page_url: str) -> AgentOutcome:
    run = deps.visibility_repository.create_audit(VisibilityCreate(url=page_url, crawl_limit=1), default_limit=1)
    await run_visibility_audit(deps.settings, deps.visibility_repository, run.id, crawler=deps.crawler)
    final = deps.visibility_repository.get_audit(run.id)
    if final.status.value == "failed":
        return AgentOutcome(agent="ai_visibility", run_id=run.id, status="failed", error=final.error)
    result = final.result
    summary = {
        "overall_score": result.overall_score,
        "dimensions": {d.dimension: d.score for d in result.dimensions},
        "top_findings": [f.title for f in result.findings[:5]],
    }
    return AgentOutcome(agent="ai_visibility", run_id=run.id, status="complete", summary=summary)


async def _run_internal_linking(deps: Dependencies, page_url: str) -> AgentOutcome:
    # Deliberately wider than the other crawlers: this agent's entire value is
    # cross-page context, which a single-page crawl cannot provide at all.
    run = deps.internal_link_repository.create_audit(
        InternalLinkCreate(url=page_url, important_urls=[page_url], audit_goal="Resort orchestrator: find contextual links into and out of this page.", crawl_limit=20)
    )
    await build_internal_link_graph(
        deps.settings, deps.internal_link_repository, crawler=deps.crawler, refiner=deps.internal_link_refiner
    ).ainvoke({"audit_id": run.id})
    final = deps.internal_link_repository.get_audit(run.id)
    if final.status.value == "failed":
        return AgentOutcome(agent="internal_linking", run_id=run.id, status="failed", error=final.error)
    result = final.result
    summary = {
        "pages_crawled": result.pages_crawled,
        "contextual_edge_count": result.contextual_edge_count,
        "recommendation_count": len(result.recommendations),
        "top_recommendations": [
            f"{r.source_url} -> {r.target_url}" for r in result.recommendations[:3]
        ],
    }
    return AgentOutcome(agent="internal_linking", run_id=run.id, status="complete", summary=summary)


async def _run_serp(deps: Dependencies, keyword: str) -> tuple[AgentOutcome, Any]:
    run = deps.serp_repository.create(SerpRequest(target_keyword=keyword))
    await run_serp_analysis(deps.settings, deps.serp_repository, run.id, crawler=deps.crawler)
    final = deps.serp_repository.get(run.id)
    if final.status != "complete" or not final.result:
        return AgentOutcome(agent="serp_competitor", run_id=run.id, status="failed", error=final.error), None
    result = final.result
    summary = {
        "search_intent": result.search_intent,
        "organic_result_count": len(result.organic_results),
        "median_word_count": result.median_word_count,
        "top_competitor_titles": [item.title for item in result.organic_results[:5]],
    }
    return AgentOutcome(agent="serp_competitor", run_id=run.id, status="complete", summary=summary), result


def _keyword_seed_list(base_keyword: str, serp_result: Any) -> str:
    """Real external search signal, not the target page's own words.

    Feeding Keyword Cluster the target page's own headings would just cluster
    its existing vocabulary back into a plan that restates itself. SERP results
    carry real competitor language and real questions instead.
    """
    seeds: list[str] = [base_keyword]
    if serp_result is not None:
        seeds.extend(item.title for item in serp_result.organic_results[:8])
        seeds.extend(q.question for q in serp_result.questions[:6])
        seeds.extend(serp_result.related_searches[:8])
        seeds.extend(p.label for p in serp_result.common_headings[:6])
    seen: set[str] = set()
    unique: list[str] = []
    for line in seeds:
        cleaned = " ".join(line.split())
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            unique.append(cleaned)
    while len(unique) < 3:
        unique.append(f"{base_keyword} {['guide', 'reviews', 'booking'][len(unique) % 3]}")
    return "\n".join(unique)


async def _run_keyword_cluster(deps: Dependencies, keyword: str, serp_result: Any) -> AgentOutcome:
    run = deps.keyword_cluster_repository.create_generation(
        KeywordClusterCreate(keywords=_keyword_seed_list(keyword, serp_result))
    )
    await build_keyword_cluster_graph(
        deps.settings, deps.keyword_cluster_repository, generator=deps.keyword_cluster_generator
    ).ainvoke({"generation_id": run.id})
    final = deps.keyword_cluster_repository.get_generation(run.id)
    if final.status.value == "failed":
        return AgentOutcome(agent="keyword_cluster", run_id=run.id, status="failed", error=final.error)
    result = final.result
    summary = {
        "unique_keyword_count": result.unique_keyword_count,
        "cluster_count": len(result.clusters),
        "pillar_count": len(result.pillars),
        "seeded_from": "serp_competitor" if serp_result else "target keyword only",
    }
    return AgentOutcome(agent="keyword_cluster", run_id=run.id, status="complete", summary=summary)


async def _run_metadata(deps: Dependencies, narrative: str, keyword: str) -> AgentOutcome:
    prompt = (
        f"Generate metadata for one existing resort page. Primary keyword: {keyword}. "
        f"Preserve the resort's own identity. English.\n\n{narrative}"
    )
    run = deps.metadata_repository.create_generation(MetadataGenerationCreate(prompt=prompt))
    await build_metadata_graph(deps.settings, deps.metadata_repository, generator=deps.metadata_generator).ainvoke(
        {"generation_id": run.id}
    )
    final = deps.metadata_repository.get_generation(run.id)
    if final.status.value == "failed":
        return AgentOutcome(agent="metadata", run_id=run.id, status="failed", error=final.error)
    page = final.result.pages[0]
    recommended_title = next((t for t in page.titles if t.recommended), page.titles[0])
    recommended_description = next((d for d in page.descriptions if d.recommended), page.descriptions[0])
    summary = {
        "recommended_title": recommended_title.text,
        "recommended_description": recommended_description.text,
        "warning_count": len(page.warnings),
    }
    return AgentOutcome(agent="metadata", run_id=run.id, status="complete", summary=summary)


async def _run_schema(deps: Dependencies, narrative: str) -> AgentOutcome:
    prompt = (
        "Suggest structured data for this existing resort page using only supplied facts. "
        "Identify missing required information; do not invent an address, aggregateRating or "
        f"FAQ answers.\n\n{narrative}"
    )
    run = deps.schema_repository.create_generation(SchemaGenerationCreate(prompt=prompt))
    await build_schema_graph(deps.settings, deps.schema_repository, interpreter=deps.schema_interpreter).ainvoke(
        {"generation_id": run.id}
    )
    final = deps.schema_repository.get_generation(run.id)
    if final.status.value == "failed":
        return AgentOutcome(agent="schema_markup", run_id=run.id, status="failed", error=final.error)
    result = final.result
    summary = {
        "publish_ready": result.publish_ready,
        "blocking_issue_count": result.blocking_issue_count,
        "types": [b.schema_type for b in result.blocks],
    }
    return AgentOutcome(agent="schema_markup", run_id=run.id, status="complete", summary=summary)


async def _run_content_brief(
    deps: Dependencies, keyword: str, narrative: str, page_url: str, audience: str | None, goal: str | None,
) -> AgentOutcome:
    resolved_audience = audience or _DEFAULT_AUDIENCE
    resolved_goal = goal or _DEFAULT_GOAL
    run = deps.content_brief_repository.create_generation(ContentBriefCreate(
        target_keyword=keyword, audience=resolved_audience, business_goal=resolved_goal,
        product_context=narrative[:1900], existing_urls=[page_url], source_notes=narrative[:7900],
        content_mode="rewrite",
    ))
    await build_content_brief_graph(deps.settings, deps.content_brief_repository, generator=deps.content_brief_generator).ainvoke(
        {"generation_id": run.id}
    )
    final = deps.content_brief_repository.get_generation(run.id)
    if final.status.value == "failed":
        return AgentOutcome(agent="content_brief", run_id=run.id, status="failed", error=final.error)
    result = final.result
    summary = {
        "quality_score": result.quality_score,
        "ready_for_handoff": result.ready_for_handoff,
        "suggested_title": result.brief.suggested_title,
        "audience_confirmed": audience is not None,
        "goal_confirmed": goal is not None,
    }
    return AgentOutcome(agent="content_brief", run_id=run.id, status="complete", summary=summary)


async def _run_local_seo(deps: Dependencies, narrative: str, page_url: str) -> AgentOutcome:
    run = deps.local_repository.create(LocalRequest(prompt=narrative, existing_urls=[page_url], lookup_maps=False))

    def _progress(stage: str, progress: int) -> None:
        deps.local_repository.mutate(run.id, stage=stage, progress=progress)

    deps.local_repository.mutate(run.id, expected={"queued"}, status="running", stage="extracting", progress=5)
    try:
        result = await run_local_seo_pipeline(run.request, deps.local_generator, _progress)
        deps.local_repository.mutate(run.id, result=result, status="complete", stage="complete", progress=100)
    except Exception as exc:
        deps.local_repository.mutate(run.id, status="failed", stage="failed", error=str(exc))
        return AgentOutcome(agent="local_seo", run_id=run.id, status="failed", error=str(exc))
    summary = {
        "status": result.status,
        "page_count": len(result.pages),
        "warning_count": len(result.warnings),
    }
    return AgentOutcome(agent="local_seo", run_id=run.id, status="complete", summary=summary)


async def _run_content_optimizer(
    deps: Dependencies, page_url: str, keyword: str, audience: str | None,
    serp_run_id: str | None, content_brief_run_id: str | None,
) -> AgentOutcome:
    run = deps.content_optimizer_repository.create(ContentOptimizerRequest(
        content_url=page_url, target_keyword=keyword, audience=audience or _DEFAULT_AUDIENCE,
        research_run_id=serp_run_id, content_brief_id=content_brief_run_id,
    ))
    await run_content_optimizer(
        deps.settings, deps.content_optimizer_repository, run.id, crawler=deps.crawler,
        serp_repository=deps.serp_repository, content_brief_repository=deps.content_brief_repository,
    )
    final = deps.content_optimizer_repository.get(run.id)
    if final.status != "complete" or not final.result:
        return AgentOutcome(agent="content_optimizer", run_id=run.id, status="failed", error=final.error)
    result = final.result
    summary = {
        "overall_score": result.overall_score,
        "assessed_checks": f"{result.assessed_checks}/{result.total_checks}",
        "action_count": len(result.actions),
        "linked_serp_run": bool(result.research_run_id),
        "linked_content_brief": bool(result.content_brief_id),
    }
    return AgentOutcome(agent="content_optimizer", run_id=run.id, status="complete", summary=summary)


def _assemble_report(record: OrchestratorRecord) -> dict[str, Any]:
    order = [
        "seo_audit", "ai_visibility", "internal_linking", "serp_competitor",
        "keyword_cluster", "metadata", "schema_markup", "content_brief",
        "local_seo", "content_optimizer",
    ]
    return {
        "page_url": record.page_url,
        "derived_keyword": record.derived_keyword,
        "agents": [record.outcomes[key].model_dump(mode="json") for key in order if key in record.outcomes],
        "completed_count": sum(1 for o in record.outcomes.values() if o.status == "complete"),
        "failed_count": sum(1 for o in record.outcomes.values() if o.status == "failed"),
    }


async def run_orchestration(deps: Dependencies, repository: OrchestratorRepository | MemoryOrchestratorRepository, run_id: str) -> None:
    run = repository.get(run_id)
    outcomes: dict[str, AgentOutcome] = {}
    warnings: list[str] = []

    def save(stage: str, progress: int) -> None:
        repository.update(run_id, stage=stage, progress=progress, outcomes=dict(outcomes))

    try:
        save("reading_page", 5)
        facts, fetch_warnings = await fetch_page_facts(deps.settings, run.page_url)
        warnings.extend(fetch_warnings)
        keyword = derive_keyword_from_url(run.page_url)
        narrative = build_fact_narrative(facts, keyword)
        repository.update(run_id, derived_keyword=keyword, warnings=warnings)

        save("seo_audit", 12)
        outcomes["seo_audit"] = await _safe("seo_audit", _run_seo_audit(deps, run.page_url))

        save("ai_visibility", 22)
        outcomes["ai_visibility"] = await _safe("ai_visibility", _run_ai_visibility(deps, run.page_url))

        save("internal_linking", 32)
        outcomes["internal_linking"] = await _safe("internal_linking", _run_internal_linking(deps, run.page_url))

        save("serp_competitor", 42)
        serp_outcome, serp_result = await _safe_serp(deps, keyword)
        outcomes["serp_competitor"] = serp_outcome

        # Every agent's own per-call token budget already fits the free tier's 1,000
        # output-tokens-per-minute ceiling in isolation. That ceiling is account-wide
        # and rolling, though: run several LLM-calling agents back to back with no
        # gap and their calls stack inside the same window and the later ones get
        # refused outright. A short pause between stages is cheaper than a retry loop.
        await asyncio.sleep(_LLM_STAGE_PACE_SECONDS)
        save("keyword_cluster", 50)
        outcomes["keyword_cluster"] = await _safe("keyword_cluster", _run_keyword_cluster(deps, keyword, serp_result))

        await asyncio.sleep(_LLM_STAGE_PACE_SECONDS)
        save("metadata", 58)
        outcomes["metadata"] = await _safe("metadata", _run_metadata(deps, narrative, keyword))

        await asyncio.sleep(_LLM_STAGE_PACE_SECONDS)
        save("schema_markup", 66)
        outcomes["schema_markup"] = await _safe("schema_markup", _run_schema(deps, narrative))

        await asyncio.sleep(_LLM_STAGE_PACE_SECONDS)
        save("content_brief", 74)
        outcomes["content_brief"] = await _safe(
            "content_brief", _run_content_brief(deps, keyword, narrative, run.page_url, run.audience, run.business_goal)
        )
        content_brief_run_id = outcomes["content_brief"].run_id if outcomes["content_brief"].status == "complete" else None

        await asyncio.sleep(_LLM_STAGE_PACE_SECONDS)
        save("local_seo", 82)
        outcomes["local_seo"] = await _safe("local_seo", _run_local_seo(deps, narrative, run.page_url))

        await asyncio.sleep(_LLM_STAGE_PACE_SECONDS)
        save("content_optimizer", 90)
        outcomes["content_optimizer"] = await _safe(
            "content_optimizer",
            _run_content_optimizer(
                deps, run.page_url, keyword, run.audience,
                serp_outcome.run_id if serp_outcome.status == "complete" else None,
                content_brief_run_id,
            ),
        )

        save("assembling_report", 96)
        current = repository.get(run_id)
        report = _assemble_report(current.model_copy(update={"outcomes": outcomes}))
        repository.update(
            run_id, status="complete", stage="complete", progress=100,
            outcomes=outcomes, report=report, warnings=warnings,
        )
    except Exception as exc:
        logger.exception("resort orchestrator run %s failed outright", run_id)
        repository.update(
            run_id, status="failed", stage="failed", progress=100,
            outcomes=outcomes, error=str(exc), warnings=warnings,
        )


async def _safe_serp(deps: Dependencies, keyword: str) -> tuple[AgentOutcome, Any]:
    try:
        return await _run_serp(deps, keyword)
    except Exception as exc:  # noqa: BLE001
        logger.warning("resort orchestrator: serp_competitor failed: %s", exc)
        return AgentOutcome(agent="serp_competitor", status="failed", error=str(exc)), None
