from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_runtime.postgres import PostgresRepository
from ai_visibility.models import (
    VisibilityCreate, VisibilityRecord, VisibilityResult, VisibilityStage,
    VisibilityStatus, utc_now,
)


class VisibilityNotFoundError(LookupError):
    pass


class VisibilityRepository(PostgresRepository):
    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS ai_visibility_audits (
                    id TEXT PRIMARY KEY, requested_url TEXT NOT NULL,
                    normalized_origin TEXT, business_name TEXT, product_name TEXT,
                    audit_goal TEXT, important_urls_json TEXT NOT NULL,
                    crawl_limit INTEGER NOT NULL, status TEXT NOT NULL, stage TEXT NOT NULL,
                    progress INTEGER NOT NULL, result_json TEXT, warnings_json TEXT NOT NULL,
                    error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_ai_visibility_created_at ON ai_visibility_audits (created_at DESC)")
            connection.execute("ALTER TABLE ai_visibility_audits ENABLE ROW LEVEL SECURITY")

    def create_audit(self, request: VisibilityCreate, default_limit: int = 10) -> VisibilityRecord:
        run = VisibilityRecord(
            requested_url=request.url, business_name=request.business_name,
            product_name=request.product_name, audit_goal=request.audit_goal,
            important_urls=request.important_urls, crawl_limit=request.crawl_limit or min(default_limit, 20),
        )
        with self.connect() as connection:
            self._execute(connection, """INSERT INTO ai_visibility_audits
                (id,requested_url,normalized_origin,business_name,product_name,audit_goal,
                 important_urls_json,crawl_limit,status,stage,progress,result_json,warnings_json,
                 error,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                run.id, run.requested_url, None, run.business_name, run.product_name,
                run.audit_goal, json.dumps(run.important_urls), run.crawl_limit,
                run.status.value, run.stage.value, 0, None, "[]", None,
                run.created_at.isoformat(), run.updated_at.isoformat(),
            ))
        return run

    def get_audit(self, audit_id: str) -> VisibilityRecord:
        with self.connect() as connection:
            row = self._execute(connection, "SELECT * FROM ai_visibility_audits WHERE id = ?", (audit_id,)).fetchone()
        if row is None:
            raise VisibilityNotFoundError(audit_id)
        return self._from_row(row)

    def list_audits(self, limit=20, offset=0, query=None):
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(connection, "SELECT * FROM ai_visibility_audits WHERE requested_url LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (pattern, limit, offset)).fetchall()
            else:
                rows = self._execute(connection, "SELECT * FROM ai_visibility_audits ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [self._from_row(row) for row in rows]

    def count_audits(self, query=None):
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            sql = "SELECT COUNT(*) AS total FROM ai_visibility_audits WHERE requested_url LIKE ?" if pattern else "SELECT COUNT(*) AS total FROM ai_visibility_audits"
            row = self._execute(connection, sql, (pattern,) if pattern else None).fetchone()
        return int(row["total"])

    def delete_audit(self, audit_id):
        self.get_audit(audit_id)
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM ai_visibility_audits WHERE id = ?", (audit_id,))

    def update_audit(self, audit_id, *, status=None, stage=None, progress=None, normalized_origin=None, warnings=None, error=None):
        current = self.get_audit(audit_id)
        with self.connect() as connection:
            self._execute(connection, """UPDATE ai_visibility_audits SET status=?,stage=?,progress=?,normalized_origin=?,warnings_json=?,error=?,updated_at=? WHERE id=?""", (
                (status or current.status).value, (stage or current.stage).value,
                current.progress if progress is None else progress,
                current.normalized_origin if normalized_origin is None else normalized_origin,
                json.dumps(current.warnings if warnings is None else warnings), error,
                utc_now().isoformat(), audit_id,
            ))
        return self.get_audit(audit_id)

    def claim_audit(self, audit_id):
        with self.connect() as connection:
            changed = self._execute(connection, """UPDATE ai_visibility_audits SET status=?,stage=?,progress=2,updated_at=? WHERE id=? AND status=?""", (
                VisibilityStatus.RUNNING.value, VisibilityStage.VALIDATING.value,
                utc_now().isoformat(), audit_id, VisibilityStatus.QUEUED.value,
            ))
            if changed.rowcount != 1:
                return None
        return self.get_audit(audit_id)

    def save_result(self, result):
        with self.connect() as connection:
            self._execute(connection, """UPDATE ai_visibility_audits SET normalized_origin=?,result_json=?,status=?,stage=?,progress=100,warnings_json=?,error=NULL,updated_at=? WHERE id=?""", (
                result.normalized_origin, result.model_dump_json(), VisibilityStatus.COMPLETE.value,
                VisibilityStage.COMPLETE.value, json.dumps(result.warnings), utc_now().isoformat(), result.audit_id,
            ))

    def retry_audit(self, audit_id):
        current = self.get_audit(audit_id)
        if current.status not in {VisibilityStatus.COMPLETE, VisibilityStatus.FAILED}:
            raise ValueError("Only failed or completed audits can be queued again")
        with self.connect() as connection:
            self._execute(connection, """UPDATE ai_visibility_audits SET status=?,stage=?,progress=0,result_json=NULL,warnings_json='[]',error=NULL,updated_at=? WHERE id=?""", (
                VisibilityStatus.QUEUED.value, VisibilityStage.QUEUED.value, utc_now().isoformat(), audit_id,
            ))
        return self.get_audit(audit_id)

    @staticmethod
    def _from_row(row: Any) -> VisibilityRecord:
        return VisibilityRecord(
            id=row["id"], requested_url=row["requested_url"], normalized_origin=row["normalized_origin"],
            business_name=row["business_name"], product_name=row["product_name"], audit_goal=row["audit_goal"],
            important_urls=json.loads(row["important_urls_json"]), crawl_limit=row["crawl_limit"],
            status=row["status"], stage=row["stage"], progress=row["progress"],
            result=VisibilityResult.model_validate_json(row["result_json"]) if row["result_json"] else None,
            warnings=json.loads(row["warnings_json"]), error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class MemoryVisibilityRepository:
    def __init__(self): self.runs: dict[str, VisibilityRecord] = {}
    def initialize(self): return None
    def create_audit(self, request, default_limit=10):
        run = VisibilityRecord(requested_url=request.url, business_name=request.business_name, product_name=request.product_name, audit_goal=request.audit_goal, important_urls=request.important_urls, crawl_limit=request.crawl_limit or min(default_limit, 20))
        self.runs[run.id] = run
        return run.model_copy(deep=True)
    def get_audit(self, audit_id):
        if audit_id not in self.runs: raise VisibilityNotFoundError(audit_id)
        return self.runs[audit_id].model_copy(deep=True)
    def list_audits(self, limit=20, offset=0, query=None):
        runs = sorted(self.runs.values(), key=lambda x: x.created_at, reverse=True)
        if query and query.strip(): runs = [r for r in runs if query.strip().casefold() in r.requested_url.casefold()]
        return [r.model_copy(deep=True) for r in runs[offset:offset+limit]]
    def count_audits(self, query=None): return len(self.list_audits(10_000, 0, query))
    def delete_audit(self, audit_id): self.get_audit(audit_id); self.runs.pop(audit_id)
    def update_audit(self, audit_id, **changes):
        current = self.get_audit(audit_id)
        data = {"status": changes.get("status") or current.status, "stage": changes.get("stage") or current.stage, "progress": current.progress if changes.get("progress") is None else changes["progress"], "normalized_origin": current.normalized_origin if changes.get("normalized_origin") is None else changes["normalized_origin"], "warnings": current.warnings if changes.get("warnings") is None else changes["warnings"], "error": changes.get("error"), "updated_at": utc_now()}
        self.runs[audit_id] = current.model_copy(update=data, deep=True)
        return self.get_audit(audit_id)
    def claim_audit(self, audit_id):
        if self.get_audit(audit_id).status != VisibilityStatus.QUEUED: return None
        return self.update_audit(audit_id, status=VisibilityStatus.RUNNING, stage=VisibilityStage.VALIDATING, progress=2)
    def save_result(self, result):
        current = self.get_audit(result.audit_id)
        self.runs[result.audit_id] = current.model_copy(update={"normalized_origin": result.normalized_origin, "result": result, "status": VisibilityStatus.COMPLETE, "stage": VisibilityStage.COMPLETE, "progress": 100, "warnings": result.warnings, "error": None, "updated_at": utc_now()}, deep=True)
    def retry_audit(self, audit_id):
        current = self.get_audit(audit_id)
        if current.status not in {VisibilityStatus.COMPLETE, VisibilityStatus.FAILED}: raise ValueError("Only failed or completed audits can be queued again")
        self.runs[audit_id] = current.model_copy(update={"status": VisibilityStatus.QUEUED, "stage": VisibilityStage.QUEUED, "progress": 0, "result": None, "warnings": [], "error": None, "updated_at": utc_now()}, deep=True)
        return self.get_audit(audit_id)
