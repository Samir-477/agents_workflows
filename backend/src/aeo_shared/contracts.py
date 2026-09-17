from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


REQUIRED_DETAIL_FIELDS = {
    "question_discovery": {"questions", "source_ledger", "limitations", "discovery_confidence_score"},
    "answer_gap": {"assessments", "prioritized_gaps", "limitations", "answer_readiness_score"},
    "answer_optimization": {"optimized_answers", "limitations", "optimization_coverage_score"},
    "faq_intelligence": {"faq_entries", "limitations", "faq_coverage_score"},
    "question_intent": {"classified_questions", "distribution", "limitations", "high_value_readiness_score"},
    "answer_structure": {"structure_entries", "structure_improvements", "unlocated_entries", "limitations", "answer_structure_score", "assessment_confidence_score", "scoring_weights"},
    "aeo_opportunity": {"opportunities", "research_opportunities", "roadmap", "limitations", "aeo_opportunity_score", "assessment_confidence_score"},
}


class AeoResultEnvelope(BaseModel):
    """Runtime guard for the shared report boundary.

    Individual agents may add specialist fields, but they cannot reach report
    assembly without the core fields their renderer and downstream agents use.
    """

    model_config = ConfigDict(extra="allow")
    status: Literal["complete"]
    detail: dict[str, Any] = Field(default_factory=dict)
    agent: str

    @model_validator(mode="after")
    def required_contract(self):
        required = REQUIRED_DETAIL_FIELDS[self.agent]
        missing = sorted(required - self.detail.keys())
        if missing:
            raise ValueError(f"{self.agent} result omitted required fields: {', '.join(missing)}")
        if not isinstance(self.detail.get("limitations"), list):
            raise ValueError(f"{self.agent} limitations must be a list")
        return self


def validate_aeo_result(agent: str, result: dict[str, Any]) -> dict[str, Any]:
    validated = AeoResultEnvelope.model_validate({**result, "agent": agent})
    payload = validated.model_dump(mode="json", exclude={"agent"})
    return payload
