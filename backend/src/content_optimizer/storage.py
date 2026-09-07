from __future__ import annotations

from datetime import datetime

from agent_runtime.postgres import PostgresRepository
from content_optimizer.models import (
    ContentOptimizerRequest,
    ContentOptimizerResult,
    ContentOptimizerRun,
    utc_now,
)


class ContentOptimizerNotFoundError(LookupError):
    pass


class ContentOptimizerRepository(PostgresRepository):
    def initialize(self):
        with self.connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS content_optimizer_runs (
                id TEXT PRIMARY KEY, request_json TEXT NOT NULL, status TEXT NOT NULL,
                stage TEXT NOT NULL, progress INTEGER NOT NULL, result_json TEXT,
                error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_content_optimizer_created_at ON content_optimizer_runs (created_at DESC)")
            connection.execute("ALTER TABLE content_optimizer_runs ENABLE ROW LEVEL SECURITY")

    def create(self, request):
        run = ContentOptimizerRun(request=request)
        with self.connect() as connection:
            self._execute(connection, "INSERT INTO content_optimizer_runs (id,request_json,status,stage,progress,result_json,error,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (
                run.id, run.request.model_dump_json(), run.status, run.stage, 0, None, None,
                run.created_at.isoformat(), run.updated_at.isoformat(),
            ))
        return run

    def get(self, run_id):
        with self.connect() as connection:
            row = self._execute(connection, "SELECT * FROM content_optimizer_runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise ContentOptimizerNotFoundError(run_id)
        return self._from_row(row)

    def list_generations(self, limit=20, offset=0, query=None):
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(connection, "SELECT * FROM content_optimizer_runs WHERE request_json LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (pattern, limit, offset)).fetchall()
            else:
                rows = self._execute(connection, "SELECT * FROM content_optimizer_runs ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [self._from_row(row) for row in rows]

    def count_generations(self, query=None):
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            sql = "SELECT COUNT(*) AS total FROM content_optimizer_runs WHERE request_json LIKE ?" if pattern else "SELECT COUNT(*) AS total FROM content_optimizer_runs"
            row = self._execute(connection, sql, (pattern,) if pattern else None).fetchone()
        return int(row["total"])

    def update(self, run_id, **changes):
        current = self.get(run_id)
        values = {
            "status": changes.get("status", current.status),
            "stage": changes.get("stage", current.stage),
            "progress": changes.get("progress", current.progress),
            "error": changes.get("error"),
        }
        with self.connect() as connection:
            self._execute(connection, "UPDATE content_optimizer_runs SET status=?,stage=?,progress=?,error=?,updated_at=? WHERE id=?", (
                values["status"], values["stage"], values["progress"], values["error"], utc_now().isoformat(), run_id,
            ))
        return self.get(run_id)

    def claim(self, run_id):
        with self.connect() as connection:
            changed = self._execute(connection, "UPDATE content_optimizer_runs SET status='running',stage='loading_content',progress=5,updated_at=? WHERE id=? AND status='queued'", (utc_now().isoformat(), run_id))
            if changed.rowcount != 1:
                return None
        return self.get(run_id)

    def save_result(self, result):
        with self.connect() as connection:
            self._execute(connection, "UPDATE content_optimizer_runs SET result_json=?,status='complete',stage='complete',progress=100,error=NULL,updated_at=? WHERE id=?", (result.model_dump_json(), utc_now().isoformat(), result.run_id))

    def retry(self, run_id):
        current = self.get(run_id)
        if current.status not in {"complete", "failed"}:
            raise ValueError("Only finished runs can be retried.")
        with self.connect() as connection:
            self._execute(connection, "UPDATE content_optimizer_runs SET status='queued',stage='queued',progress=0,result_json=NULL,error=NULL,updated_at=? WHERE id=?", (utc_now().isoformat(), run_id))
        return self.get(run_id)

    def delete(self, run_id):
        current = self.get(run_id)
        if current.status == "running":
            raise ValueError("Wait for this run to finish.")
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM content_optimizer_runs WHERE id=?", (run_id,))

    @staticmethod
    def _from_row(row):
        return ContentOptimizerRun(
            id=row["id"], request=ContentOptimizerRequest.model_validate_json(row["request_json"]),
            status=row["status"], stage=row["stage"], progress=row["progress"],
            result=ContentOptimizerResult.model_validate_json(row["result_json"]) if row["result_json"] else None,
            error=row["error"], created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class MemoryContentOptimizerRepository:
    def __init__(self): self.runs = {}
    def initialize(self): return None
    def create(self, request):
        run = ContentOptimizerRun(request=request); self.runs[run.id] = run; return run.model_copy(deep=True)
    def get(self, run_id):
        if run_id not in self.runs: raise ContentOptimizerNotFoundError(run_id)
        return self.runs[run_id].model_copy(deep=True)
    def list_generations(self, limit=20, offset=0, query=None):
        rows = sorted(self.runs.values(), key=lambda item: item.created_at, reverse=True)
        if query and query.strip():
            needle = query.casefold()
            rows = [item for item in rows if needle in item.request.target_keyword.casefold() or needle in (item.request.content_url or "").casefold()]
        return [item.model_copy(deep=True) for item in rows[offset:offset + limit]]
    def count_generations(self, query=None): return len(self.list_generations(10000, 0, query))
    def update(self, run_id, **changes):
        current = self.get(run_id); changes["updated_at"] = utc_now()
        self.runs[run_id] = current.model_copy(update=changes, deep=True); return self.get(run_id)
    def claim(self, run_id):
        if self.get(run_id).status != "queued": return None
        return self.update(run_id, status="running", stage="loading_content", progress=5)
    def save_result(self, result): self.update(result.run_id, result=result, status="complete", stage="complete", progress=100, error=None)
    def retry(self, run_id):
        if self.get(run_id).status not in {"complete", "failed"}: raise ValueError("Only finished runs can be retried.")
        return self.update(run_id, status="queued", stage="queued", progress=0, result=None, error=None)
    def delete(self, run_id):
        if self.get(run_id).status == "running": raise ValueError("Wait for this run to finish.")
        self.runs.pop(run_id)
