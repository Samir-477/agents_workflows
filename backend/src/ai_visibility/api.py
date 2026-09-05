from fastapi import APIRouter, HTTPException, status

from ai_visibility.models import VisibilityCreate, VisibilityHistoryResponse, VisibilityResponse, VisibilityResult, VisibilitySummary
from ai_visibility.storage import VisibilityNotFoundError
from ai_visibility.workflow import run_visibility_audit


def create_visibility_router(settings, repository, *, crawler=None):
    router = APIRouter(prefix="/api/agents/ai-visibility")

    @router.post("/audits", response_model=VisibilityResponse, status_code=status.HTTP_202_ACCEPTED)
    def create(request: VisibilityCreate):
        if request.crawl_limit and request.crawl_limit > settings.maximum_crawl_limit:
            raise HTTPException(422, f"The maximum crawl limit is {settings.maximum_crawl_limit} pages.")
        run = repository.create_audit(request, settings.default_crawl_limit)
        return VisibilityResponse(audit=run)

    @router.get("/audits", response_model=VisibilityHistoryResponse)
    def list_runs(limit: int = 10, offset: int = 0, query: str | None = None):
        limit, offset = max(1, min(limit, 50)), max(0, offset)
        runs = repository.list_audits(limit, offset, query)
        return VisibilityHistoryResponse(items=[VisibilitySummary(
            id=r.id, url=r.requested_url, status=r.status, stage=r.stage, progress=r.progress,
            overall_score=r.result.overall_score if r.result else None,
            page_count=r.result.pages_crawled if r.result else 0,
            finding_count=len(r.result.findings) if r.result else 0,
            result_available=r.result is not None, error=r.error, created_at=r.created_at, updated_at=r.updated_at,
        ) for r in runs], total=repository.count_audits(query), limit=limit, offset=offset)

    def get_run(audit_id):
        try: return repository.get_audit(audit_id)
        except VisibilityNotFoundError as exc: raise HTTPException(404, "AI visibility audit not found") from exc

    @router.get("/audits/{audit_id}", response_model=VisibilityResponse)
    def get(audit_id: str):
        run = get_run(audit_id)
        return VisibilityResponse(audit=run, result_available=run.result is not None)

    @router.post("/audits/{audit_id}/process", response_model=VisibilityResponse)
    async def process(audit_id: str):
        current = get_run(audit_id)
        claimed = repository.claim_audit(audit_id)
        if claimed is not None: await run_visibility_audit(settings, repository, audit_id, crawler)
        elif current.status.value == "queued": raise HTTPException(409, "Audit could not be claimed")
        run = get_run(audit_id)
        return VisibilityResponse(audit=run, result_available=run.result is not None)

    @router.get("/audits/{audit_id}/result", response_model=VisibilityResult)
    def result(audit_id: str):
        run = get_run(audit_id)
        if not run.result: raise HTTPException(409, "AI visibility result is not ready")
        return run.result

    @router.post("/audits/{audit_id}/retry", response_model=VisibilityResponse, status_code=202)
    def retry(audit_id: str):
        try: return VisibilityResponse(audit=repository.retry_audit(audit_id))
        except VisibilityNotFoundError as exc: raise HTTPException(404, "AI visibility audit not found") from exc
        except ValueError as exc: raise HTTPException(409, str(exc)) from exc

    @router.delete("/audits/{audit_id}", status_code=204)
    def delete(audit_id: str):
        try: repository.delete_audit(audit_id)
        except VisibilityNotFoundError as exc: raise HTTPException(404, "AI visibility audit not found") from exc

    return router
