from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from internal_linking.analysis import AnalysisResult, analyze_crawl, compile_recommendations
from internal_linking.generation import InternalLinkRefiner
from internal_linking.models import (
    InternalLinkResult,
    InternalLinkStage,
    InternalLinkStatus,
    LinkRefinement,
)
from internal_linking.storage import InternalLinkRepository
from seo_audit.config import Settings
from seo_audit.crawler import CrawlResult, SiteCrawler
from seo_audit.url_safety import validate_public_target


class InternalLinkState(TypedDict, total=False):
    audit_id: str
    normalized_url: str
    normalized_origin: str
    crawl: CrawlResult
    analysis: AnalysisResult
    refinements: list[LinkRefinement]
    warnings: list[str]
    result: InternalLinkResult
    error: str


def build_internal_link_graph(
    settings: Settings,
    repository: InternalLinkRepository,
    *,
    crawler: SiteCrawler | None = None,
    refiner: InternalLinkRefiner | None = None,
):
    crawler = crawler or SiteCrawler(settings)
    refiner = refiner or InternalLinkRefiner(settings)

    async def validate(state: InternalLinkState) -> InternalLinkState:
        run = repository.get_audit(state["audit_id"])
        repository.update_audit(run.id, stage=InternalLinkStage.VALIDATING, progress=7)
        try:
            target = await validate_public_target(
                run.requested_url, allow_private_networks=settings.allow_private_networks
            )
            repository.update_audit(run.id, normalized_origin=target.origin)
            return {"normalized_url": target.url, "normalized_origin": target.origin, "warnings": []}
        except Exception as exc:
            return {"error": str(exc)}

    async def crawl(state: InternalLinkState) -> InternalLinkState:
        run = repository.get_audit(state["audit_id"])
        repository.update_audit(run.id, stage=InternalLinkStage.CRAWLING, progress=24)
        try:
            result = await crawler.crawl(run.id, state["normalized_url"], run.crawl_limit)
            return {"crawl": result, "normalized_origin": result.origin, "warnings": result.warnings}
        except Exception as exc:
            return {"error": str(exc)}

    def map_links(state: InternalLinkState) -> InternalLinkState:
        repository.update_audit(state["audit_id"], stage=InternalLinkStage.MAPPING, progress=52)
        try:
            run = repository.get_audit(state["audit_id"])
            return {"analysis": analyze_crawl(state["crawl"], run.important_urls)}
        except Exception as exc:
            return {"error": str(exc)}

    async def refine(state: InternalLinkState) -> InternalLinkState:
        repository.update_audit(state["audit_id"], stage=InternalLinkStage.REFINING, progress=72)
        run = repository.get_audit(state["audit_id"])
        if not state["analysis"].candidates:
            return {"refinements": []}
        try:
            draft = await refiner.refine(
                state["analysis"].candidates,
                business_description=run.business_description,
                audit_goal=run.audit_goal,
            )
            valid_ids = {candidate.id for candidate in state["analysis"].candidates}
            return {
                "refinements": [
                    item for item in draft.refinements if item.candidate_id in valid_ids
                ]
            }
        except Exception as exc:
            warning = (
                "AI wording refinement was unavailable; deterministic anchors and placement "
                f"guidance were used instead ({exc})."
            )
            return {"refinements": [], "warnings": [*state.get("warnings", []), warning]}

    def finalize(state: InternalLinkState) -> InternalLinkState:
        repository.update_audit(
            state["audit_id"], stage=InternalLinkStage.VALIDATING_RESULTS, progress=90
        )
        try:
            run = repository.get_audit(state["audit_id"])
            crawl_result = state["crawl"]
            analysis = state["analysis"]
            refinements = state.get("refinements", [])
            warnings = list(dict.fromkeys(state.get("warnings", [])))
            limitations = []
            if not crawl_result.coverage_complete:
                limitations.append(
                    "The crawler did not establish complete site coverage. Zero observed inbound "
                    "links are labelled orphan candidates, not confirmed orphan pages."
                )
            if len(crawl_result.pages) < 2:
                limitations.append(
                    "Fewer than two HTML pages were available, so cross-page link opportunities "
                    "could not be assessed reliably."
                )
            result = InternalLinkResult(
                audit_id=run.id,
                requested_url=run.requested_url,
                normalized_origin=crawl_result.origin,
                pages_crawled=len(crawl_result.pages),
                discovered_url_count=max(
                    len(crawl_result.discovered_urls), len(crawl_result.pages)
                ),
                coverage_complete=crawl_result.coverage_complete,
                observed_edge_count=analysis.observed_edge_count,
                contextual_edge_count=analysis.contextual_edge_count,
                confirmed_orphan_count=analysis.confirmed_orphan_count,
                orphan_candidate_count=analysis.orphan_candidate_count,
                weak_anchor_count=analysis.weak_anchor_count,
                recommendations=compile_recommendations(
                    analysis.candidates, refinements
                ),
                pages=analysis.pages,
                warnings=warnings,
                limitations=limitations,
                generated_with_llm=bool(refinements),
            )
            repository.save_result(result)
            return {"result": result}
        except Exception as exc:
            return {"error": str(exc)}

    def fail(state: InternalLinkState) -> InternalLinkState:
        message = state.get("error", "The internal-link audit failed unexpectedly.")
        repository.update_audit(
            state["audit_id"], status=InternalLinkStatus.FAILED,
            stage=InternalLinkStage.FAILED, progress=100, error=message,
        )
        return {"error": message}

    def route(state: InternalLinkState) -> str:
        return "fail" if state.get("error") else "continue"

    graph = StateGraph(InternalLinkState)
    graph.add_node("validate", validate)
    graph.add_node("crawl", crawl)
    graph.add_node("map_links", map_links)
    graph.add_node("refine", refine)
    graph.add_node("finalize", finalize)
    graph.add_node("fail", fail)
    graph.add_edge(START, "validate")
    graph.add_conditional_edges("validate", route, {"continue": "crawl", "fail": "fail"})
    graph.add_conditional_edges("crawl", route, {"continue": "map_links", "fail": "fail"})
    graph.add_conditional_edges("map_links", route, {"continue": "refine", "fail": "fail"})
    graph.add_conditional_edges("refine", route, {"continue": "finalize", "fail": "fail"})
    graph.add_conditional_edges("finalize", route, {"continue": END, "fail": "fail"})
    graph.add_edge("fail", END)
    return graph.compile()
