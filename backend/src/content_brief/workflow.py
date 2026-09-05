from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from content_brief.generation import ContentBriefGenerator
from content_brief.models import (
    ContentBriefDraft,
    ContentBriefResult,
    ContentBriefStage,
    ContentBriefStatus,
)
from content_brief.storage import ContentBriefRepository
from content_brief.validation import validate_brief
from seo_audit.config import Settings


class ContentBriefWorkflowState(TypedDict, total=False):
    generation_id: str
    draft: ContentBriefDraft
    result: ContentBriefResult
    repair_instructions: list[str]
    error: str


def build_content_brief_graph(
    settings: Settings,
    repository: ContentBriefRepository,
    *,
    generator: ContentBriefGenerator | None = None,
):
    generator = generator or ContentBriefGenerator(settings)

    def normalize(state: ContentBriefWorkflowState) -> ContentBriefWorkflowState:
        try:
            repository.update_generation(
                state["generation_id"], status=ContentBriefStatus.RUNNING,
                stage=ContentBriefStage.NORMALIZING, progress=10,
            )
            repository.get_generation(state["generation_id"])
            return {}
        except Exception as exc:
            return {"error": str(exc)}

    async def plan(state: ContentBriefWorkflowState) -> ContentBriefWorkflowState:
        repository.update_generation(
            state["generation_id"], status=ContentBriefStatus.RUNNING,
            stage=ContentBriefStage.PLANNING, progress=28,
        )
        try:
            run = repository.get_generation(state["generation_id"])
            draft = await generator.generate(run.request)
            repository.save_draft(run.id, draft)
            return {"draft": draft}
        except Exception as exc:
            return {"error": str(exc)}

    def validate(state: ContentBriefWorkflowState) -> ContentBriefWorkflowState:
        repository.update_generation(
            state["generation_id"], status=ContentBriefStatus.RUNNING,
            stage=ContentBriefStage.VALIDATING, progress=68,
        )
        try:
            run = repository.get_generation(state["generation_id"])
            outcome = validate_brief(run.id, run.request, state["draft"])
            return {
                "draft": outcome.result.brief,
                "result": outcome.result,
                "repair_instructions": outcome.repair_instructions,
            }
        except Exception as exc:
            return {"error": str(exc)}

    async def repair(state: ContentBriefWorkflowState) -> ContentBriefWorkflowState:
        repository.update_generation(
            state["generation_id"], status=ContentBriefStatus.RUNNING,
            stage=ContentBriefStage.REPAIRING, progress=79,
        )
        try:
            run = repository.get_generation(state["generation_id"])
            repaired = await generator.generate(
                run.request,
                repair_instructions=state["repair_instructions"],
                previous_draft=state["draft"],
            )
            repository.save_draft(run.id, repaired)
            outcome = validate_brief(run.id, run.request, repaired)
            return {
                "draft": outcome.result.brief,
                "result": outcome.result,
                "repair_instructions": [],
            }
        except Exception as exc:
            current_result = state.get("result")
            if current_result is None:
                return {"error": str(exc)}
            warning = "The optional repair pass could not complete; the validated first draft was preserved."
            preserved = current_result.model_copy(
                update={"warnings": [*current_result.warnings, warning]}, deep=True
            )
            return {"result": preserved, "repair_instructions": []}

    def finalize(state: ContentBriefWorkflowState) -> ContentBriefWorkflowState:
        repository.update_generation(
            state["generation_id"], status=ContentBriefStatus.RUNNING,
            stage=ContentBriefStage.FINALIZING, progress=94,
        )
        try:
            result = state["result"]
            warnings = list(result.warnings)
            if not result.ready_for_handoff:
                warnings.append("The brief is saved as a review draft because blocking validation issues remain.")
                result = result.model_copy(update={"warnings": warnings}, deep=True)
            repository.save_draft(state["generation_id"], result.brief)
            repository.save_result(result)
            return {"result": result}
        except Exception as exc:
            return {"error": str(exc)}

    def fail(state: ContentBriefWorkflowState) -> ContentBriefWorkflowState:
        error = state.get("error") or "Content brief generation failed for an unknown reason"
        repository.update_generation(
            state["generation_id"], status=ContentBriefStatus.FAILED,
            stage=ContentBriefStage.FAILED, progress=100, error=error,
        )
        return {"error": error}

    def route_error(state: ContentBriefWorkflowState) -> Literal["continue", "fail"]:
        return "fail" if state.get("error") else "continue"

    def route_validation(state: ContentBriefWorkflowState) -> Literal["repair", "finalize", "fail"]:
        if state.get("error"):
            return "fail"
        return "repair" if state.get("repair_instructions") else "finalize"

    graph = StateGraph(ContentBriefWorkflowState)
    graph.add_node("normalize", normalize)
    graph.add_node("plan", plan)
    graph.add_node("validate", validate)
    graph.add_node("repair", repair)
    graph.add_node("finalize", finalize)
    graph.add_node("fail", fail)
    graph.add_edge(START, "normalize")
    graph.add_conditional_edges("normalize", route_error, {"continue": "plan", "fail": "fail"})
    graph.add_conditional_edges("plan", route_error, {"continue": "validate", "fail": "fail"})
    graph.add_conditional_edges("validate", route_validation, {"repair": "repair", "finalize": "finalize", "fail": "fail"})
    graph.add_conditional_edges("repair", route_error, {"continue": "finalize", "fail": "fail"})
    graph.add_conditional_edges("finalize", route_error, {"continue": END, "fail": "fail"})
    graph.add_edge("fail", END)
    return graph.compile()
