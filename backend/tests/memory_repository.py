from __future__ import annotations

from seo_audit.models import (
    AuditCreate,
    AuditRecord,
    AuditReport,
    AuditStage,
    AuditStatus,
    Finding,
    PageRecord,
    utc_now,
)
from seo_audit.storage import AuditNotFoundError


class MemoryAuditRepository:
    """Small Postgres-free repository used only by the automated tests."""

    def __init__(self) -> None:
        self.audits: dict[str, AuditRecord] = {}
        self.pages: dict[str, list[PageRecord]] = {}
        self.findings: dict[str, list[Finding]] = {}
        self.reports: dict[str, AuditReport] = {}

    def initialize(self) -> None:
        return None

    def create_audit(self, request: AuditCreate, crawl_limit: int) -> AuditRecord:
        audit = AuditRecord(
            requested_url=request.url,
            business_description=request.business_description,
            audit_reason=request.audit_reason,
            important_urls=request.important_urls,
            crawl_limit=crawl_limit,
        )
        self.audits[audit.id] = audit
        return audit.model_copy(deep=True)

    def get_audit(self, audit_id: str) -> AuditRecord:
        try:
            return self.audits[audit_id].model_copy(deep=True)
        except KeyError as exc:
            raise AuditNotFoundError(audit_id) from exc

    def list_audits(
        self, limit: int = 20, offset: int = 0, query: str | None = None
    ) -> list[AuditRecord]:
        audits = sorted(
            self.audits.values(), key=lambda item: item.created_at, reverse=True
        )
        if query and query.strip():
            needle = query.strip().lower()
            audits = [item for item in audits if needle in item.requested_url.lower()]
        return [item.model_copy(deep=True) for item in audits[offset : offset + limit]]

    def count_audits(self, query: str | None = None) -> int:
        if not query or not query.strip():
            return len(self.audits)
        needle = query.strip().lower()
        return sum(needle in item.requested_url.lower() for item in self.audits.values())

    def delete_audit(self, audit_id: str) -> None:
        self.get_audit(audit_id)
        self.audits.pop(audit_id)
        self.pages.pop(audit_id, None)
        self.findings.pop(audit_id, None)
        self.reports.pop(audit_id, None)

    def update_audit(
        self,
        audit_id: str,
        *,
        status: AuditStatus | None = None,
        stage: AuditStage | None = None,
        progress: int | None = None,
        normalized_origin: str | None = None,
        warnings: list[str] | None = None,
        error: str | None = None,
    ) -> AuditRecord:
        current = self.get_audit(audit_id)
        updated = current.model_copy(
            update={
                "status": status or current.status,
                "stage": stage or current.stage,
                "progress": current.progress if progress is None else progress,
                "normalized_origin": (
                    current.normalized_origin
                    if normalized_origin is None
                    else normalized_origin
                ),
                "warnings": current.warnings if warnings is None else warnings,
                "error": error,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        self.audits[audit_id] = updated
        return updated.model_copy(deep=True)

    def claim_next_audit(self) -> AuditRecord | None:
        queued = sorted(
            (item for item in self.audits.values() if item.status == AuditStatus.QUEUED),
            key=lambda item: item.created_at,
        )
        return self.claim_audit(queued[0].id) if queued else None

    def claim_audit(self, audit_id: str) -> AuditRecord | None:
        audit = self.get_audit(audit_id)
        if audit.status != AuditStatus.QUEUED:
            return None
        return self.update_audit(
            audit_id,
            status=AuditStatus.RUNNING,
            stage=AuditStage.VALIDATING,
            progress=2,
        )

    def retry_audit(self, audit_id: str) -> AuditRecord:
        audit = self.get_audit(audit_id)
        if audit.status not in {AuditStatus.FAILED, AuditStatus.COMPLETE}:
            raise ValueError("Only failed or completed audits can be queued again")
        self.pages[audit_id] = []
        self.findings[audit_id] = []
        self.reports.pop(audit_id, None)
        retried = audit.model_copy(
            update={
                "status": AuditStatus.QUEUED,
                "stage": AuditStage.QUEUED,
                "progress": 0,
                "warnings": [],
                "error": None,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        self.audits[audit_id] = retried
        return retried.model_copy(deep=True)

    def replace_pages(self, audit_id: str, pages: list[PageRecord]) -> None:
        self.pages[audit_id] = [item.model_copy(deep=True) for item in pages]

    def list_pages(self, audit_id: str) -> list[PageRecord]:
        return [item.model_copy(deep=True) for item in self.pages.get(audit_id, [])]

    def replace_findings(self, audit_id: str, findings: list[Finding]) -> None:
        self.findings[audit_id] = [item.model_copy(deep=True) for item in findings]

    def list_findings(self, audit_id: str) -> list[Finding]:
        return [
            item.model_copy(deep=True)
            for item in sorted(
                self.findings.get(audit_id, []),
                key=lambda item: (-item.score, item.rule_id),
            )
        ]

    def save_report(self, report: AuditReport) -> None:
        self.get_audit(report.audit_id)
        self.reports[report.audit_id] = report.model_copy(deep=True)
        self.update_audit(
            report.audit_id,
            status=AuditStatus.COMPLETE,
            stage=AuditStage.COMPLETE,
            progress=100,
        )

    def get_report(self, audit_id: str) -> AuditReport | None:
        self.get_audit(audit_id)
        report = self.reports.get(audit_id)
        return report.model_copy(deep=True) if report else None

    def counts(self, audit_id: str) -> tuple[int, int]:
        return len(self.pages.get(audit_id, [])), len(self.findings.get(audit_id, []))
