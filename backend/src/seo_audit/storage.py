from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from seo_audit.models import (
    AuditCreate,
    AuditRecord,
    AuditReport,
    AuditStage,
    AuditStatus,
    Finding,
    LinkRecord,
    PageRecord,
    utc_now,
)


class AuditNotFoundError(LookupError):
    pass


class AuditRepository:
    def __init__(self, database_path: Path, database_url: str | None = None):
        self.database_path = database_path
        self.database_url = database_url
        self.is_postgres = bool(database_url)
        if not self.is_postgres:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[Any]:
        if self.is_postgres:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError(
                    "PostgreSQL requires the 'psycopg[binary]' package"
                ) from exc
            connection = psycopg.connect(
                self.database_url,
                row_factory=dict_row,
                prepare_threshold=None,
            )
        else:
            connection = sqlite3.connect(self.database_path, timeout=30)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _sql(self, statement: str, params: Any = None) -> str:
        if not self.is_postgres:
            return statement
        if isinstance(params, dict):
            return re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"%(\1)s", statement)
        return statement.replace("?", "%s")

    def _execute(self, connection: Any, statement: str, params: Any = None):
        sql = self._sql(statement, params)
        return connection.execute(sql) if params is None else connection.execute(sql, params)

    def _executemany(self, connection: Any, statement: str, params: list[tuple[Any, ...]]):
        if not params:
            return None
        sql = self._sql(statement, params)
        if self.is_postgres:
            with connection.cursor() as cursor:
                cursor.executemany(sql, params)
            return None
        return connection.executemany(sql, params)

    def initialize(self) -> None:
        with self.connect() as connection:
            schema = """
                CREATE TABLE IF NOT EXISTS audits (
                    id TEXT PRIMARY KEY,
                    requested_url TEXT NOT NULL,
                    normalized_origin TEXT,
                    business_description TEXT,
                    audit_reason TEXT,
                    important_urls_json TEXT NOT NULL,
                    crawl_limit INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    warnings_json TEXT NOT NULL,
                    error TEXT,
                    report_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pages (
                    id TEXT PRIMARY KEY,
                    audit_id TEXT NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
                    requested_url TEXT NOT NULL,
                    final_url TEXT NOT NULL,
                    status_code INTEGER,
                    depth INTEGER NOT NULL,
                    content_type TEXT,
                    title TEXT,
                    meta_description TEXT,
                    canonical TEXT,
                    robots_directives_json TEXT NOT NULL,
                    h1_json TEXT NOT NULL,
                    h2_json TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    internal_links_json TEXT NOT NULL,
                    images_total INTEGER NOT NULL,
                    images_missing_alt INTEGER NOT NULL,
                    schema_types_json TEXT NOT NULL,
                    has_viewport INTEGER NOT NULL,
                    content_hash TEXT,
                    fetch_error TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_pages_audit ON pages(audit_id);

                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    audit_id TEXT NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
                    rule_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    why_it_matters TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    affected_urls_json TEXT NOT NULL,
                    score REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_findings_audit ON findings(audit_id);
                """
            if self.is_postgres:
                for statement in schema.split(";"):
                    if statement.strip():
                        connection.execute(statement)
            else:
                connection.executescript(schema)

    def create_audit(self, request: AuditCreate, crawl_limit: int) -> AuditRecord:
        audit = AuditRecord(
            requested_url=request.url,
            business_description=request.business_description,
            audit_reason=request.audit_reason,
            important_urls=request.important_urls,
            crawl_limit=crawl_limit,
        )
        with self.connect() as connection:
            self._execute(connection,
                """
                INSERT INTO audits (
                    id, requested_url, normalized_origin, business_description,
                    audit_reason, important_urls_json, crawl_limit, status, stage,
                    progress, warnings_json, error, report_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit.id,
                    audit.requested_url,
                    audit.normalized_origin,
                    audit.business_description,
                    audit.audit_reason,
                    json.dumps(audit.important_urls),
                    audit.crawl_limit,
                    audit.status.value,
                    audit.stage.value,
                    audit.progress,
                    json.dumps(audit.warnings),
                    audit.error,
                    None,
                    audit.created_at.isoformat(),
                    audit.updated_at.isoformat(),
                ),
            )
        return audit

    def get_audit(self, audit_id: str) -> AuditRecord:
        with self.connect() as connection:
            row = self._execute(connection,
                "SELECT * FROM audits WHERE id = ?", (audit_id,)
            ).fetchone()
        if row is None:
            raise AuditNotFoundError(audit_id)
        return self._audit_from_row(row)

    def list_audits(
        self, limit: int = 20, offset: int = 0, query: str | None = None
    ) -> list[AuditRecord]:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(connection,
                    "SELECT * FROM audits WHERE requested_url LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (pattern, limit, offset),
                ).fetchall()
            else:
                rows = self._execute(connection,
                    "SELECT * FROM audits ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
        return [self._audit_from_row(row) for row in rows]

    def count_audits(self, query: str | None = None) -> int:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                return int(self._execute(connection,
                    "SELECT COUNT(*) AS total FROM audits WHERE requested_url LIKE ?", (pattern,)
                ).fetchone()["total"])
            return int(self._execute(connection, "SELECT COUNT(*) AS total FROM audits").fetchone()["total"])

    def delete_audit(self, audit_id: str) -> None:
        self.get_audit(audit_id)
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM audits WHERE id = ?", (audit_id,))

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
        values = {
            "status": (status or current.status).value,
            "stage": (stage or current.stage).value,
            "progress": current.progress if progress is None else progress,
            "normalized_origin": current.normalized_origin
            if normalized_origin is None
            else normalized_origin,
            "warnings_json": json.dumps(current.warnings if warnings is None else warnings),
            "error": error,
            "updated_at": utc_now().isoformat(),
            "id": audit_id,
        }
        with self.connect() as connection:
            self._execute(connection,
                """
                UPDATE audits
                SET status = :status, stage = :stage, progress = :progress,
                    normalized_origin = :normalized_origin,
                    warnings_json = :warnings_json, error = :error,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                values,
            )
        return self.get_audit(audit_id)

    def claim_next_audit(self) -> AuditRecord | None:
        with self.connect() as connection:
            if not self.is_postgres:
                connection.execute("BEGIN IMMEDIATE")
            row = self._execute(connection,
                """
                SELECT id FROM audits
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT 1
                """ + (" FOR UPDATE SKIP LOCKED" if self.is_postgres else """"""),
                (AuditStatus.QUEUED.value,),
            ).fetchone()
            if row is None:
                return None
            now = utc_now().isoformat()
            updated = self._execute(connection,
                """
                UPDATE audits
                SET status = ?, stage = ?, progress = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (
                    AuditStatus.RUNNING.value,
                    AuditStage.VALIDATING.value,
                    2,
                    now,
                    row["id"],
                    AuditStatus.QUEUED.value,
                ),
            )
            if updated.rowcount != 1:
                return None
        return self.get_audit(row["id"])

    def claim_audit(self, audit_id: str) -> AuditRecord | None:
        """Atomically claim one queued audit for a serverless invocation."""
        with self.connect() as connection:
            updated = self._execute(
                connection,
                """
                UPDATE audits
                SET status = ?, stage = ?, progress = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (
                    AuditStatus.RUNNING.value,
                    AuditStage.VALIDATING.value,
                    2,
                    utc_now().isoformat(),
                    audit_id,
                    AuditStatus.QUEUED.value,
                ),
            )
            if updated.rowcount != 1:
                return None
        return self.get_audit(audit_id)

    def retry_audit(self, audit_id: str) -> AuditRecord:
        audit = self.get_audit(audit_id)
        if audit.status not in {AuditStatus.FAILED, AuditStatus.COMPLETE}:
            raise ValueError("Only failed or completed audits can be queued again")
        self.replace_pages(audit_id, [])
        self.replace_findings(audit_id, [])
        with self.connect() as connection:
            self._execute(connection,
                """
                UPDATE audits
                SET status = ?, stage = ?, progress = 0, warnings_json = '[]',
                    error = NULL, report_json = NULL, updated_at = ?
                WHERE id = ?
                """,
                (
                    AuditStatus.QUEUED.value,
                    AuditStage.QUEUED.value,
                    utc_now().isoformat(),
                    audit_id,
                ),
            )
        return self.get_audit(audit_id)

    def replace_pages(self, audit_id: str, pages: list[PageRecord]) -> None:
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM pages WHERE audit_id = ?", (audit_id,))
            self._executemany(connection,
                """
                INSERT INTO pages (
                    id, audit_id, requested_url, final_url, status_code, depth,
                    content_type, title, meta_description, canonical,
                    robots_directives_json, h1_json, h2_json, word_count,
                    internal_links_json, images_total, images_missing_alt,
                    schema_types_json, has_viewport, content_hash, fetch_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        page.id,
                        page.audit_id,
                        page.requested_url,
                        page.final_url,
                        page.status_code,
                        page.depth,
                        page.content_type,
                        page.title,
                        page.meta_description,
                        page.canonical,
                        json.dumps(page.robots_directives),
                        json.dumps(page.h1),
                        json.dumps(page.h2),
                        page.word_count,
                        json.dumps([link.model_dump() for link in page.internal_links]),
                        page.images_total,
                        page.images_missing_alt,
                        json.dumps(page.schema_types),
                        int(page.has_viewport),
                        page.content_hash,
                        page.fetch_error,
                    )
                    for page in pages
                ],
            )

    def list_pages(self, audit_id: str) -> list[PageRecord]:
        with self.connect() as connection:
            rows = self._execute(connection,
                "SELECT * FROM pages WHERE audit_id = ? ORDER BY depth, requested_url",
                (audit_id,),
            ).fetchall()
        return [self._page_from_row(row) for row in rows]

    def replace_findings(self, audit_id: str, findings: list[Finding]) -> None:
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM findings WHERE audit_id = ?", (audit_id,))
            self._executemany(connection,
                """
                INSERT INTO findings (
                    id, audit_id, rule_id, title, severity, confidence, evidence,
                    why_it_matters, recommendation, affected_urls_json, score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        finding.id,
                        finding.audit_id,
                        finding.rule_id,
                        finding.title,
                        finding.severity.value,
                        finding.confidence.value,
                        finding.evidence,
                        finding.why_it_matters,
                        finding.recommendation,
                        json.dumps(finding.affected_urls),
                        finding.score,
                    )
                    for finding in findings
                ],
            )

    def list_findings(self, audit_id: str) -> list[Finding]:
        with self.connect() as connection:
            rows = self._execute(connection,
                """
                SELECT * FROM findings
                WHERE audit_id = ?
                ORDER BY score DESC, rule_id ASC
                """,
                (audit_id,),
            ).fetchall()
        return [self._finding_from_row(row) for row in rows]

    def save_report(self, report: AuditReport) -> None:
        with self.connect() as connection:
            self._execute(connection,
                """
                UPDATE audits
                SET report_json = ?, status = ?, stage = ?, progress = 100,
                    error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (
                    report.model_dump_json(),
                    AuditStatus.COMPLETE.value,
                    AuditStage.COMPLETE.value,
                    utc_now().isoformat(),
                    report.audit_id,
                ),
            )

    def get_report(self, audit_id: str) -> AuditReport | None:
        with self.connect() as connection:
            row = self._execute(connection,
                "SELECT report_json FROM audits WHERE id = ?", (audit_id,)
            ).fetchone()
        if row is None:
            raise AuditNotFoundError(audit_id)
        if not row["report_json"]:
            return None
        return AuditReport.model_validate_json(row["report_json"])

    def counts(self, audit_id: str) -> tuple[int, int]:
        with self.connect() as connection:
            page_count = self._execute(connection,
                "SELECT COUNT(*) AS total FROM pages WHERE audit_id = ?", (audit_id,)
            ).fetchone()["total"]
            finding_count = self._execute(connection,
                "SELECT COUNT(*) AS total FROM findings WHERE audit_id = ?", (audit_id,)
            ).fetchone()["total"]
        return page_count, finding_count

    @staticmethod
    def _audit_from_row(row: Any) -> AuditRecord:
        return AuditRecord(
            id=row["id"],
            requested_url=row["requested_url"],
            normalized_origin=row["normalized_origin"],
            business_description=row["business_description"],
            audit_reason=row["audit_reason"],
            important_urls=json.loads(row["important_urls_json"]),
            crawl_limit=row["crawl_limit"],
            status=row["status"],
            stage=row["stage"],
            progress=row["progress"],
            warnings=json.loads(row["warnings_json"]),
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _page_from_row(row: Any) -> PageRecord:
        return PageRecord(
            id=row["id"],
            audit_id=row["audit_id"],
            requested_url=row["requested_url"],
            final_url=row["final_url"],
            status_code=row["status_code"],
            depth=row["depth"],
            content_type=row["content_type"],
            title=row["title"],
            meta_description=row["meta_description"],
            canonical=row["canonical"],
            robots_directives=json.loads(row["robots_directives_json"]),
            h1=json.loads(row["h1_json"]),
            h2=json.loads(row["h2_json"]),
            word_count=row["word_count"],
            internal_links=[
                LinkRecord.model_validate(link)
                for link in json.loads(row["internal_links_json"])
            ],
            images_total=row["images_total"],
            images_missing_alt=row["images_missing_alt"],
            schema_types=json.loads(row["schema_types_json"]),
            has_viewport=bool(row["has_viewport"]),
            content_hash=row["content_hash"],
            fetch_error=row["fetch_error"],
        )

    @staticmethod
    def _finding_from_row(row: Any) -> Finding:
        return Finding(
            id=row["id"],
            audit_id=row["audit_id"],
            rule_id=row["rule_id"],
            title=row["title"],
            severity=row["severity"],
            confidence=row["confidence"],
            evidence=row["evidence"],
            why_it_matters=row["why_it_matters"],
            recommendation=row["recommendation"],
            affected_urls=json.loads(row["affected_urls_json"]),
            score=row["score"],
        )
