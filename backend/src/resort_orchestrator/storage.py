from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_runtime.postgres import PostgresRepository
from resort_orchestrator.models import (
    AgentOutcome,
    OrchestratorCreate,
    OrchestratorRecord,
    OrchestratorStatus,
    utc_now,
)


class OrchestratorNotFoundError(LookupError):
    pass


def _outcomes_to_json(outcomes: dict[str, AgentOutcome]) -> str:
    return json.dumps({key: value.model_dump(mode="json") for key, value in outcomes.items()})


def _outcomes_from_json(raw: str) -> dict[str, AgentOutcome]:
    return {key: AgentOutcome.model_validate(value) for key, value in json.loads(raw).items()}


class OrchestratorRepository(PostgresRepository):
    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS resort_orchestrator_runs (
                    id TEXT PRIMARY KEY, page_url TEXT NOT NULL,
                    audience TEXT, business_goal TEXT, derived_keyword TEXT,
                    status TEXT NOT NULL, stage TEXT NOT NULL, progress INTEGER NOT NULL,
                    outcomes_json TEXT NOT NULL, report_json TEXT, warnings_json TEXT NOT NULL,
                    error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_resort_orchestrator_created_at "
                "ON resort_orchestrator_runs (created_at DESC)"
            )
            connection.execute("ALTER TABLE resort_orchestrator_runs ENABLE ROW LEVEL SECURITY")

    def create(self, request: OrchestratorCreate) -> OrchestratorRecord:
        run = OrchestratorRecord(
            page_url=request.page_url, audience=request.audience, business_goal=request.business_goal,
        )
        with self.connect() as connection:
            self._execute(connection, """INSERT INTO resort_orchestrator_runs
                (id,page_url,audience,business_goal,derived_keyword,status,stage,progress,
                 outcomes_json,report_json,warnings_json,error,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                run.id, run.page_url, run.audience, run.business_goal, None,
                run.status.value, run.stage, 0, "{}", None, "[]", None,
                run.created_at.isoformat(), run.updated_at.isoformat(),
            ))
        return run

    def get(self, run_id: str) -> OrchestratorRecord:
        with self.connect() as connection:
            row = self._execute(connection, "SELECT * FROM resort_orchestrator_runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise OrchestratorNotFoundError(run_id)
        return self._from_row(row)

    def list(self, limit: int = 20, offset: int = 0, query: str | None = None) -> list[OrchestratorRecord]:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(
                    connection,
                    "SELECT * FROM resort_orchestrator_runs WHERE page_url LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (pattern, limit, offset),
                ).fetchall()
            else:
                rows = self._execute(
                    connection,
                    "SELECT * FROM resort_orchestrator_runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self, query: str | None = None) -> int:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            sql = (
                "SELECT COUNT(*) AS total FROM resort_orchestrator_runs WHERE page_url LIKE ?"
                if pattern else "SELECT COUNT(*) AS total FROM resort_orchestrator_runs"
            )
            row = self._execute(connection, sql, (pattern,) if pattern else None).fetchone()
        return int(row["total"])

    def delete(self, run_id: str) -> None:
        self.get(run_id)
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM resort_orchestrator_runs WHERE id = ?", (run_id,))

    def update(
        self, run_id: str, *, status=None, stage=None, progress=None, derived_keyword=None,
        outcomes=None, report=None, warnings=None, error=None,
    ) -> OrchestratorRecord:
        current = self.get(run_id)
        next_status = status or current.status
        next_outcomes = current.outcomes if outcomes is None else outcomes
        with self.connect() as connection:
            self._execute(connection, """UPDATE resort_orchestrator_runs SET
                status=?,stage=?,progress=?,derived_keyword=?,outcomes_json=?,report_json=?,
                warnings_json=?,error=?,updated_at=? WHERE id=?""", (
                next_status.value if hasattr(next_status, "value") else next_status,
                stage or current.stage,
                current.progress if progress is None else progress,
                current.derived_keyword if derived_keyword is None else derived_keyword,
                _outcomes_to_json(next_outcomes),
                json.dumps(report) if report is not None else (
                    json.dumps(current.report) if current.report is not None else None
                ),
                json.dumps(current.warnings if warnings is None else warnings),
                error, utc_now().isoformat(), run_id,
            ))
        return self.get(run_id)

    def claim(self, run_id: str) -> OrchestratorRecord | None:
        with self.connect() as connection:
            changed = self._execute(connection, """UPDATE resort_orchestrator_runs SET
                status=?,stage=?,progress=2,updated_at=? WHERE id=? AND status=?""", (
                OrchestratorStatus.RUNNING.value, "reading_page", utc_now().isoformat(),
                run_id, OrchestratorStatus.QUEUED.value,
            ))
            if changed.rowcount != 1:
                return None
        return self.get(run_id)

    def retry(self, run_id: str) -> OrchestratorRecord:
        current = self.get(run_id)
        if current.status not in {OrchestratorStatus.COMPLETE, OrchestratorStatus.FAILED}:
            raise ValueError("Only a completed or failed run can be queued again")
        with self.connect() as connection:
            self._execute(connection, """UPDATE resort_orchestrator_runs SET
                status=?,stage=?,progress=0,outcomes_json='{}',report_json=NULL,
                warnings_json='[]',error=NULL,updated_at=? WHERE id=?""", (
                OrchestratorStatus.QUEUED.value, "queued", utc_now().isoformat(), run_id,
            ))
        return self.get(run_id)

    @staticmethod
    def _from_row(row: Any) -> OrchestratorRecord:
        return OrchestratorRecord(
            id=row["id"], page_url=row["page_url"], audience=row["audience"],
            business_goal=row["business_goal"], derived_keyword=row["derived_keyword"],
            status=row["status"], stage=row["stage"], progress=row["progress"],
            outcomes=_outcomes_from_json(row["outcomes_json"]),
            report=json.loads(row["report_json"]) if row["report_json"] else None,
            warnings=json.loads(row["warnings_json"]), error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class MemoryOrchestratorRepository:
    def __init__(self) -> None:
        self.runs: dict[str, OrchestratorRecord] = {}

    def initialize(self) -> None:
        return None

    def create(self, request: OrchestratorCreate) -> OrchestratorRecord:
        run = OrchestratorRecord(
            page_url=request.page_url, audience=request.audience, business_goal=request.business_goal,
        )
        self.runs[run.id] = run
        return run.model_copy(deep=True)

    def get(self, run_id: str) -> OrchestratorRecord:
        if run_id not in self.runs:
            raise OrchestratorNotFoundError(run_id)
        return self.runs[run_id].model_copy(deep=True)

    def list(self, limit: int = 20, offset: int = 0, query: str | None = None) -> list[OrchestratorRecord]:
        runs = sorted(self.runs.values(), key=lambda item: item.created_at, reverse=True)
        if query and query.strip():
            runs = [item for item in runs if query.strip().casefold() in item.page_url.casefold()]
        return [item.model_copy(deep=True) for item in runs[offset:offset + limit]]

    def count(self, query: str | None = None) -> int:
        return len(self.list(10_000, 0, query))

    def delete(self, run_id: str) -> None:
        self.get(run_id)
        self.runs.pop(run_id)

    def update(
        self, run_id: str, *, status=None, stage=None, progress=None, derived_keyword=None,
        outcomes=None, report=None, warnings=None, error=None,
    ) -> OrchestratorRecord:
        current = self.get(run_id)
        data = {
            "status": status or current.status,
            "stage": stage or current.stage,
            "progress": current.progress if progress is None else progress,
            "derived_keyword": current.derived_keyword if derived_keyword is None else derived_keyword,
            "outcomes": current.outcomes if outcomes is None else outcomes,
            "report": current.report if report is None else report,
            "warnings": current.warnings if warnings is None else warnings,
            "error": error,
            "updated_at": utc_now(),
        }
        self.runs[run_id] = current.model_copy(update=data, deep=True)
        return self.get(run_id)

    def claim(self, run_id: str) -> OrchestratorRecord | None:
        if self.get(run_id).status != OrchestratorStatus.QUEUED:
            return None
        return self.update(run_id, status=OrchestratorStatus.RUNNING, stage="reading_page", progress=2)

    def retry(self, run_id: str) -> OrchestratorRecord:
        current = self.get(run_id)
        if current.status not in {OrchestratorStatus.COMPLETE, OrchestratorStatus.FAILED}:
            raise ValueError("Only a completed or failed run can be queued again")
        self.runs[run_id] = current.model_copy(update={
            "status": OrchestratorStatus.QUEUED, "stage": "queued", "progress": 0,
            "outcomes": {}, "report": None, "warnings": [], "error": None, "updated_at": utc_now(),
        }, deep=True)
        return self.get(run_id)
