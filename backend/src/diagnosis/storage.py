from __future__ import annotations

import json
from threading import RLock
from agent_runtime.postgres import PostgresRepository
from diagnosis.models import Diagnosis, DiagnosisInput, Task, now


def new_diagnosis(request: DiagnosisInput) -> Diagnosis:
    keys = ["capture", *request.selected_agents]
    if request.run_mode == "diagnosis":
        keys.append("report")
    tasks = {key: Task() for key in keys}
    return Diagnosis(request=request, tasks=tasks)


class DiagnosisRepository(PostgresRepository):
    def initialize(self):
        with self.connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS website_diagnoses (id TEXT PRIMARY KEY, document JSONB NOT NULL, created_at TEXT NOT NULL)")

    def create(self, request: DiagnosisInput):
        run = new_diagnosis(request)
        with self.connect() as c:
            self._execute(c, "INSERT INTO website_diagnoses VALUES (?,?::jsonb,?)", (run.id, run.model_dump_json(), run.created_at))
        return run

    def get(self, id):
        with self.connect() as c:
            row = self._execute(c, "SELECT document FROM website_diagnoses WHERE id=?", (id,)).fetchone()
        if not row:
            raise LookupError("Diagnosis not found")
        return Diagnosis.model_validate(row["document"])

    def get_for_display(self, id):
        """Load the report UI payload without transferring duplicate raw task evidence."""
        statement = """
            SELECT jsonb_set(
                document,
                '{tasks}',
                COALESCE((
                    SELECT jsonb_object_agg(
                        task.key,
                        (task.value - 'token' - 'result') || jsonb_build_object(
                            'result',
                            CASE
                                WHEN task.key = 'report' THEN '{}'::jsonb
                                WHEN jsonb_exists(task.value->'result', 'reason')
                                    THEN jsonb_build_object('reason', task.value->'result'->'reason')
                                ELSE '{}'::jsonb
                            END
                        )
                    )
                    FROM jsonb_each(document->'tasks') AS task
                ), '{}'::jsonb),
                true
            ) AS document
            FROM website_diagnoses
            WHERE id=?
        """
        with self.connect() as c:
            row = self._execute(c, statement, (id,)).fetchone()
        if not row:
            raise LookupError("Diagnosis not found")
        return Diagnosis.model_validate(row["document"])

    def list(self, limit=30):
        with self.connect() as c:
            rows = self._execute(c, "SELECT document FROM website_diagnoses ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Diagnosis.model_validate(r["document"]) for r in rows]

    def history(self, subject, limit=10, offset=0):
        """Return only the fields used by the session list and filter in SQL."""
        admin = subject in {"admin", "local-demo-admin"}
        ownership = """
            (document->>'owner_subject' = ? OR document->>'owner_subject' IS NULL OR document->>'owner_subject' = 'local-demo-admin')
        """ if admin else "document->>'owner_subject' = ?"
        statement = f"""
            SELECT
                id,
                document->'request'->>'page_url' AS url,
                document->>'status' AS status,
                created_at,
                COALESCE(document->'request'->>'run_mode', 'diagnosis') AS run_mode,
                COALESCE(document->'request'->'selected_agents', '[]'::jsonb) AS selected_agents,
                CASE
                    WHEN jsonb_typeof(document->'report'->'findings') = 'array'
                        THEN jsonb_array_length(document->'report'->'findings')
                    ELSE 0
                END AS finding_count,
                COUNT(*) OVER() AS total_count
            FROM website_diagnoses
            WHERE {ownership}
            ORDER BY created_at DESC
            LIMIT ?
            OFFSET ?
        """
        with self.connect() as c:
            rows = self._execute(c, statement, (subject, limit, offset)).fetchall()
        total = int(rows[0]["total_count"]) if rows else 0
        items = []
        for row in rows:
            item = dict(row)
            item.pop("total_count", None)
            items.append(item)
        return {"items": items, "total": total}

    def delete(self, id):
        self.get(id)
        with self.connect() as c:
            self._execute(c, "DELETE FROM website_diagnoses WHERE id=?", (id,))

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
        run = new_diagnosis(request)
        self.runs[run.id] = run
        return self.get(run.id)

    def get(self, id):
        if id not in self.runs:
            raise LookupError("Diagnosis not found")
        return self.runs[id].model_copy(deep=True)

    def get_for_display(self, id):
        return self.get(id)

    def list(self, limit=30):
        return [r.model_copy(deep=True) for r in sorted(self.runs.values(), key=lambda r: r.created_at, reverse=True)[:limit]]

    def history(self, subject, limit=10, offset=0):
        admin = subject in {"admin", "local-demo-admin"}
        visible = [
            run for run in self.list(len(self.runs))
            if run.owner_subject == subject or (admin and run.owner_subject in {None, "local-demo-admin"})
        ]
        items = [{
            "id": run.id,
            "url": str(run.request.page_url),
            "status": run.status,
            "created_at": run.created_at,
            "run_mode": run.request.run_mode,
            "selected_agents": run.request.selected_agents,
            "finding_count": len((run.report or {}).get("findings", [])),
        } for run in visible[offset:offset + limit]]
        return {"items": items, "total": len(visible)}

    def delete(self, id):
        self.get(id)
        self.runs.pop(id)

    def pending(self):
        return [r.id for r in self.runs.values() if r.status in {"queued", "running"}]

    def mutate(self, id, change):
        with self.lock:
            run = self.get(id)
            result = change(run)
            run.updated_at = now()
            self.runs[id] = run
            return result
