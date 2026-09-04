from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_runtime.postgres import PostgresRepository
from keyword_cluster.models import (
    KeywordClusterCreate,
    KeywordClusterRecord,
    KeywordClusterResult,
    KeywordClusterStage,
    KeywordClusterStatus,
    KeywordItem,
    utc_now,
)


class KeywordClusterNotFoundError(LookupError):
    pass


class KeywordClusterRepository(PostgresRepository):
    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS keyword_cluster_generations (
                    id TEXT PRIMARY KEY, raw_keywords TEXT NOT NULL, status TEXT NOT NULL,
                    stage TEXT NOT NULL, progress INTEGER NOT NULL, parsed_keywords_json TEXT NOT NULL,
                    result_json TEXT, warnings_json TEXT NOT NULL, error TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_keyword_cluster_created_at ON keyword_cluster_generations (created_at DESC)")
            connection.execute("ALTER TABLE keyword_cluster_generations ENABLE ROW LEVEL SECURITY")

    def create_generation(self, request: KeywordClusterCreate) -> KeywordClusterRecord:
        run = KeywordClusterRecord(raw_keywords=request.keywords)
        with self.connect() as connection:
            self._execute(connection, """
                INSERT INTO keyword_cluster_generations
                (id,raw_keywords,status,stage,progress,parsed_keywords_json,result_json,warnings_json,error,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (run.id, run.raw_keywords, run.status.value, run.stage.value, 0, "[]", None, "[]", None, run.created_at.isoformat(), run.updated_at.isoformat()))
        return run

    def get_generation(self, generation_id: str) -> KeywordClusterRecord:
        with self.connect() as connection:
            row = self._execute(connection, "SELECT * FROM keyword_cluster_generations WHERE id = ?", (generation_id,)).fetchone()
        if row is None:
            raise KeywordClusterNotFoundError(generation_id)
        return self._from_row(row)

    def list_generations(self, limit: int = 20, offset: int = 0, query: str | None = None) -> list[KeywordClusterRecord]:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(connection, "SELECT * FROM keyword_cluster_generations WHERE raw_keywords LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (pattern, limit, offset)).fetchall()
            else:
                rows = self._execute(connection, "SELECT * FROM keyword_cluster_generations ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [self._from_row(row) for row in rows]

    def count_generations(self, query: str | None = None) -> int:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            row = self._execute(connection, "SELECT COUNT(*) AS total FROM keyword_cluster_generations WHERE raw_keywords LIKE ?" if pattern else "SELECT COUNT(*) AS total FROM keyword_cluster_generations", (pattern,) if pattern else None).fetchone()
        return int(row["total"])

    def delete_generation(self, generation_id: str) -> None:
        self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM keyword_cluster_generations WHERE id = ?", (generation_id,))

    def update_generation(self, generation_id: str, *, status=None, stage=None, progress=None, warnings=None, error=None) -> KeywordClusterRecord:
        current = self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(connection, "UPDATE keyword_cluster_generations SET status=?,stage=?,progress=?,warnings_json=?,error=?,updated_at=? WHERE id=?", (
                (status or current.status).value, (stage or current.stage).value,
                current.progress if progress is None else progress,
                json.dumps(current.warnings if warnings is None else warnings), error,
                utc_now().isoformat(), generation_id,
            ))
        return self.get_generation(generation_id)

    def claim_generation(self, generation_id: str) -> KeywordClusterRecord | None:
        with self.connect() as connection:
            updated = self._execute(connection, "UPDATE keyword_cluster_generations SET status=?,stage=?,progress=?,updated_at=? WHERE id=? AND status=?", (
                KeywordClusterStatus.RUNNING.value, KeywordClusterStage.PARSING.value, 2,
                utc_now().isoformat(), generation_id, KeywordClusterStatus.QUEUED.value,
            ))
            if updated.rowcount != 1:
                return None
        return self.get_generation(generation_id)

    def save_keywords(self, generation_id: str, keywords: list[KeywordItem], warnings: list[str]) -> None:
        with self.connect() as connection:
            self._execute(connection, "UPDATE keyword_cluster_generations SET parsed_keywords_json=?,warnings_json=?,updated_at=? WHERE id=?", (
                json.dumps([item.model_dump(mode="json") for item in keywords]), json.dumps(warnings), utc_now().isoformat(), generation_id,
            ))

    def save_result(self, result: KeywordClusterResult) -> None:
        with self.connect() as connection:
            self._execute(connection, "UPDATE keyword_cluster_generations SET result_json=?,status=?,stage=?,progress=100,warnings_json=?,error=NULL,updated_at=? WHERE id=?", (
                result.model_dump_json(), KeywordClusterStatus.COMPLETE.value, KeywordClusterStage.COMPLETE.value,
                json.dumps(result.warnings), utc_now().isoformat(), result.generation_id,
            ))

    def retry_generation(self, generation_id: str) -> KeywordClusterRecord:
        current = self.get_generation(generation_id)
        if current.status not in {KeywordClusterStatus.COMPLETE, KeywordClusterStatus.FAILED}:
            raise ValueError("Only failed or completed generations can be queued again")
        with self.connect() as connection:
            self._execute(connection, "UPDATE keyword_cluster_generations SET status=?,stage=?,progress=0,parsed_keywords_json='[]',result_json=NULL,warnings_json='[]',error=NULL,updated_at=? WHERE id=?", (
                KeywordClusterStatus.QUEUED.value, KeywordClusterStage.QUEUED.value, utc_now().isoformat(), generation_id,
            ))
        return self.get_generation(generation_id)

    @staticmethod
    def _from_row(row: Any) -> KeywordClusterRecord:
        return KeywordClusterRecord(
            id=row["id"], raw_keywords=row["raw_keywords"], status=row["status"], stage=row["stage"], progress=row["progress"],
            parsed_keywords=[KeywordItem.model_validate(item) for item in json.loads(row["parsed_keywords_json"])],
            result=KeywordClusterResult.model_validate_json(row["result_json"]) if row["result_json"] else None,
            warnings=json.loads(row["warnings_json"]), error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class MemoryKeywordClusterRepository:
    def __init__(self) -> None:
        self.runs: dict[str, KeywordClusterRecord] = {}

    def initialize(self) -> None:
        return None

    def create_generation(self, request: KeywordClusterCreate) -> KeywordClusterRecord:
        run = KeywordClusterRecord(raw_keywords=request.keywords)
        self.runs[run.id] = run
        return run.model_copy(deep=True)

    def get_generation(self, generation_id: str) -> KeywordClusterRecord:
        try:
            return self.runs[generation_id].model_copy(deep=True)
        except KeyError as exc:
            raise KeywordClusterNotFoundError(generation_id) from exc

    def list_generations(self, limit: int = 20, offset: int = 0, query: str | None = None) -> list[KeywordClusterRecord]:
        runs = sorted(self.runs.values(), key=lambda item: item.created_at, reverse=True)
        if query and query.strip():
            needle = query.strip().casefold()
            runs = [item for item in runs if needle in item.raw_keywords.casefold()]
        return [item.model_copy(deep=True) for item in runs[offset:offset + limit]]

    def count_generations(self, query: str | None = None) -> int:
        if not query or not query.strip():
            return len(self.runs)
        needle = query.strip().casefold()
        return sum(needle in item.raw_keywords.casefold() for item in self.runs.values())

    def delete_generation(self, generation_id: str) -> None:
        self.get_generation(generation_id)
        self.runs.pop(generation_id)

    def update_generation(self, generation_id: str, *, status=None, stage=None, progress=None, warnings=None, error=None) -> KeywordClusterRecord:
        current = self.get_generation(generation_id)
        updated = current.model_copy(update={
            "status": status or current.status, "stage": stage or current.stage,
            "progress": current.progress if progress is None else progress,
            "warnings": current.warnings if warnings is None else warnings,
            "error": error, "updated_at": utc_now(),
        }, deep=True)
        self.runs[generation_id] = updated
        return updated.model_copy(deep=True)

    def claim_generation(self, generation_id: str) -> KeywordClusterRecord | None:
        current = self.get_generation(generation_id)
        if current.status != KeywordClusterStatus.QUEUED:
            return None
        return self.update_generation(generation_id, status=KeywordClusterStatus.RUNNING, stage=KeywordClusterStage.PARSING, progress=2)

    def save_keywords(self, generation_id: str, keywords: list[KeywordItem], warnings: list[str]) -> None:
        current = self.get_generation(generation_id)
        self.runs[generation_id] = current.model_copy(update={"parsed_keywords": keywords, "warnings": warnings, "updated_at": utc_now()}, deep=True)

    def save_result(self, result: KeywordClusterResult) -> None:
        current = self.get_generation(result.generation_id)
        self.runs[result.generation_id] = current.model_copy(update={
            "result": result, "status": KeywordClusterStatus.COMPLETE, "stage": KeywordClusterStage.COMPLETE,
            "progress": 100, "warnings": result.warnings, "error": None, "updated_at": utc_now(),
        }, deep=True)

    def retry_generation(self, generation_id: str) -> KeywordClusterRecord:
        current = self.get_generation(generation_id)
        if current.status not in {KeywordClusterStatus.COMPLETE, KeywordClusterStatus.FAILED}:
            raise ValueError("Only failed or completed generations can be queued again")
        retried = current.model_copy(update={
            "status": KeywordClusterStatus.QUEUED, "stage": KeywordClusterStage.QUEUED,
            "progress": 0, "parsed_keywords": [], "result": None, "warnings": [], "error": None, "updated_at": utc_now(),
        }, deep=True)
        self.runs[generation_id] = retried
        return retried.model_copy(deep=True)
