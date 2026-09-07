from datetime import UTC, datetime
from threading import Lock

from agent_runtime.postgres import PostgresRepository
from local_seo.models import LocalRun

DDL = """CREATE TABLE IF NOT EXISTS local_seo_generations (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS local_seo_created_idx ON local_seo_generations(created_at DESC);
ALTER TABLE local_seo_generations ENABLE ROW LEVEL SECURITY;
"""


class LocalRepository(PostgresRepository):
    def initialize(self):
        with self.connect() as connection:
            connection.execute(DDL)

    def create(self, request):
        run = LocalRun(request=request)
        with self.connect() as connection:
            connection.execute("INSERT INTO local_seo_generations VALUES (%s,%s,%s,%s,%s)",
                               (run.id, run.model_dump_json(), run.status, request.prompt, run.created_at.isoformat()))
        return run

    def get(self, run_id):
        with self.connect() as connection:
            row = connection.execute("SELECT record_json FROM local_seo_generations WHERE id=%s", (run_id,)).fetchone()
        if not row:
            raise KeyError(run_id)
        return LocalRun.model_validate_json(row["record_json"])

    def mutate(self, run_id, *, expected=None, expected_updated_at=None, **updates):
        with self.connect() as connection:
            row = connection.execute("SELECT record_json FROM local_seo_generations WHERE id=%s FOR UPDATE", (run_id,)).fetchone()
            if not row:
                raise KeyError(run_id)
            run = LocalRun.model_validate_json(row["record_json"])
            if expected and run.status not in expected:
                return None
            if expected_updated_at is not None and run.updated_at != expected_updated_at:
                return None
            run = run.model_copy(update={**updates, "updated_at": datetime.now(UTC)})
            connection.execute("UPDATE local_seo_generations SET record_json=%s,status=%s WHERE id=%s", (run.model_dump_json(), run.status, run_id))
            return run

    def list_generations(self, limit=10, offset=0, query=None):
        with self.connect() as connection:
            rows = connection.execute("SELECT record_json FROM local_seo_generations WHERE prompt ILIKE %s ORDER BY created_at DESC LIMIT %s OFFSET %s", (f"%{query or ''}%", limit, offset)).fetchall()
        return [LocalRun.model_validate_json(row["record_json"]) for row in rows]

    def count_generations(self, query=None):
        with self.connect() as connection:
            return connection.execute("SELECT COUNT(*) AS count FROM local_seo_generations WHERE prompt ILIKE %s", (f"%{query or ''}%",)).fetchone()["count"]

    def delete(self, run_id):
        with self.connect() as connection:
            row = connection.execute("DELETE FROM local_seo_generations WHERE id=%s AND status != 'running' RETURNING id", (run_id,)).fetchone()
            return row is not None


class MemoryLocalRepository:
    def __init__(self):
        self.runs = {}
        self.lock = Lock()

    def initialize(self):
        pass

    def create(self, request):
        run = LocalRun(request=request)
        self.runs[run.id] = run
        return run.model_copy(deep=True)

    def get(self, run_id):
        return self.runs[run_id].model_copy(deep=True)

    def mutate(self, run_id, *, expected=None, expected_updated_at=None, **updates):
        with self.lock:
            run = self.get(run_id)
            if expected and run.status not in expected:
                return None
            if expected_updated_at is not None and run.updated_at != expected_updated_at:
                return None
            run = run.model_copy(update={**updates, "updated_at": datetime.now(UTC)})
            self.runs[run_id] = run
            return run.model_copy(deep=True)

    def list_generations(self, limit=10, offset=0, query=None):
        runs = sorted((r for r in self.runs.values() if (query or "").casefold() in r.request.prompt.casefold()), key=lambda r: r.created_at, reverse=True)
        return [r.model_copy(deep=True) for r in runs[offset:offset + limit]]

    def count_generations(self, query=None):
        return sum((query or "").casefold() in r.request.prompt.casefold() for r in self.runs.values())

    def delete(self, run_id):
        with self.lock:
            if run_id not in self.runs or self.runs[run_id].status == "running":
                return False
            del self.runs[run_id]
            return True
