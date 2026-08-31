from __future__ import annotations

from meta_generator.models import (
    GenerationStage,
    GenerationStatus,
    MetadataGenerationCreate,
    MetadataGenerationRecord,
    MetadataGenerationResult,
    ParsedGenerationBrief,
    utc_now,
)
from meta_generator.storage import MetadataGenerationNotFoundError


class MemoryMetadataGenerationRepository:
    def __init__(self) -> None:
        self.runs: dict[str, MetadataGenerationRecord] = {}

    def initialize(self) -> None:
        return None

    def create_generation(
        self, request: MetadataGenerationCreate
    ) -> MetadataGenerationRecord:
        run = MetadataGenerationRecord(prompt=request.prompt)
        self.runs[run.id] = run
        return run.model_copy(deep=True)

    def get_generation(self, generation_id: str) -> MetadataGenerationRecord:
        try:
            return self.runs[generation_id].model_copy(deep=True)
        except KeyError as exc:
            raise MetadataGenerationNotFoundError(generation_id) from exc

    def list_generations(
        self, limit: int = 20, offset: int = 0, query: str | None = None
    ) -> list[MetadataGenerationRecord]:
        runs = sorted(
            self.runs.values(), key=lambda item: item.created_at, reverse=True
        )
        if query and query.strip():
            needle = query.strip().casefold()
            runs = [item for item in runs if needle in item.prompt.casefold()]
        return [item.model_copy(deep=True) for item in runs[offset : offset + limit]]

    def count_generations(self, query: str | None = None) -> int:
        if not query or not query.strip():
            return len(self.runs)
        needle = query.strip().casefold()
        return sum(needle in item.prompt.casefold() for item in self.runs.values())

    def delete_generation(self, generation_id: str) -> None:
        self.get_generation(generation_id)
        self.runs.pop(generation_id)

    def update_generation(
        self,
        generation_id: str,
        *,
        status: GenerationStatus | None = None,
        stage: GenerationStage | None = None,
        progress: int | None = None,
        warnings: list[str] | None = None,
        error: str | None = None,
    ) -> MetadataGenerationRecord:
        current = self.get_generation(generation_id)
        updated = current.model_copy(
            update={
                "status": status or current.status,
                "stage": stage or current.stage,
                "progress": current.progress if progress is None else progress,
                "warnings": current.warnings if warnings is None else warnings,
                "error": error,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        self.runs[generation_id] = updated
        return updated.model_copy(deep=True)

    def claim_generation(self, generation_id: str) -> MetadataGenerationRecord | None:
        current = self.get_generation(generation_id)
        if current.status != GenerationStatus.QUEUED:
            return None
        return self.update_generation(
            generation_id,
            status=GenerationStatus.RUNNING,
            stage=GenerationStage.PARSING,
            progress=2,
        )

    def save_brief(
        self, generation_id: str, brief: ParsedGenerationBrief
    ) -> MetadataGenerationRecord:
        current = self.get_generation(generation_id)
        updated = current.model_copy(
            update={
                "parsed_brief": brief,
                "warnings": brief.warnings,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        self.runs[generation_id] = updated
        return updated.model_copy(deep=True)

    def save_result(self, result: MetadataGenerationResult) -> None:
        current = self.get_generation(result.generation_id)
        self.runs[result.generation_id] = current.model_copy(
            update={
                "result": result,
                "status": GenerationStatus.COMPLETE,
                "stage": GenerationStage.COMPLETE,
                "progress": 100,
                "warnings": result.batch_warnings,
                "error": None,
                "updated_at": utc_now(),
            },
            deep=True,
        )

    def retry_generation(self, generation_id: str) -> MetadataGenerationRecord:
        current = self.get_generation(generation_id)
        if current.status not in {GenerationStatus.COMPLETE, GenerationStatus.FAILED}:
            raise ValueError("Only failed or completed generations can be queued again")
        retried = current.model_copy(
            update={
                "status": GenerationStatus.QUEUED,
                "stage": GenerationStage.QUEUED,
                "progress": 0,
                "parsed_brief": None,
                "result": None,
                "warnings": [],
                "error": None,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        self.runs[generation_id] = retried
        return retried.model_copy(deep=True)
