from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from meta_generator.generation import MetadataGenerator
from meta_generator.models import (
    DraftGenerationResult,
    GenerationStage,
    GenerationStatus,
    MetadataGenerationResult,
    ParsedGenerationBrief,
)
from meta_generator.storage import MetadataGenerationRepository
from meta_generator.validation import validate_draft
from seo_audit.config import Settings


class MetadataWorkflowState(TypedDict, total=False):
    generation_id: str
    brief: ParsedGenerationBrief
    draft: DraftGenerationResult
    result: MetadataGenerationResult
    repair_instructions: list[str]
    error: str


def build_metadata_graph(
    settings: Settings,
    repository: MetadataGenerationRepository,
    *,
    generator: MetadataGenerator | None = None,
):
    generator = generator or MetadataGenerator(settings)

    async def parse_prompt(state: MetadataWorkflowState) -> MetadataWorkflowState:
        run = repository.get_generation(state["generation_id"])
        repository.update_generation(
            run.id,
            status=GenerationStatus.RUNNING,
            stage=GenerationStage.PARSING,
            progress=10,
        )
        try:
            brief = await generator.parse(run.prompt)
            repository.save_brief(run.id, brief)
            return {"brief": brief}
        except Exception as exc:
            return {"error": str(exc)}

    async def generate_options(state: MetadataWorkflowState) -> MetadataWorkflowState:
        run = repository.get_generation(state["generation_id"])
        repository.update_generation(
            run.id,
            status=GenerationStatus.RUNNING,
            stage=GenerationStage.GENERATING,
            progress=38,
        )
        try:
            draft = await generator.generate(run.prompt, state["brief"])
            return {"draft": draft}
        except Exception as exc:
            return {"error": str(exc)}

    async def validate_and_repair(
        state: MetadataWorkflowState,
    ) -> MetadataWorkflowState:
        run = repository.get_generation(state["generation_id"])
        repository.update_generation(
            run.id,
            status=GenerationStatus.RUNNING,
            stage=GenerationStage.VALIDATING,
            progress=66,
        )
        try:
            outcome = validate_draft(run.id, run.prompt, state["brief"], state["draft"])
            draft = state["draft"]
            for _ in range(2):
                if not outcome.repair_instructions:
                    break
                draft = await generator.generate(
                    run.prompt,
                    state["brief"],
                    repair_instructions=outcome.repair_instructions,
                    previous_draft=draft,
                )
                outcome = validate_draft(run.id, run.prompt, state["brief"], draft)
            for page in outcome.result.pages:
                if not any(not option.issues for option in page.titles):
                    raise ValueError(f"No valid title option remained for {page.page_name}")
                if not any(not option.issues for option in page.descriptions):
                    raise ValueError(
                        f"No valid meta description option remained for {page.page_name}"
                    )
            return {
                "draft": draft,
                "result": outcome.result,
                "repair_instructions": outcome.repair_instructions,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def deduplicate_batch(state: MetadataWorkflowState) -> MetadataWorkflowState:
        repository.update_generation(
            state["generation_id"],
            status=GenerationStatus.RUNNING,
            stage=GenerationStage.DEDUPLICATING,
            progress=84,
        )
        return {}

    def recommend_and_save(state: MetadataWorkflowState) -> MetadataWorkflowState:
        repository.update_generation(
            state["generation_id"],
            status=GenerationStatus.RUNNING,
            stage=GenerationStage.RECOMMENDING,
            progress=94,
        )
        try:
            repository.save_result(state["result"])
            return {}
        except Exception as exc:
            return {"error": str(exc)}

    def fail_generation(state: MetadataWorkflowState) -> MetadataWorkflowState:
        error = state.get("error") or "Metadata generation failed for an unknown reason"
        repository.update_generation(
            state["generation_id"],
            status=GenerationStatus.FAILED,
            stage=GenerationStage.FAILED,
            progress=100,
            error=error,
        )
        return {"error": error}

    def route(state: MetadataWorkflowState) -> Literal["continue", "fail"]:
        return "fail" if state.get("error") else "continue"

    graph = StateGraph(MetadataWorkflowState)
    graph.add_node("parse_prompt", parse_prompt)
    graph.add_node("generate_options", generate_options)
    graph.add_node("validate_and_repair", validate_and_repair)
    graph.add_node("deduplicate_batch", deduplicate_batch)
    graph.add_node("recommend_and_save", recommend_and_save)
    graph.add_node("fail_generation", fail_generation)
    graph.add_edge(START, "parse_prompt")
    graph.add_conditional_edges(
        "parse_prompt", route, {"continue": "generate_options", "fail": "fail_generation"}
    )
    graph.add_conditional_edges(
        "generate_options", route, {"continue": "validate_and_repair", "fail": "fail_generation"}
    )
    graph.add_conditional_edges(
        "validate_and_repair", route, {"continue": "deduplicate_batch", "fail": "fail_generation"}
    )
    graph.add_edge("deduplicate_batch", "recommend_and_save")
    graph.add_conditional_edges(
        "recommend_and_save", route, {"continue": END, "fail": "fail_generation"}
    )
    graph.add_edge("fail_generation", END)
    return graph.compile()
