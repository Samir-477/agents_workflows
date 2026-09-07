from __future__ import annotations

from datetime import datetime, timedelta

from agent_runtime.postgres import PostgresRepository
from serp_competitor.models import SerpRequest, SerpResult, SerpRun, utc_now


class SerpNotFoundError(LookupError):
    pass


class SerpRepository(PostgresRepository):
    def initialize(self):
        with self.connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS serp_competitor_runs (
                id TEXT PRIMARY KEY, request_json TEXT NOT NULL, status TEXT NOT NULL,
                stage TEXT NOT NULL, progress INTEGER NOT NULL, result_json TEXT,
                error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_serp_competitor_created_at ON serp_competitor_runs (created_at DESC)")
            connection.execute("ALTER TABLE serp_competitor_runs ENABLE ROW LEVEL SECURITY")

    def create(self, request):
        run = SerpRun(request=request)
        with self.connect() as connection:
            self._execute(connection, "INSERT INTO serp_competitor_runs (id,request_json,status,stage,progress,result_json,error,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (
                run.id, run.request.model_dump_json(), run.status, run.stage, 0, None, None,
                run.created_at.isoformat(), run.updated_at.isoformat(),
            ))
        return run

    def get(self, run_id):
        with self.connect() as connection:
            row = self._execute(connection, "SELECT * FROM serp_competitor_runs WHERE id=?", (run_id,)).fetchone()
        if row is None: raise SerpNotFoundError(run_id)
        return self._from_row(row)

    def list_generations(self, limit=20, offset=0, query=None):
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(connection, "SELECT * FROM serp_competitor_runs WHERE request_json LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (pattern, limit, offset)).fetchall()
            else:
                rows = self._execute(connection, "SELECT * FROM serp_competitor_runs ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [self._from_row(row) for row in rows]

    def count_generations(self, query=None):
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            sql = "SELECT COUNT(*) AS total FROM serp_competitor_runs WHERE request_json LIKE ?" if pattern else "SELECT COUNT(*) AS total FROM serp_competitor_runs"
            row = self._execute(connection, sql, (pattern,) if pattern else None).fetchone()
        return int(row["total"])

    def update(self, run_id, **changes):
        current = self.get(run_id)
        data = {
            "status": changes.get("status", current.status), "stage": changes.get("stage", current.stage),
            "progress": changes.get("progress", current.progress), "error": changes.get("error"),
        }
        with self.connect() as connection:
            self._execute(connection, "UPDATE serp_competitor_runs SET status=?,stage=?,progress=?,error=?,updated_at=? WHERE id=?", (
                data["status"], data["stage"], data["progress"], data["error"], utc_now().isoformat(), run_id,
            ))
        return self.get(run_id)

    def find_fresh_result(self, request, max_age: timedelta = timedelta(hours=6)):
        cutoff = utc_now() - max_age
        for candidate in self.list_generations(100, 0):
            if candidate.status != "complete" or candidate.result is None:
                continue
            same_query = " ".join(candidate.request.target_keyword.casefold().split()) == " ".join(request.target_keyword.casefold().split())
            same_locale = candidate.request.country.casefold() == request.country.casefold() and candidate.request.language.casefold() == request.language.casefold()
            enough_results = candidate.request.result_limit >= request.result_limit
            enough_pages = candidate.request.inspect_limit >= request.inspect_limit
            if same_query and same_locale and enough_results and enough_pages and candidate.result.observed_at >= cutoff:
                return candidate
        return None

    def claim(self, run_id):
        with self.connect() as connection:
            changed = self._execute(connection, "UPDATE serp_competitor_runs SET status='running',stage='searching',progress=5,updated_at=? WHERE id=? AND status='queued'", (utc_now().isoformat(), run_id))
            if changed.rowcount != 1: return None
        return self.get(run_id)

    def save_result(self, result):
        with self.connect() as connection:
            self._execute(connection, "UPDATE serp_competitor_runs SET result_json=?,status='complete',stage='complete',progress=100,error=NULL,updated_at=? WHERE id=?", (result.model_dump_json(), utc_now().isoformat(), result.run_id))

    def retry(self, run_id):
        current = self.get(run_id)
        if current.status not in {"complete", "failed"}: raise ValueError("Only finished runs can be retried.")
        with self.connect() as connection:
            self._execute(connection, "UPDATE serp_competitor_runs SET status='queued',stage='queued',progress=0,result_json=NULL,error=NULL,updated_at=? WHERE id=?", (utc_now().isoformat(), run_id))
        return self.get(run_id)

    def delete(self, run_id):
        self.get(run_id)
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM serp_competitor_runs WHERE id=? AND status!='running'", (run_id,))

    @staticmethod
    def _from_row(row):
        return SerpRun(
            id=row["id"], request=SerpRequest.model_validate_json(row["request_json"]),
            status=row["status"], stage=row["stage"], progress=row["progress"],
            result=SerpResult.model_validate_json(row["result_json"]) if row["result_json"] else None,
            error=row["error"], created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class MemorySerpRepository:
    def __init__(self): self.runs = {}
    def initialize(self): return None
    def create(self, request):
        run = SerpRun(request=request); self.runs[run.id] = run; return run.model_copy(deep=True)
    def get(self, run_id):
        if run_id not in self.runs: raise SerpNotFoundError(run_id)
        return self.runs[run_id].model_copy(deep=True)
    def list_generations(self, limit=20, offset=0, query=None):
        rows = sorted(self.runs.values(), key=lambda item: item.created_at, reverse=True)
        if query and query.strip(): rows = [item for item in rows if query.casefold() in item.request.target_keyword.casefold()]
        return [item.model_copy(deep=True) for item in rows[offset:offset+limit]]
    def count_generations(self, query=None): return len(self.list_generations(10000, 0, query))
    def update(self, run_id, **changes):
        current = self.get(run_id); changes["updated_at"] = utc_now()
        self.runs[run_id] = current.model_copy(update=changes, deep=True); return self.get(run_id)
    def find_fresh_result(self, request, max_age=timedelta(hours=6)):
        cutoff = utc_now() - max_age
        for candidate in self.list_generations(10000):
            if candidate.status != "complete" or candidate.result is None: continue
            same_query = " ".join(candidate.request.target_keyword.casefold().split()) == " ".join(request.target_keyword.casefold().split())
            same_locale = candidate.request.country.casefold() == request.country.casefold() and candidate.request.language.casefold() == request.language.casefold()
            enough_results = candidate.request.result_limit >= request.result_limit
            enough_pages = candidate.request.inspect_limit >= request.inspect_limit
            if same_query and same_locale and enough_results and enough_pages and candidate.result.observed_at >= cutoff: return candidate
        return None
    def claim(self, run_id):
        if self.get(run_id).status != "queued": return None
        return self.update(run_id, status="running", stage="searching", progress=5)
    def save_result(self, result): self.update(result.run_id, result=result, status="complete", stage="complete", progress=100, error=None)
    def retry(self, run_id):
        if self.get(run_id).status not in {"complete", "failed"}: raise ValueError("Only finished runs can be retried.")
        return self.update(run_id, status="queued", stage="queued", progress=0, result=None, error=None)
    def delete(self, run_id): self.get(run_id); self.runs.pop(run_id)
