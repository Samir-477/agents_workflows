from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from meta_generator.generation import MetadataGenerator
from meta_generator.models import (
    GenerationStage,
    GenerationStatus,
    MetadataGenerationCreate,
    MetadataGenerationHistoryResponse,
    MetadataGenerationResponse,
    MetadataGenerationResult,
    MetadataGenerationSummary,
)
from meta_generator.storage import (
    MetadataGenerationNotFoundError,
    MetadataGenerationRepository,
)
from meta_generator.workflow import build_metadata_graph
from seo_audit.config import Settings


def create_metadata_router(
    settings: Settings,
    repository: MetadataGenerationRepository,
    *,
    generator: MetadataGenerator | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/agents/meta-title-description")

    @router.post(
        "/generations",
        response_model=MetadataGenerationResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_generation(
        request: MetadataGenerationCreate,
    ) -> MetadataGenerationResponse:
        run = repository.create_generation(request)
        return MetadataGenerationResponse(generation=run)

    @router.get(
        "/generations", response_model=MetadataGenerationHistoryResponse
    )
    def list_generations(
        limit: int = 10, offset: int = 0, query: str | None = None
    ) -> MetadataGenerationHistoryResponse:
        safe_limit = max(1, min(limit, 50))
        safe_offset = max(0, offset)
        runs = repository.list_generations(safe_limit, safe_offset, query)
        return MetadataGenerationHistoryResponse(
            items=[
                MetadataGenerationSummary(
                    id=run.id,
                    prompt_preview=(
                        run.prompt if len(run.prompt) <= 240 else run.prompt[:237] + "..."
                    ),
                    status=run.status,
                    stage=run.stage,
                    progress=run.progress,
                    page_count=(
                        len(run.parsed_brief.pages) if run.parsed_brief else 0
                    ),
                    result_available=run.result is not None,
                    error=run.error,
                    created_at=run.created_at,
                    updated_at=run.updated_at,
                )
                for run in runs
            ],
            total=repository.count_generations(query),
            limit=safe_limit,
            offset=safe_offset,
        )

    @router.get(
        "/generations/{generation_id}", response_model=MetadataGenerationResponse
    )
    def get_generation(generation_id: str) -> MetadataGenerationResponse:
        try:
            run = repository.get_generation(generation_id)
        except MetadataGenerationNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Generation not found") from exc
        return MetadataGenerationResponse(
            generation=run, result_available=run.result is not None
        )

    @router.post(
        "/generations/{generation_id}/process",
        response_model=MetadataGenerationResponse,
    )
    async def process_generation(generation_id: str) -> MetadataGenerationResponse:
        try:
            current = repository.get_generation(generation_id)
        except MetadataGenerationNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Generation not found") from exc

        claimed = repository.claim_generation(generation_id)
        if claimed is not None:
            try:
                graph = build_metadata_graph(
                    settings, repository, generator=generator
                )
                await graph.ainvoke({"generation_id": generation_id})
            except Exception as exc:
                repository.update_generation(
                    generation_id,
                    status=GenerationStatus.FAILED,
                    stage=GenerationStage.FAILED,
                    progress=100,
                    error=f"Unhandled workflow error: {exc}",
                )
        elif current.status == GenerationStatus.QUEUED:
            raise HTTPException(
                status_code=409, detail="Generation could not be claimed"
            )

        run = repository.get_generation(generation_id)
        return MetadataGenerationResponse(
            generation=run, result_available=run.result is not None
        )

    @router.get(
        "/generations/{generation_id}/result",
        response_model=MetadataGenerationResult,
    )
    def get_result(generation_id: str) -> MetadataGenerationResult:
        try:
            run = repository.get_generation(generation_id)
        except MetadataGenerationNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Generation not found") from exc
        if run.result is None:
            raise HTTPException(status_code=409, detail="Generation result is not ready")
        return run.result

    @router.post(
        "/generations/{generation_id}/retry",
        response_model=MetadataGenerationResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def retry_generation(generation_id: str) -> MetadataGenerationResponse:
        try:
            run = repository.retry_generation(generation_id)
        except MetadataGenerationNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Generation not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return MetadataGenerationResponse(generation=run)

    @router.delete(
        "/generations/{generation_id}", status_code=status.HTTP_204_NO_CONTENT
    )
    def delete_generation(generation_id: str) -> None:
        try:
            repository.delete_generation(generation_id)
        except MetadataGenerationNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Generation not found") from exc

    return router
