from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from content_brief.generation import ContentBriefGenerator
from content_brief.models import (
    ContentBriefCreate,
    ContentBriefHistoryResponse,
    ContentBriefResponse,
    ContentBriefResult,
    ContentBriefStage,
    ContentBriefStatus,
    ContentBriefSummary,
)
from content_brief.storage import ContentBriefNotFoundError, ContentBriefRepository
from content_brief.workflow import build_content_brief_graph
from seo_audit.config import Settings


def create_content_brief_router(
    settings: Settings,
    repository: ContentBriefRepository,
    *,
    generator: ContentBriefGenerator | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/agents/content-brief")

    @router.post("/generations", response_model=ContentBriefResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_generation(request: ContentBriefCreate) -> ContentBriefResponse:
        return ContentBriefResponse(generation=repository.create_generation(request))

    @router.get("/generations", response_model=ContentBriefHistoryResponse)
    def list_generations(limit: int = 10, offset: int = 0, query: str | None = None) -> ContentBriefHistoryResponse:
        safe_limit, safe_offset = max(1, min(limit, 50)), max(0, offset)
        runs = repository.list_generations(safe_limit, safe_offset, query)
        return ContentBriefHistoryResponse(
            items=[ContentBriefSummary(
                id=run.id, target_keyword=run.request.target_keyword,
                audience=run.request.audience, status=run.status, stage=run.stage,
                progress=run.progress,
                ready_for_handoff=run.result.ready_for_handoff if run.result else None,
                result_available=run.result is not None, error=run.error,
                created_at=run.created_at, updated_at=run.updated_at,
            ) for run in runs],
            total=repository.count_generations(query), limit=safe_limit, offset=safe_offset,
        )

    @router.get("/generations/{generation_id}", response_model=ContentBriefResponse)
    def get_generation(generation_id: str) -> ContentBriefResponse:
        try:
            run = repository.get_generation(generation_id)
        except ContentBriefNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Content brief generation not found") from exc
        return ContentBriefResponse(generation=run, result_available=run.result is not None)

    @router.post("/generations/{generation_id}/process", response_model=ContentBriefResponse)
    async def process_generation(generation_id: str) -> ContentBriefResponse:
        try:
            current = repository.get_generation(generation_id)
        except ContentBriefNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Content brief generation not found") from exc
        claimed = repository.claim_generation(generation_id)
        if claimed is not None:
            try:
                await build_content_brief_graph(settings, repository, generator=generator).ainvoke({"generation_id": generation_id})
            except Exception as exc:
                repository.update_generation(
                    generation_id, status=ContentBriefStatus.FAILED,
                    stage=ContentBriefStage.FAILED, progress=100,
                    error=f"Unhandled workflow error: {exc}",
                )
        elif current.status == ContentBriefStatus.QUEUED:
            raise HTTPException(status_code=409, detail="Content brief generation could not be claimed")
        run = repository.get_generation(generation_id)
        return ContentBriefResponse(generation=run, result_available=run.result is not None)

    @router.get("/generations/{generation_id}/result", response_model=ContentBriefResult)
    def get_result(generation_id: str) -> ContentBriefResult:
        try:
            run = repository.get_generation(generation_id)
        except ContentBriefNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Content brief generation not found") from exc
        if run.result is None:
            raise HTTPException(status_code=409, detail="Content brief is not ready")
        return run.result

    @router.post("/generations/{generation_id}/retry", response_model=ContentBriefResponse, status_code=status.HTTP_202_ACCEPTED)
    def retry_generation(generation_id: str) -> ContentBriefResponse:
        try:
            return ContentBriefResponse(generation=repository.retry_generation(generation_id))
        except ContentBriefNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Content brief generation not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.delete("/generations/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_generation(generation_id: str) -> None:
        try:
            repository.delete_generation(generation_id)
        except ContentBriefNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Content brief generation not found") from exc

    return router
