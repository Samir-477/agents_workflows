import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response
from local_seo.models import CopyDraft, LocalRequest, LocalResult, LocalRun
from local_seo.pipeline import finalize, generate_run


def create_local_router(repository, generator):
    router = APIRouter(prefix="/api/agents/local-seo", tags=["Local SEO Page Generator"])

    def get_run(run_id):
        try:
            run = repository.get(run_id)
            if run.status == "running" and (datetime.now(UTC) - run.updated_at).total_seconds() > 360:
                return repository.mutate(run_id, expected={"running"}, expected_updated_at=run.updated_at, status="failed", stage="failed", error="Run interrupted. Retry to generate again.") or repository.get(run_id)
            return run
        except KeyError:
            raise HTTPException(404, "Local page run not found.") from None

    @router.post("/generations", response_model=LocalRun, status_code=202)
    def create(payload: LocalRequest):
        return repository.create(payload)

    @router.get("/generations")
    def history(limit: int = 10, offset: int = 0, query: str | None = None):
        limit, offset = max(1, min(limit, 50)), max(0, offset)
        return {"items": repository.list_generations(limit, offset, query), "total": repository.count_generations(query), "limit": limit, "offset": offset}

    @router.get("/generations/{run_id}", response_model=LocalRun)
    def read(run_id: str):
        return get_run(run_id)

    @router.post("/generations/{run_id}/process", response_model=LocalRun)
    async def process(run_id: str):
        get_run(run_id)
        run = repository.mutate(run_id, expected={"queued"}, status="running", stage="extracting", progress=5)
        if run is None:
            return get_run(run_id)
        try:
            result = await generate_run(run.request, generator, lambda stage, progress: repository.mutate(run_id, stage=stage, progress=progress))
            repository.mutate(run_id, result=result, status="complete", stage="complete", progress=100)
        except (Exception, asyncio.CancelledError):
            # Provider exception strings can include credentials or request bodies.
            repository.mutate(run_id, status="failed", stage="failed", error="Generation could not finish. Check model settings and provide explicit services and at most three areas, then retry.")
        return get_run(run_id)

    @router.get("/generations/{run_id}/result", response_model=LocalResult)
    def result(run_id: str):
        run = get_run(run_id)
        if run.result is None:
            raise HTTPException(409, "Result is not available yet.")
        return run.result

    @router.post("/generations/{run_id}/retry", response_model=LocalRun, status_code=202)
    def retry(run_id: str):
        get_run(run_id)
        run = repository.mutate(run_id, expected={"complete", "failed"}, status="queued", stage="queued", progress=0, error=None, result=None)
        if run is None:
            raise HTTPException(409, "Only finished runs can be retried.")
        return run

    @router.put("/generations/{run_id}/pages/{page_index}", response_model=LocalRun)
    def edit(run_id: str, page_index: int, payload: CopyDraft):
        run = get_run(run_id)
        if run.status != "complete" or run.result is None:
            raise HTTPException(409, "Only completed drafts can be edited.")
        if page_index < 0 or page_index >= len(run.result.pages):
            raise HTTPException(404, "Page not found.")
        drafts = [page.content for page in run.result.pages]
        drafts[page_index] = payload
        result = finalize(
            run.result.profile,
            drafts,
            run.request.existing_urls,
            run.request.prompt,
        )
        result.maps_candidates = run.result.maps_candidates
        enrichment_warnings = [
            warning for warning in run.result.warnings
            if any(marker in warning.casefold() for marker in (
                "openstreetmap", "listing lookup", "public listing"
            ))
        ]
        result.warnings = list(dict.fromkeys([*result.warnings, *enrichment_warnings]))
        saved = repository.mutate(run_id, expected={"complete"}, expected_updated_at=run.updated_at, result=result)
        if saved is None:
            raise HTTPException(409, "Run changed; reload before saving.")
        return saved

    @router.delete("/generations/{run_id}", status_code=204)
    def delete(run_id: str):
        get_run(run_id)
        if not repository.delete(run_id):
            raise HTTPException(409, "Wait for the running generation to finish.")
        return Response(status_code=204)

    return router
