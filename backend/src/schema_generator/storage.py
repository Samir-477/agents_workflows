from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_runtime.postgres import PostgresRepository
from schema_generator.models import (
    ParsedSchemaBrief,
    SchemaGenerationCreate,
    SchemaGenerationRecord,
    SchemaGenerationResult,
    SchemaGenerationStage,
    SchemaGenerationStatus,
    utc_now,
)


class SchemaGenerationNotFoundError(LookupError):
    pass


class SchemaGenerationRepository(PostgresRepository):
    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS schema_generations (
                    id TEXT PRIMARY KEY, prompt TEXT NOT NULL, status TEXT NOT NULL,
                    stage TEXT NOT NULL, progress INTEGER NOT NULL, parsed_brief_json TEXT,
                    result_json TEXT, warnings_json TEXT NOT NULL, error TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_schema_generations_created_at ON schema_generations (created_at DESC)")
            connection.execute("ALTER TABLE schema_generations ENABLE ROW LEVEL SECURITY")

    def create_generation(self, request: SchemaGenerationCreate) -> SchemaGenerationRecord:
        run = SchemaGenerationRecord(prompt=request.prompt)
        with self.connect() as connection:
            self._execute(connection, """
                INSERT INTO schema_generations (id,prompt,status,stage,progress,parsed_brief_json,result_json,warnings_json,error,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (run.id, run.prompt, run.status.value, run.stage.value, 0, None, None, "[]", None, run.created_at.isoformat(), run.updated_at.isoformat()))
        return run

    def get_generation(self, generation_id: str) -> SchemaGenerationRecord:
        with self.connect() as connection:
            row = self._execute(connection, "SELECT * FROM schema_generations WHERE id = ?", (generation_id,)).fetchone()
        if row is None:
            raise SchemaGenerationNotFoundError(generation_id)
        return self._from_row(row)

    def list_generations(self, limit: int = 20, offset: int = 0, query: str | None = None) -> list[SchemaGenerationRecord]:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(connection, "SELECT * FROM schema_generations WHERE prompt LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (pattern, limit, offset)).fetchall()
            else:
                rows = self._execute(connection, "SELECT * FROM schema_generations ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [self._from_row(row) for row in rows]

    def count_generations(self, query: str | None = None) -> int:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            row = self._execute(connection, "SELECT COUNT(*) AS total FROM schema_generations WHERE prompt LIKE ?" if pattern else "SELECT COUNT(*) AS total FROM schema_generations", (pattern,) if pattern else None).fetchone()
        return int(row["total"])

    def delete_generation(self, generation_id: str) -> None:
        self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM schema_generations WHERE id = ?", (generation_id,))

    def update_generation(self, generation_id: str, *, status=None, stage=None, progress=None, warnings=None, error=None) -> SchemaGenerationRecord:
        current = self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(connection, "UPDATE schema_generations SET status=?,stage=?,progress=?,warnings_json=?,error=?,updated_at=? WHERE id=?", (
                (status or current.status).value, (stage or current.stage).value,
                current.progress if progress is None else progress,
                json.dumps(current.warnings if warnings is None else warnings), error,
                utc_now().isoformat(), generation_id,
            ))
        return self.get_generation(generation_id)

    def claim_generation(self, generation_id: str) -> SchemaGenerationRecord | None:
        with self.connect() as connection:
            updated = self._execute(connection, "UPDATE schema_generations SET status=?,stage=?,progress=?,updated_at=? WHERE id=? AND status=?", (
                SchemaGenerationStatus.RUNNING.value, SchemaGenerationStage.INTERPRETING.value, 2,
                utc_now().isoformat(), generation_id, SchemaGenerationStatus.QUEUED.value,
            ))
            if updated.rowcount != 1:
                return None
        return self.get_generation(generation_id)

    def save_brief(self, generation_id: str, brief: ParsedSchemaBrief) -> None:
        with self.connect() as connection:
            self._execute(connection, "UPDATE schema_generations SET parsed_brief_json=?,warnings_json=?,updated_at=? WHERE id=?", (
                brief.model_dump_json(), json.dumps(brief.mismatches), utc_now().isoformat(), generation_id,
            ))

    def save_result(self, result: SchemaGenerationResult) -> None:
        with self.connect() as connection:
            self._execute(connection, "UPDATE schema_generations SET result_json=?,status=?,stage=?,progress=100,warnings_json=?,error=NULL,updated_at=? WHERE id=?", (
                result.model_dump_json(), SchemaGenerationStatus.COMPLETE.value,
                SchemaGenerationStage.COMPLETE.value, json.dumps(result.warnings), utc_now().isoformat(), result.generation_id,
            ))

    def retry_generation(self, generation_id: str) -> SchemaGenerationRecord:
        current = self.get_generation(generation_id)
        if current.status not in {SchemaGenerationStatus.COMPLETE, SchemaGenerationStatus.FAILED}:
            raise ValueError("Only failed or completed generations can be queued again")
        with self.connect() as connection:
            self._execute(connection, "UPDATE schema_generations SET status=?,stage=?,progress=0,parsed_brief_json=NULL,result_json=NULL,warnings_json='[]',error=NULL,updated_at=? WHERE id=?", (
                SchemaGenerationStatus.QUEUED.value, SchemaGenerationStage.QUEUED.value, utc_now().isoformat(), generation_id,
            ))
        return self.get_generation(generation_id)

    @staticmethod
    def _from_row(row: Any) -> SchemaGenerationRecord:
        return SchemaGenerationRecord(
            id=row["id"], prompt=row["prompt"], status=row["status"], stage=row["stage"], progress=row["progress"],
            parsed_brief=ParsedSchemaBrief.model_validate_json(row["parsed_brief_json"]) if row["parsed_brief_json"] else None,
            result=SchemaGenerationResult.model_validate_json(row["result_json"]) if row["result_json"] else None,
            warnings=json.loads(row["warnings_json"]), error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class MemorySchemaGenerationRepository:
    """In-process repository used by isolated API tests."""

    def __init__(self) -> None:
        self.runs: dict[str, SchemaGenerationRecord] = {}

    def initialize(self) -> None:
        return None

    def create_generation(self, request: SchemaGenerationCreate) -> SchemaGenerationRecord:
        run = SchemaGenerationRecord(prompt=request.prompt)
        self.runs[run.id] = run
        return run.model_copy(deep=True)

    def get_generation(self, generation_id: str) -> SchemaGenerationRecord:
        try:
            return self.runs[generation_id].model_copy(deep=True)
        except KeyError as exc:
            raise SchemaGenerationNotFoundError(generation_id) from exc

    def list_generations(self, limit: int = 20, offset: int = 0, query: str | None = None) -> list[SchemaGenerationRecord]:
        runs = sorted(self.runs.values(), key=lambda item: item.created_at, reverse=True)
        if query and query.strip():
            needle = query.strip().casefold()
            runs = [item for item in runs if needle in item.prompt.casefold()]
        return [item.model_copy(deep=True) for item in runs[offset:offset + limit]]

    def count_generations(self, query: str | None = None) -> int:
        if not query or not query.strip():
            return len(self.runs)
        needle = query.strip().casefold()
        return sum(needle in item.prompt.casefold() for item in self.runs.values())

    def delete_generation(self, generation_id: str) -> None:
        self.get_generation(generation_id)
        self.runs.pop(generation_id)

    def update_generation(self, generation_id: str, *, status=None, stage=None, progress=None, warnings=None, error=None) -> SchemaGenerationRecord:
        current = self.get_generation(generation_id)
        updated = current.model_copy(update={
            "status": status or current.status,
            "stage": stage or current.stage,
            "progress": current.progress if progress is None else progress,
            "warnings": current.warnings if warnings is None else warnings,
            "error": error,
            "updated_at": utc_now(),
        }, deep=True)
        self.runs[generation_id] = updated
        return updated.model_copy(deep=True)

    def claim_generation(self, generation_id: str) -> SchemaGenerationRecord | None:
        current = self.get_generation(generation_id)
        if current.status != SchemaGenerationStatus.QUEUED:
            return None
        return self.update_generation(generation_id, status=SchemaGenerationStatus.RUNNING, stage=SchemaGenerationStage.INTERPRETING, progress=2)

    def save_brief(self, generation_id: str, brief: ParsedSchemaBrief) -> None:
        current = self.get_generation(generation_id)
        self.runs[generation_id] = current.model_copy(update={"parsed_brief": brief, "warnings": brief.mismatches, "updated_at": utc_now()}, deep=True)

    def save_result(self, result: SchemaGenerationResult) -> None:
        current = self.get_generation(result.generation_id)
        self.runs[result.generation_id] = current.model_copy(update={"result": result, "status": SchemaGenerationStatus.COMPLETE, "stage": SchemaGenerationStage.COMPLETE, "progress": 100, "warnings": result.warnings, "error": None, "updated_at": utc_now()}, deep=True)

    def retry_generation(self, generation_id: str) -> SchemaGenerationRecord:
        current = self.get_generation(generation_id)
        if current.status not in {SchemaGenerationStatus.COMPLETE, SchemaGenerationStatus.FAILED}:
            raise ValueError("Only failed or completed generations can be queued again")
        retried = current.model_copy(update={"status": SchemaGenerationStatus.QUEUED, "stage": SchemaGenerationStage.QUEUED, "progress": 0, "parsed_brief": None, "result": None, "warnings": [], "error": None, "updated_at": utc_now()}, deep=True)
        self.runs[generation_id] = retried
        return retried.model_copy(deep=True)
