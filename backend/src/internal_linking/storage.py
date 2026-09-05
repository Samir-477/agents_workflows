from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_runtime.postgres import PostgresRepository
from internal_linking.models import (
    InternalLinkCreate,
    InternalLinkRecord,
    InternalLinkResult,
    InternalLinkStage,
    InternalLinkStatus,
    utc_now,
)


class InternalLinkNotFoundError(LookupError):
    pass


class InternalLinkRepository(PostgresRepository):
    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS internal_link_audits (
                    id TEXT PRIMARY KEY, requested_url TEXT NOT NULL,
                    normalized_origin TEXT, business_description TEXT, audit_goal TEXT,
                    important_urls_json TEXT NOT NULL, crawl_limit INTEGER NOT NULL,
                    status TEXT NOT NULL, stage TEXT NOT NULL, progress INTEGER NOT NULL,
                    result_json TEXT, warnings_json TEXT NOT NULL, error TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_internal_link_audits_created_at "
                "ON internal_link_audits (created_at DESC)"
            )
            connection.execute("ALTER TABLE internal_link_audits ENABLE ROW LEVEL SECURITY")

    def create_audit(
        self, request: InternalLinkCreate, default_limit: int = 20
    ) -> InternalLinkRecord:
        run = InternalLinkRecord(
            requested_url=request.url,
            business_description=request.business_description,
            audit_goal=request.audit_goal,
            important_urls=request.important_urls,
            crawl_limit=request.crawl_limit or default_limit,
        )
        with self.connect() as connection:
            self._execute(connection, """
                INSERT INTO internal_link_audits
                (id,requested_url,normalized_origin,business_description,audit_goal,
                 important_urls_json,crawl_limit,status,stage,progress,result_json,
                 warnings_json,error,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                run.id, run.requested_url, None, run.business_description, run.audit_goal,
                json.dumps(run.important_urls), run.crawl_limit, run.status.value,
                run.stage.value, 0, None, "[]", None, run.created_at.isoformat(),
                run.updated_at.isoformat(),
            ))
        return run

    def get_audit(self, audit_id: str) -> InternalLinkRecord:
        with self.connect() as connection:
            row = self._execute(
                connection, "SELECT * FROM internal_link_audits WHERE id = ?", (audit_id,)
            ).fetchone()
        if row is None:
            raise InternalLinkNotFoundError(audit_id)
        return self._from_row(row)

    def list_audits(
        self, limit: int = 20, offset: int = 0, query: str | None = None
    ) -> list[InternalLinkRecord]:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(
                    connection,
                    "SELECT * FROM internal_link_audits WHERE requested_url LIKE ? "
                    "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (pattern, limit, offset),
                ).fetchall()
            else:
                rows = self._execute(
                    connection,
                    "SELECT * FROM internal_link_audits ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
        return [self._from_row(row) for row in rows]

    def count_audits(self, query: str | None = None) -> int:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            sql = (
                "SELECT COUNT(*) AS total FROM internal_link_audits WHERE requested_url LIKE ?"
                if pattern else "SELECT COUNT(*) AS total FROM internal_link_audits"
            )
            row = self._execute(connection, sql, (pattern,) if pattern else None).fetchone()
        return int(row["total"])

    def delete_audit(self, audit_id: str) -> None:
        self.get_audit(audit_id)
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM internal_link_audits WHERE id = ?", (audit_id,))

    def update_audit(
        self, audit_id: str, *, status=None, stage=None, progress=None,
        normalized_origin=None, warnings=None, error=None,
    ) -> InternalLinkRecord:
        current = self.get_audit(audit_id)
        with self.connect() as connection:
            self._execute(connection, """
                UPDATE internal_link_audits
                SET status=?,stage=?,progress=?,normalized_origin=?,warnings_json=?,error=?,updated_at=?
                WHERE id=?
            """, (
                (status or current.status).value,
                (stage or current.stage).value,
                current.progress if progress is None else progress,
                current.normalized_origin if normalized_origin is None else normalized_origin,
                json.dumps(current.warnings if warnings is None else warnings),
                error, utc_now().isoformat(), audit_id,
            ))
        return self.get_audit(audit_id)

    def claim_audit(self, audit_id: str) -> InternalLinkRecord | None:
        with self.connect() as connection:
            updated = self._execute(connection, """
                UPDATE internal_link_audits SET status=?,stage=?,progress=?,updated_at=?
                WHERE id=? AND status=?
            """, (
                InternalLinkStatus.RUNNING.value, InternalLinkStage.VALIDATING.value,
                2, utc_now().isoformat(), audit_id, InternalLinkStatus.QUEUED.value,
            ))
            if updated.rowcount != 1:
                return None
        return self.get_audit(audit_id)

    def save_result(self, result: InternalLinkResult) -> None:
        with self.connect() as connection:
            self._execute(connection, """
                UPDATE internal_link_audits
                SET normalized_origin=?,result_json=?,status=?,stage=?,progress=100,
                    warnings_json=?,error=NULL,updated_at=? WHERE id=?
            """, (
                result.normalized_origin, result.model_dump_json(),
                InternalLinkStatus.COMPLETE.value, InternalLinkStage.COMPLETE.value,
                json.dumps(result.warnings), utc_now().isoformat(), result.audit_id,
            ))

    def retry_audit(self, audit_id: str) -> InternalLinkRecord:
        current = self.get_audit(audit_id)
        if current.status not in {InternalLinkStatus.COMPLETE, InternalLinkStatus.FAILED}:
            raise ValueError("Only failed or completed audits can be queued again")
        with self.connect() as connection:
            self._execute(connection, """
                UPDATE internal_link_audits SET status=?,stage=?,progress=0,
                    result_json=NULL,warnings_json='[]',error=NULL,updated_at=? WHERE id=?
            """, (
                InternalLinkStatus.QUEUED.value, InternalLinkStage.QUEUED.value,
                utc_now().isoformat(), audit_id,
            ))
        return self.get_audit(audit_id)

    @staticmethod
    def _from_row(row: Any) -> InternalLinkRecord:
        return InternalLinkRecord(
            id=row["id"], requested_url=row["requested_url"],
            normalized_origin=row["normalized_origin"],
            business_description=row["business_description"], audit_goal=row["audit_goal"],
            important_urls=json.loads(row["important_urls_json"]),
            crawl_limit=row["crawl_limit"], status=row["status"], stage=row["stage"],
            progress=row["progress"],
            result=InternalLinkResult.model_validate_json(row["result_json"])
            if row["result_json"] else None,
            warnings=json.loads(row["warnings_json"]), error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class MemoryInternalLinkRepository:
    def __init__(self) -> None:
        self.runs: dict[str, InternalLinkRecord] = {}

    def initialize(self) -> None:
        return None

    def create_audit(self, request: InternalLinkCreate, default_limit: int = 20) -> InternalLinkRecord:
        run = InternalLinkRecord(
            requested_url=request.url, business_description=request.business_description,
            audit_goal=request.audit_goal, important_urls=request.important_urls,
            crawl_limit=request.crawl_limit or default_limit,
        )
        self.runs[run.id] = run
        return run.model_copy(deep=True)

    def get_audit(self, audit_id: str) -> InternalLinkRecord:
        try:
            return self.runs[audit_id].model_copy(deep=True)
        except KeyError as exc:
            raise InternalLinkNotFoundError(audit_id) from exc

    def list_audits(self, limit=20, offset=0, query=None):
        runs = sorted(self.runs.values(), key=lambda item: item.created_at, reverse=True)
        if query and query.strip():
            needle = query.strip().casefold()
            runs = [run for run in runs if needle in run.requested_url.casefold()]
        return [run.model_copy(deep=True) for run in runs[offset:offset + limit]]

    def count_audits(self, query=None):
        if not query or not query.strip():
            return len(self.runs)
        needle = query.strip().casefold()
        return sum(needle in run.requested_url.casefold() for run in self.runs.values())

    def delete_audit(self, audit_id):
        self.get_audit(audit_id)
        self.runs.pop(audit_id)

    def update_audit(self, audit_id, *, status=None, stage=None, progress=None, normalized_origin=None, warnings=None, error=None):
        current = self.get_audit(audit_id)
        updated = current.model_copy(update={
            "status": status or current.status, "stage": stage or current.stage,
            "progress": current.progress if progress is None else progress,
            "normalized_origin": current.normalized_origin if normalized_origin is None else normalized_origin,
            "warnings": current.warnings if warnings is None else warnings,
            "error": error, "updated_at": utc_now(),
        }, deep=True)
        self.runs[audit_id] = updated
        return updated.model_copy(deep=True)

    def claim_audit(self, audit_id):
        current = self.get_audit(audit_id)
        if current.status != InternalLinkStatus.QUEUED:
            return None
        return self.update_audit(audit_id, status=InternalLinkStatus.RUNNING, stage=InternalLinkStage.VALIDATING, progress=2)

    def save_result(self, result):
        current = self.get_audit(result.audit_id)
        self.runs[result.audit_id] = current.model_copy(update={
            "normalized_origin": result.normalized_origin, "result": result,
            "status": InternalLinkStatus.COMPLETE, "stage": InternalLinkStage.COMPLETE,
            "progress": 100, "warnings": result.warnings, "error": None,
            "updated_at": utc_now(),
        }, deep=True)

    def retry_audit(self, audit_id):
        current = self.get_audit(audit_id)
        if current.status not in {InternalLinkStatus.COMPLETE, InternalLinkStatus.FAILED}:
            raise ValueError("Only failed or completed audits can be queued again")
        retried = current.model_copy(update={
            "status": InternalLinkStatus.QUEUED, "stage": InternalLinkStage.QUEUED,
            "progress": 0, "result": None, "warnings": [], "error": None,
            "updated_at": utc_now(),
        }, deep=True)
        self.runs[audit_id] = retried
        return retried.model_copy(deep=True)
