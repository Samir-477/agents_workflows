from __future__ import annotations

from fastapi import APIRouter, HTTPException

from resort_orchestrator.models import (
    OrchestratorCreate,
    OrchestratorHistoryResponse,
    OrchestratorResponse,
    OrchestratorSummary,
)
from resort_orchestrator.storage import OrchestratorNotFoundError
from resort_orchestrator.workflow import Dependencies, run_orchestration


def create_orchestrator_router(repository, deps: Dependencies) -> APIRouter:
    router = APIRouter(prefix="/api/agents/resort-orchestrator", tags=["Resort Orchestrator"])

    def get_run(run_id: str):
        try:
            return repository.get(run_id)
        except OrchestratorNotFoundError:
            raise HTTPException(status_code=404, detail="Orchestrator run not found") from None

    @router.post("/runs", response_model=OrchestratorResponse, status_code=202)
    def create(payload: OrchestratorCreate) -> OrchestratorResponse:
        run = repository.create(payload)
        return OrchestratorResponse(run=run, result_available=False)

    @router.get("/runs", response_model=OrchestratorHistoryResponse)
    def history(limit: int = 10, offset: int = 0, query: str | None = None) -> OrchestratorHistoryResponse:
        limit, offset = max(1, min(limit, 50)), max(0, offset)
        items = [
            OrchestratorSummary(
                id=item.id, page_url=item.page_url, status=item.status, stage=item.stage,
                progress=item.progress, result_available=item.report is not None,
                error=item.error, created_at=item.created_at, updated_at=item.updated_at,
            )
            for item in repository.list(limit, offset, query)
        ]
        return OrchestratorHistoryResponse(items=items, total=repository.count(query), limit=limit, offset=offset)

    @router.get("/runs/{run_id}", response_model=OrchestratorResponse)
    def read(run_id: str) -> OrchestratorResponse:
        run = get_run(run_id)
        return OrchestratorResponse(run=run, result_available=run.report is not None)

    @router.post("/runs/{run_id}/process", response_model=OrchestratorResponse)
    async def process(run_id: str) -> OrchestratorResponse:
        current = get_run(run_id)
        claimed = repository.claim(run_id)
        if claimed is not None:
            await run_orchestration(deps, repository, run_id)
        elif current.status.value == "queued":
            raise HTTPException(status_code=409, detail="Run could not be claimed")
        return OrchestratorResponse(run=get_run(run_id), result_available=get_run(run_id).report is not None)

    @router.get("/runs/{run_id}/result")
    def result(run_id: str):
        run = get_run(run_id)
        if run.report is None:
            raise HTTPException(status_code=409, detail="Report is not ready")
        return run.report

    @router.post("/runs/{run_id}/retry", response_model=OrchestratorResponse, status_code=202)
    def retry(run_id: str) -> OrchestratorResponse:
        try:
            run = repository.retry(run_id)
        except OrchestratorNotFoundError:
            raise HTTPException(status_code=404, detail="Orchestrator run not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return OrchestratorResponse(run=run, result_available=False)

    @router.delete("/runs/{run_id}", status_code=204)
    def delete(run_id: str) -> None:
        try:
            repository.delete(run_id)
        except OrchestratorNotFoundError:
            raise HTTPException(status_code=404, detail="Orchestrator run not found") from None

    return router
