from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from keyword_cluster.generation import KeywordClusterGenerator
from keyword_cluster.models import (
    CandidateCluster,
    ConsolidatedClusterSet,
    KeywordClusterResult,
    KeywordClusterStage,
    KeywordClusterStatus,
    KeywordItem,
)
from keyword_cluster.parsing import parse_keywords
from keyword_cluster.planning import compile_plan
from keyword_cluster.storage import KeywordClusterRepository
from seo_audit.config import Settings


class KeywordClusterWorkflowState(TypedDict, total=False):
    generation_id: str
    keywords: list[KeywordItem]
    duplicate_count: int
    warnings: list[str]
    candidates: list[CandidateCluster]
    draft: ConsolidatedClusterSet
    result: KeywordClusterResult
    error: str


def build_keyword_cluster_graph(
    settings: Settings,
    repository: KeywordClusterRepository,
    *,
    generator: KeywordClusterGenerator | None = None,
):
    generator = generator or KeywordClusterGenerator(settings)

    def parse(state: KeywordClusterWorkflowState) -> KeywordClusterWorkflowState:
        run = repository.get_generation(state["generation_id"])
        repository.update_generation(run.id, status=KeywordClusterStatus.RUNNING, stage=KeywordClusterStage.PARSING, progress=8)
        try:
            keywords, duplicates, warnings = parse_keywords(run.raw_keywords)
            if len(keywords) < 3:
                raise ValueError("At least three unique keywords are required")
            repository.save_keywords(run.id, keywords, warnings)
            return {"keywords": keywords, "duplicate_count": duplicates, "warnings": warnings}
        except Exception as exc:
            return {"error": str(exc)}

    async def cluster(state: KeywordClusterWorkflowState) -> KeywordClusterWorkflowState:
        repository.update_generation(state["generation_id"], status=KeywordClusterStatus.RUNNING, stage=KeywordClusterStage.CLUSTERING, progress=28)
        try:
            return {"candidates": await generator.create_candidates(state["keywords"])}
        except Exception as exc:
            return {"error": str(exc)}

    async def consolidate(state: KeywordClusterWorkflowState) -> KeywordClusterWorkflowState:
        repository.update_generation(state["generation_id"], status=KeywordClusterStatus.RUNNING, stage=KeywordClusterStage.CONSOLIDATING, progress=62)
        try:
            return {"draft": await generator.consolidate(state["keywords"], state["candidates"])}
        except Exception as exc:
            return {"error": str(exc)}

    def plan(state: KeywordClusterWorkflowState) -> KeywordClusterWorkflowState:
        repository.update_generation(state["generation_id"], status=KeywordClusterStatus.RUNNING, stage=KeywordClusterStage.PLANNING, progress=82)
        try:
            run = repository.get_generation(state["generation_id"])
            input_count = len([line for line in run.raw_keywords.splitlines() if line.strip()])
            return {"result": compile_plan(
                run.id, state["keywords"], state["draft"], input_count=input_count,
                duplicate_count=state["duplicate_count"], warnings=state["warnings"],
            )}
        except Exception as exc:
            return {"error": str(exc)}

    def validate(state: KeywordClusterWorkflowState) -> KeywordClusterWorkflowState:
        repository.update_generation(state["generation_id"], status=KeywordClusterStatus.RUNNING, stage=KeywordClusterStage.VALIDATING, progress=94)
        try:
            result = state["result"]
            covered = {item.keyword.casefold() for cluster in result.clusters for item in cluster.keywords}
            expected = {item.keyword.casefold() for item in state["keywords"]}
            if covered != expected:
                raise ValueError("The final plan did not preserve complete keyword coverage")
            if not result.pillars:
                raise ValueError("No pillar plan could be produced")
            repository.save_result(result)
            return {}
        except Exception as exc:
            return {"error": str(exc)}

    def fail(state: KeywordClusterWorkflowState) -> KeywordClusterWorkflowState:
        error = state.get("error") or "Keyword clustering failed for an unknown reason"
        repository.update_generation(state["generation_id"], status=KeywordClusterStatus.FAILED, stage=KeywordClusterStage.FAILED, progress=100, error=error)
        return {"error": error}

    def route(state: KeywordClusterWorkflowState) -> Literal["continue", "fail"]:
        return "fail" if state.get("error") else "continue"

    graph = StateGraph(KeywordClusterWorkflowState)
    graph.add_node("parse", parse)
    graph.add_node("cluster", cluster)
    graph.add_node("consolidate", consolidate)
    graph.add_node("plan", plan)
    graph.add_node("validate", validate)
    graph.add_node("fail", fail)
    graph.add_edge(START, "parse")
    graph.add_conditional_edges("parse", route, {"continue": "cluster", "fail": "fail"})
    graph.add_conditional_edges("cluster", route, {"continue": "consolidate", "fail": "fail"})
    graph.add_conditional_edges("consolidate", route, {"continue": "plan", "fail": "fail"})
    graph.add_conditional_edges("plan", route, {"continue": "validate", "fail": "fail"})
    graph.add_conditional_edges("validate", route, {"continue": END, "fail": "fail"})
    graph.add_edge("fail", END)
    return graph.compile()
