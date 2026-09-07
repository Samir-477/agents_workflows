from fastapi import APIRouter, HTTPException, Response

from content_optimizer.models import ContentOptimizerRequest, ContentOptimizerResult, ContentOptimizerRun
from content_optimizer.storage import ContentOptimizerNotFoundError
from content_optimizer.workflow import run_content_optimizer


def create_content_optimizer_router(settings, repository, *, crawler=None, serp_repository=None, content_brief_repository=None):
    router = APIRouter(prefix="/api/agents/content-optimizer", tags=["SEO Content Optimizer"])

    def find(run_id):
        try: return repository.get(run_id)
        except ContentOptimizerNotFoundError as exc: raise HTTPException(404, "Content optimization not found.") from exc

    @router.post("/runs", response_model=ContentOptimizerRun, status_code=202)
    def create(payload: ContentOptimizerRequest): return repository.create(payload)

    @router.get("/runs", response_model=dict)
    def history(limit: int = 10, offset: int = 0, query: str | None = None):
        limit, offset = max(1, min(limit, 50)), max(0, offset)
        return {"items": repository.list_generations(limit, offset, query), "total": repository.count_generations(query), "limit": limit, "offset": offset}

    @router.get("/runs/{run_id}", response_model=ContentOptimizerRun)
    def read(run_id: str): return find(run_id)

    @router.post("/runs/{run_id}/process", response_model=ContentOptimizerRun)
    async def process(run_id: str):
        current = find(run_id)
        claimed = repository.claim(run_id)
        if claimed is not None:
            await run_content_optimizer(settings, repository, run_id, crawler=crawler, serp_repository=serp_repository, content_brief_repository=content_brief_repository)
        elif current.status == "queued":
            raise HTTPException(409, "Run could not be claimed.")
        return find(run_id)

    @router.get("/runs/{run_id}/result", response_model=ContentOptimizerResult)
    def result(run_id: str):
        run = find(run_id)
        if run.result is None: raise HTTPException(409, "Content optimization is not ready.")
        return run.result

    @router.post("/runs/{run_id}/retry", response_model=ContentOptimizerRun, status_code=202)
    def retry(run_id: str):
        try: return repository.retry(run_id)
        except ContentOptimizerNotFoundError as exc: raise HTTPException(404, "Content optimization not found.") from exc
        except ValueError as exc: raise HTTPException(409, str(exc)) from exc

    @router.delete("/runs/{run_id}", status_code=204)
    def delete(run_id: str):
        try: repository.delete(run_id)
        except ContentOptimizerNotFoundError as exc: raise HTTPException(404, "Content optimization not found.") from exc
        except ValueError as exc: raise HTTPException(409, str(exc)) from exc
        return Response(status_code=204)

    return router
