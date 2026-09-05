from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from internal_linking.generation import InternalLinkRefiner
from internal_linking.models import (
    InternalLinkCreate, InternalLinkHistoryResponse, InternalLinkResponse,
    InternalLinkResult, InternalLinkStage, InternalLinkStatus, InternalLinkSummary,
)
from internal_linking.storage import InternalLinkNotFoundError, InternalLinkRepository
from internal_linking.workflow import build_internal_link_graph
from seo_audit.config import Settings
from seo_audit.crawler import SiteCrawler


def create_internal_link_router(
    settings: Settings, repository: InternalLinkRepository, *,
    crawler: SiteCrawler | None = None, refiner: InternalLinkRefiner | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/agents/internal-linking")

    @router.post("/audits", response_model=InternalLinkResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_audit(request: InternalLinkCreate):
        if request.crawl_limit and request.crawl_limit > settings.maximum_crawl_limit:
            raise HTTPException(status_code=422, detail=f"The maximum crawl limit is {settings.maximum_crawl_limit} pages.")
        return InternalLinkResponse(audit=repository.create_audit(request, settings.default_crawl_limit))

    @router.get("/audits", response_model=InternalLinkHistoryResponse)
    def list_audits(limit: int = 10, offset: int = 0, query: str | None = None):
        safe_limit, safe_offset = max(1, min(limit, 50)), max(0, offset)
        runs = repository.list_audits(safe_limit, safe_offset, query)
        return InternalLinkHistoryResponse(
            items=[InternalLinkSummary(
                id=run.id, url=run.requested_url, status=run.status, stage=run.stage,
                progress=run.progress, page_count=run.result.pages_crawled if run.result else 0,
                recommendation_count=len(run.result.recommendations) if run.result else 0,
                result_available=run.result is not None, error=run.error,
                created_at=run.created_at, updated_at=run.updated_at,
            ) for run in runs],
            total=repository.count_audits(query), limit=safe_limit, offset=safe_offset,
        )

    @router.get("/audits/{audit_id}", response_model=InternalLinkResponse)
    def get_audit(audit_id: str):
        try:
            run = repository.get_audit(audit_id)
        except InternalLinkNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Internal-link audit not found") from exc
        return InternalLinkResponse(audit=run, result_available=run.result is not None)

    @router.post("/audits/{audit_id}/process", response_model=InternalLinkResponse)
    async def process_audit(audit_id: str):
        try:
            current = repository.get_audit(audit_id)
        except InternalLinkNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Internal-link audit not found") from exc
        claimed = repository.claim_audit(audit_id)
        if claimed is not None:
            try:
                await build_internal_link_graph(settings, repository, crawler=crawler, refiner=refiner).ainvoke({"audit_id": audit_id})
            except Exception as exc:
                repository.update_audit(
                    audit_id, status=InternalLinkStatus.FAILED,
                    stage=InternalLinkStage.FAILED, progress=100,
                    error=f"Unhandled workflow error: {exc}",
                )
        elif current.status == InternalLinkStatus.QUEUED:
            raise HTTPException(status_code=409, detail="Internal-link audit could not be claimed")
        run = repository.get_audit(audit_id)
        return InternalLinkResponse(audit=run, result_available=run.result is not None)

    @router.get("/audits/{audit_id}/result", response_model=InternalLinkResult)
    def get_result(audit_id: str):
        try:
            run = repository.get_audit(audit_id)
        except InternalLinkNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Internal-link audit not found") from exc
        if run.result is None:
            raise HTTPException(status_code=409, detail="Internal-link result is not ready")
        return run.result

    @router.post("/audits/{audit_id}/retry", response_model=InternalLinkResponse, status_code=status.HTTP_202_ACCEPTED)
    def retry_audit(audit_id: str):
        try:
            return InternalLinkResponse(audit=repository.retry_audit(audit_id))
        except InternalLinkNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Internal-link audit not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.delete("/audits/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_audit(audit_id: str) -> None:
        try:
            repository.delete_audit(audit_id)
        except InternalLinkNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Internal-link audit not found") from exc

    return router
