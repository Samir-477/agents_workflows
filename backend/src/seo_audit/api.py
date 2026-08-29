from __future__ import annotations

from contextlib import asynccontextmanager
from io import BytesIO

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from seo_audit.config import Settings
from seo_audit.models import (
    AuditCreate,
    AuditHistoryResponse,
    AuditResponse,
    AuditStage,
    AuditStatus,
)
from seo_audit.pdf_report import build_report_pdf
from seo_audit.storage import AuditNotFoundError, AuditRepository
from seo_audit.url_safety import UnsafeTargetError, normalize_http_url
from seo_audit.workflow import build_audit_graph


def create_app(
    settings: Settings | None = None,
    repository: AuditRepository | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    repository = repository or AuditRepository(
        settings.database_path,
        database_url=settings.database_url,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        repository.initialize()
        yield

    app = FastAPI(
        title="SEO/AEO Audit Agent API",
        version="0.1.0",
        description="Queue and retrieve evidence-backed website audits.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.repository = repository
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post(
        "/audits",
        response_model=AuditResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_audit(request: AuditCreate) -> AuditResponse:
        try:
            normalized_url = normalize_http_url(request.url)
        except UnsafeTargetError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        normalized_request = request.model_copy(update={"url": normalized_url})
        crawl_limit = min(
            request.crawl_limit or settings.default_crawl_limit,
            settings.maximum_crawl_limit,
        )
        audit = repository.create_audit(normalized_request, crawl_limit)
        return AuditResponse(audit=audit)

    @router.get("/audits", response_model=AuditHistoryResponse)
    def list_audits(
        limit: int = 10, offset: int = 0, query: str | None = None
    ) -> AuditHistoryResponse:
        safe_limit = max(1, min(limit, 50))
        safe_offset = max(0, offset)
        responses: list[AuditResponse] = []
        for audit in repository.list_audits(safe_limit, safe_offset, query):
            pages, findings = repository.counts(audit.id)
            report = repository.get_report(audit.id)
            responses.append(
                AuditResponse(
                    audit=audit,
                    pages_crawled=pages,
                    findings_count=findings,
                    report_available=report is not None,
                )
            )
        return AuditHistoryResponse(
            items=responses,
            total=repository.count_audits(query),
            limit=safe_limit,
            offset=safe_offset,
        )

    @router.post("/audits/{audit_id}/process", response_model=AuditResponse)
    async def process_audit(audit_id: str) -> AuditResponse:
        """Run one queued audit inside this Vercel-safe function invocation."""
        try:
            current = repository.get_audit(audit_id)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Audit not found") from exc

        claimed = repository.claim_audit(audit_id)
        if claimed is not None:
            try:
                graph = build_audit_graph(settings, repository)
                await graph.ainvoke({"audit_id": audit_id})
            except Exception as exc:
                repository.update_audit(
                    audit_id,
                    status=AuditStatus.FAILED,
                    stage=AuditStage.FAILED,
                    progress=100,
                    error=f"Unhandled workflow error: {exc}",
                )
        elif current.status == AuditStatus.QUEUED:
            raise HTTPException(status_code=409, detail="Audit could not be claimed")

        audit = repository.get_audit(audit_id)
        pages, findings = repository.counts(audit_id)
        return AuditResponse(
            audit=audit,
            pages_crawled=pages,
            findings_count=findings,
            report_available=repository.get_report(audit_id) is not None,
        )

    @router.delete("/audits/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_audit(audit_id: str) -> None:
        try:
            audit = repository.get_audit(audit_id)
            repository.delete_audit(audit_id)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Audit not found") from exc
        if settings.write_report_files:
            report_dir = settings.report_output_dir or settings.database_path.parent / "reports"
            report_file = report_dir / f"{audit.id}.md"
            report_file.unlink(missing_ok=True)

    @router.get("/audits/{audit_id}", response_model=AuditResponse)
    def get_audit(audit_id: str) -> AuditResponse:
        try:
            audit = repository.get_audit(audit_id)
            pages, findings = repository.counts(audit_id)
            report = repository.get_report(audit_id)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Audit not found") from exc
        return AuditResponse(
            audit=audit,
            pages_crawled=pages,
            findings_count=findings,
            report_available=report is not None,
        )

    @router.get("/audits/{audit_id}/report")
    def get_report(audit_id: str):
        try:
            report = repository.get_report(audit_id)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Audit not found") from exc
        if report is None:
            raise HTTPException(status_code=409, detail="Audit report is not ready")
        return report

    @router.get("/audits/{audit_id}/report.pdf")
    def download_report_pdf(audit_id: str) -> StreamingResponse:
        try:
            report = repository.get_report(audit_id)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Audit not found") from exc
        if report is None:
            raise HTTPException(status_code=409, detail="Audit report is not ready")
        pdf_bytes = build_report_pdf(report)
        filename = f"stellar-seo-audit-{audit_id[:8]}.pdf"
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.post(
        "/audits/{audit_id}/retry",
        response_model=AuditResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def retry_audit(audit_id: str) -> AuditResponse:
        try:
            audit = repository.retry_audit(audit_id)
        except AuditNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Audit not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return AuditResponse(audit=audit)

    app.include_router(router)
    app.include_router(router, prefix="/api/backend")
    app.include_router(router, prefix="/api")

    @app.get("/api/backend/docs", include_in_schema=False)
    @app.get("/api/docs", include_in_schema=False)
    def docs_redirect() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.get("/api/backend/openapi.json", include_in_schema=False)
    @app.get("/api/openapi.json", include_in_schema=False)
    def openapi_redirect() -> RedirectResponse:
        return RedirectResponse(url="/openapi.json")

    return app


app = create_app()


def run() -> None:
    uvicorn.run("seo_audit.api:app", host="127.0.0.1", port=8000, reload=False)
