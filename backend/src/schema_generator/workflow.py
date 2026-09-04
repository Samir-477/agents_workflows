from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from schema_generator.compiler import compile_schema
from schema_generator.generation import SchemaInterpreter
from schema_generator.models import (
    ParsedSchemaBrief,
    SchemaGenerationResult,
    SchemaGenerationStage,
    SchemaGenerationStatus,
)
from schema_generator.storage import SchemaGenerationRepository
from seo_audit.config import Settings


class SchemaWorkflowState(TypedDict, total=False):
    generation_id: str
    brief: ParsedSchemaBrief
    result: SchemaGenerationResult
    error: str


def build_schema_graph(
    settings: Settings,
    repository: SchemaGenerationRepository,
    *,
    interpreter: SchemaInterpreter | None = None,
):
    interpreter = interpreter or SchemaInterpreter(settings)

    async def interpret(state: SchemaWorkflowState) -> SchemaWorkflowState:
        run = repository.get_generation(state["generation_id"])
        repository.update_generation(run.id, status=SchemaGenerationStatus.RUNNING, stage=SchemaGenerationStage.INTERPRETING, progress=18)
        try:
            brief = await interpreter.interpret(run.prompt)
            repository.save_brief(run.id, brief)
            return {"brief": brief}
        except Exception as exc:
            return {"error": str(exc)}

    def compile_output(state: SchemaWorkflowState) -> SchemaWorkflowState:
        repository.update_generation(state["generation_id"], status=SchemaGenerationStatus.RUNNING, stage=SchemaGenerationStage.COMPILING, progress=58)
        try:
            run = repository.get_generation(state["generation_id"])
            return {"result": compile_schema(state["generation_id"], state["brief"], source_prompt=run.prompt)}
        except Exception as exc:
            return {"error": str(exc)}

    def validate(state: SchemaWorkflowState) -> SchemaWorkflowState:
        repository.update_generation(state["generation_id"], status=SchemaGenerationStatus.RUNNING, stage=SchemaGenerationStage.VALIDATING, progress=80)
        try:
            if not state["result"].blocks:
                raise ValueError("No supported schema type could be compiled from this page description")
            return {}
        except Exception as exc:
            return {"error": str(exc)}

    def save(state: SchemaWorkflowState) -> SchemaWorkflowState:
        repository.update_generation(state["generation_id"], status=SchemaGenerationStatus.RUNNING, stage=SchemaGenerationStage.RECOMMENDING, progress=94)
        try:
            repository.save_result(state["result"])
            return {}
        except Exception as exc:
            return {"error": str(exc)}

    def fail(state: SchemaWorkflowState) -> SchemaWorkflowState:
        error = state.get("error") or "Schema generation failed for an unknown reason"
        repository.update_generation(state["generation_id"], status=SchemaGenerationStatus.FAILED, stage=SchemaGenerationStage.FAILED, progress=100, error=error)
        return {"error": error}

    def route(state: SchemaWorkflowState) -> Literal["continue", "fail"]:
        return "fail" if state.get("error") else "continue"

    graph = StateGraph(SchemaWorkflowState)
    graph.add_node("interpret", interpret)
    graph.add_node("compile", compile_output)
    graph.add_node("validate", validate)
    graph.add_node("save", save)
    graph.add_node("fail", fail)
    graph.add_edge(START, "interpret")
    graph.add_conditional_edges("interpret", route, {"continue": "compile", "fail": "fail"})
    graph.add_conditional_edges("compile", route, {"continue": "validate", "fail": "fail"})
    graph.add_conditional_edges("validate", route, {"continue": "save", "fail": "fail"})
    graph.add_conditional_edges("save", route, {"continue": END, "fail": "fail"})
    graph.add_edge("fail", END)
    return graph.compile()
