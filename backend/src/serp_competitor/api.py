from fastapi import APIRouter, HTTPException, Response

from pydantic import BaseModel

from serp_competitor.models import SerpRequest, SerpResult, SerpRun
from serp_competitor.storage import SerpNotFoundError
from serp_competitor.workflow import run_serp_analysis


class SerperStatus(BaseModel):
    configured: bool
    provider: str = "Serper"


def create_serp_router(settings, repository, *, client=None, crawler=None):
    router = APIRouter(prefix="/api/agents/serp-competitor", tags=["SERP & Competitor Analysis"])

    def find(run_id):
        try: return repository.get(run_id)
        except SerpNotFoundError as exc: raise HTTPException(404, "SERP analysis not found.") from exc

    @router.get("/status", response_model=SerperStatus)
    def provider_status():
        return SerperStatus(configured=bool(settings.serper_api_key))

    @router.post("/runs", response_model=SerpRun, status_code=202)
    def create(payload: SerpRequest): return repository.create(payload)

    @router.get("/runs", response_model=dict)
    def history(limit: int = 10, offset: int = 0, query: str | None = None):
        limit, offset = max(1, min(limit, 50)), max(0, offset)
        return {"items": repository.list_generations(limit, offset, query), "total": repository.count_generations(query), "limit": limit, "offset": offset}

    @router.get("/runs/{run_id}", response_model=SerpRun)
    def read(run_id: str): return find(run_id)

    @router.post("/runs/{run_id}/process", response_model=SerpRun)
    async def process(run_id: str):
        current = find(run_id)
        claimed = repository.claim(run_id)
        if claimed is not None: await run_serp_analysis(settings, repository, run_id, client=client, crawler=crawler)
        elif current.status == "queued": raise HTTPException(409, "Run could not be claimed.")
        return find(run_id)

    @router.get("/runs/{run_id}/result", response_model=SerpResult)
    def result(run_id: str):
        run = find(run_id)
        if run.result is None: raise HTTPException(409, "SERP analysis is not ready.")
        return run.result

    @router.post("/runs/{run_id}/retry", response_model=SerpRun, status_code=202)
    def retry(run_id: str):
        try: return repository.retry(run_id)
        except SerpNotFoundError as exc: raise HTTPException(404, "SERP analysis not found.") from exc
        except ValueError as exc: raise HTTPException(409, str(exc)) from exc

    @router.delete("/runs/{run_id}", status_code=204)
    def delete(run_id: str):
        run = find(run_id)
        if run.status == "running": raise HTTPException(409, "Wait for this run to finish.")
        repository.delete(run_id)
        return Response(status_code=204)

    return router
