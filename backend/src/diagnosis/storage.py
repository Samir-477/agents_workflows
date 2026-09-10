from __future__ import annotations

import json
from threading import RLock
from agent_runtime.postgres import PostgresRepository
from diagnosis.models import Diagnosis, DiagnosisInput, now


class DiagnosisRepository(PostgresRepository):
    def initialize(self):
        with self.connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS website_diagnoses (id TEXT PRIMARY KEY, document JSONB NOT NULL, created_at TEXT NOT NULL)")

    def create(self, request: DiagnosisInput):
        run = Diagnosis(request=request)
        with self.connect() as c:
            self._execute(c, "INSERT INTO website_diagnoses VALUES (?,?::jsonb,?)", (run.id, run.model_dump_json(), run.created_at))
        return run

    def get(self, id):
        with self.connect() as c:
            row = self._execute(c, "SELECT document FROM website_diagnoses WHERE id=?", (id,)).fetchone()
        if not row:
            raise LookupError("Diagnosis not found")
        return Diagnosis.model_validate(row["document"])

    def list(self, limit=30):
        with self.connect() as c:
            rows = self._execute(c, "SELECT document FROM website_diagnoses ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Diagnosis.model_validate(r["document"]) for r in rows]

    def pending(self):
        with self.connect() as c:
            rows = c.execute("SELECT id FROM website_diagnoses WHERE document->>'status' IN ('queued','running') ORDER BY created_at LIMIT 50").fetchall()
        return [r["id"] for r in rows]

    def mutate(self, id, change):
        # Serialize state transitions; lease tokens fence stale workers.
        with self.connect() as c:
            row = self._execute(c, "SELECT document FROM website_diagnoses WHERE id=? FOR UPDATE", (id,)).fetchone()
            if not row:
                raise LookupError("Diagnosis not found")
            run = Diagnosis.model_validate(row["document"])
            result = change(run)
            run.updated_at = now()
            self._execute(c, "UPDATE website_diagnoses SET document=?::jsonb WHERE id=?", (run.model_dump_json(), id))
        return result


class MemoryDiagnosisRepository:
    def __init__(self):
        self.runs = {}
        self.lock = RLock()

    def initialize(self):
        pass

    def create(self, request):
        run = Diagnosis(request=request)
        self.runs[run.id] = run
        return self.get(run.id)

    def get(self, id):
        if id not in self.runs:
            raise LookupError("Diagnosis not found")
        return self.runs[id].model_copy(deep=True)

    def list(self, limit=30):
        return [r.model_copy(deep=True) for r in sorted(self.runs.values(), key=lambda r: r.created_at, reverse=True)[:limit]]

    def pending(self):
        return [r.id for r in self.runs.values() if r.status in {"queued", "running"}]

    def mutate(self, id, change):
        with self.lock:
            run = self.get(id)
            result = change(run)
            run.updated_at = now()
            self.runs[id] = run
            return result
