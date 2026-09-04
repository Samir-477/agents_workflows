from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from keyword_cluster.generation import KeywordClusterGenerator
from keyword_cluster.models import (
    KeywordClusterCreate,
    KeywordClusterHistoryResponse,
    KeywordClusterResponse,
    KeywordClusterResult,
    KeywordClusterStage,
    KeywordClusterStatus,
    KeywordClusterSummary,
)
from keyword_cluster.storage import KeywordClusterNotFoundError, KeywordClusterRepository
from keyword_cluster.workflow import build_keyword_cluster_graph
from seo_audit.config import Settings


def create_keyword_cluster_router(
    settings: Settings,
    repository: KeywordClusterRepository,
    *,
    generator: KeywordClusterGenerator | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/agents/keyword-cluster")

    @router.post("/generations", response_model=KeywordClusterResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_generation(request: KeywordClusterCreate) -> KeywordClusterResponse:
        return KeywordClusterResponse(generation=repository.create_generation(request))

    @router.get("/generations", response_model=KeywordClusterHistoryResponse)
    def list_generations(limit: int = 10, offset: int = 0, query: str | None = None) -> KeywordClusterHistoryResponse:
        safe_limit, safe_offset = max(1, min(limit, 50)), max(0, offset)
        runs = repository.list_generations(safe_limit, safe_offset, query)
        return KeywordClusterHistoryResponse(
            items=[KeywordClusterSummary(
                id=run.id,
                keyword_preview=next((item.keyword for item in run.parsed_keywords), run.raw_keywords.splitlines()[0] if run.raw_keywords.splitlines() else "Keyword plan"),
                status=run.status, stage=run.stage, progress=run.progress,
                keyword_count=len(run.parsed_keywords), cluster_count=len(run.result.clusters) if run.result else 0,
                pillar_count=len(run.result.pillars) if run.result else 0,
                result_available=run.result is not None, error=run.error,
                created_at=run.created_at, updated_at=run.updated_at,
            ) for run in runs],
            total=repository.count_generations(query), limit=safe_limit, offset=safe_offset,
        )

    @router.get("/generations/{generation_id}", response_model=KeywordClusterResponse)
    def get_generation(generation_id: str) -> KeywordClusterResponse:
        try:
            run = repository.get_generation(generation_id)
        except KeywordClusterNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Keyword cluster generation not found") from exc
        return KeywordClusterResponse(generation=run, result_available=run.result is not None)

    @router.post("/generations/{generation_id}/process", response_model=KeywordClusterResponse)
    async def process_generation(generation_id: str) -> KeywordClusterResponse:
        try:
            current = repository.get_generation(generation_id)
        except KeywordClusterNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Keyword cluster generation not found") from exc
        claimed = repository.claim_generation(generation_id)
        if claimed is not None:
            try:
                await build_keyword_cluster_graph(settings, repository, generator=generator).ainvoke({"generation_id": generation_id})
            except Exception as exc:
                repository.update_generation(generation_id, status=KeywordClusterStatus.FAILED, stage=KeywordClusterStage.FAILED, progress=100, error=f"Unhandled workflow error: {exc}")
        elif current.status == KeywordClusterStatus.QUEUED:
            raise HTTPException(status_code=409, detail="Keyword cluster generation could not be claimed")
        run = repository.get_generation(generation_id)
        return KeywordClusterResponse(generation=run, result_available=run.result is not None)

    @router.get("/generations/{generation_id}/result", response_model=KeywordClusterResult)
    def get_result(generation_id: str) -> KeywordClusterResult:
        try:
            run = repository.get_generation(generation_id)
        except KeywordClusterNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Keyword cluster generation not found") from exc
        if run.result is None:
            raise HTTPException(status_code=409, detail="Keyword cluster result is not ready")
        return run.result

    @router.post("/generations/{generation_id}/retry", response_model=KeywordClusterResponse, status_code=status.HTTP_202_ACCEPTED)
    def retry_generation(generation_id: str) -> KeywordClusterResponse:
        try:
            return KeywordClusterResponse(generation=repository.retry_generation(generation_id))
        except KeywordClusterNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Keyword cluster generation not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.delete("/generations/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_generation(generation_id: str) -> None:
        try:
            repository.delete_generation(generation_id)
        except KeywordClusterNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Keyword cluster generation not found") from exc

    return router
