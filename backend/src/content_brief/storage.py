from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_runtime.postgres import PostgresRepository
from content_brief.models import (
    ContentBriefCreate,
    ContentBriefDraft,
    ContentBriefRecord,
    ContentBriefResult,
    ContentBriefStage,
    ContentBriefStatus,
    utc_now,
)


class ContentBriefNotFoundError(LookupError):
    pass


class ContentBriefRepository(PostgresRepository):
    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS content_brief_generations (
                    id TEXT PRIMARY KEY, request_json TEXT NOT NULL,
                    target_keyword TEXT NOT NULL, audience TEXT NOT NULL,
                    status TEXT NOT NULL, stage TEXT NOT NULL, progress INTEGER NOT NULL,
                    draft_json TEXT, result_json TEXT, warnings_json TEXT NOT NULL,
                    error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_content_briefs_created_at ON content_brief_generations (created_at DESC)")
            connection.execute("ALTER TABLE content_brief_generations ENABLE ROW LEVEL SECURITY")

    def create_generation(self, request: ContentBriefCreate) -> ContentBriefRecord:
        run = ContentBriefRecord(request=request)
        with self.connect() as connection:
            self._execute(connection, """
                INSERT INTO content_brief_generations
                (id,request_json,target_keyword,audience,status,stage,progress,draft_json,result_json,warnings_json,error,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (run.id, request.model_dump_json(), request.target_keyword, request.audience,
                  run.status.value, run.stage.value, 0, None, None, "[]", None,
                  run.created_at.isoformat(), run.updated_at.isoformat()))
        return run

    def get_generation(self, generation_id: str) -> ContentBriefRecord:
        with self.connect() as connection:
            row = self._execute(connection, "SELECT * FROM content_brief_generations WHERE id = ?", (generation_id,)).fetchone()
        if row is None:
            raise ContentBriefNotFoundError(generation_id)
        return self._from_row(row)

    def list_generations(self, limit: int = 20, offset: int = 0, query: str | None = None) -> list[ContentBriefRecord]:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(connection, """
                    SELECT * FROM content_brief_generations
                    WHERE target_keyword LIKE ? OR audience LIKE ? OR request_json LIKE ?
                    ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (pattern, pattern, pattern, limit, offset)).fetchall()
            else:
                rows = self._execute(connection, "SELECT * FROM content_brief_generations ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [self._from_row(row) for row in rows]

    def count_generations(self, query: str | None = None) -> int:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                row = self._execute(connection, "SELECT COUNT(*) AS total FROM content_brief_generations WHERE target_keyword LIKE ? OR audience LIKE ? OR request_json LIKE ?", (pattern, pattern, pattern)).fetchone()
            else:
                row = self._execute(connection, "SELECT COUNT(*) AS total FROM content_brief_generations").fetchone()
        return int(row["total"])

    def delete_generation(self, generation_id: str) -> None:
        self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(connection, "DELETE FROM content_brief_generations WHERE id = ?", (generation_id,))

    def update_generation(self, generation_id: str, *, status=None, stage=None, progress=None, warnings=None, error=None) -> ContentBriefRecord:
        current = self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(connection, """UPDATE content_brief_generations
                SET status=?,stage=?,progress=?,warnings_json=?,error=?,updated_at=? WHERE id=?""", (
                (status or current.status).value, (stage or current.stage).value,
                current.progress if progress is None else progress,
                json.dumps(current.warnings if warnings is None else warnings), error,
                utc_now().isoformat(), generation_id,
            ))
        return self.get_generation(generation_id)

    def claim_generation(self, generation_id: str) -> ContentBriefRecord | None:
        with self.connect() as connection:
            updated = self._execute(connection, """UPDATE content_brief_generations
                SET status=?,stage=?,progress=?,updated_at=? WHERE id=? AND status=?""", (
                ContentBriefStatus.RUNNING.value, ContentBriefStage.NORMALIZING.value, 3,
                utc_now().isoformat(), generation_id, ContentBriefStatus.QUEUED.value,
            ))
            if updated.rowcount != 1:
                return None
        return self.get_generation(generation_id)

    def save_draft(self, generation_id: str, draft: ContentBriefDraft) -> None:
        with self.connect() as connection:
            self._execute(connection, "UPDATE content_brief_generations SET draft_json=?,updated_at=? WHERE id=?", (draft.model_dump_json(), utc_now().isoformat(), generation_id))

    def save_result(self, result: ContentBriefResult) -> None:
        with self.connect() as connection:
            self._execute(connection, """UPDATE content_brief_generations
                SET result_json=?,status=?,stage=?,progress=100,warnings_json=?,error=NULL,updated_at=? WHERE id=?""", (
                result.model_dump_json(), ContentBriefStatus.COMPLETE.value,
                ContentBriefStage.COMPLETE.value, json.dumps(result.warnings),
                utc_now().isoformat(), result.generation_id,
            ))

    def retry_generation(self, generation_id: str) -> ContentBriefRecord:
        current = self.get_generation(generation_id)
        if current.status not in {ContentBriefStatus.COMPLETE, ContentBriefStatus.FAILED}:
            raise ValueError("Only failed or completed generations can be queued again")
        with self.connect() as connection:
            self._execute(connection, """UPDATE content_brief_generations
                SET status=?,stage=?,progress=0,draft_json=NULL,result_json=NULL,warnings_json='[]',error=NULL,updated_at=? WHERE id=?""", (
                ContentBriefStatus.QUEUED.value, ContentBriefStage.QUEUED.value,
                utc_now().isoformat(), generation_id,
            ))
        return self.get_generation(generation_id)

    @staticmethod
    def _from_row(row: Any) -> ContentBriefRecord:
        return ContentBriefRecord(
            id=row["id"], request=ContentBriefCreate.model_validate_json(row["request_json"]),
            status=row["status"], stage=row["stage"], progress=row["progress"],
            draft=ContentBriefDraft.model_validate_json(row["draft_json"]) if row["draft_json"] else None,
            result=ContentBriefResult.model_validate_json(row["result_json"]) if row["result_json"] else None,
            warnings=json.loads(row["warnings_json"]), error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class MemoryContentBriefRepository:
    def __init__(self) -> None:
        self.runs: dict[str, ContentBriefRecord] = {}

    def initialize(self) -> None:
        return None

    def create_generation(self, request: ContentBriefCreate) -> ContentBriefRecord:
        run = ContentBriefRecord(request=request)
        self.runs[run.id] = run
        return run.model_copy(deep=True)

    def get_generation(self, generation_id: str) -> ContentBriefRecord:
        try:
            return self.runs[generation_id].model_copy(deep=True)
        except KeyError as exc:
            raise ContentBriefNotFoundError(generation_id) from exc

    def list_generations(self, limit: int = 20, offset: int = 0, query: str | None = None) -> list[ContentBriefRecord]:
        runs = sorted(self.runs.values(), key=lambda item: item.created_at, reverse=True)
        if query and query.strip():
            needle = query.strip().casefold()
            runs = [item for item in runs if needle in item.request.model_dump_json().casefold()]
        return [item.model_copy(deep=True) for item in runs[offset:offset + limit]]

    def count_generations(self, query: str | None = None) -> int:
        if not query or not query.strip():
            return len(self.runs)
        needle = query.strip().casefold()
        return sum(needle in run.request.model_dump_json().casefold() for run in self.runs.values())

    def delete_generation(self, generation_id: str) -> None:
        self.get_generation(generation_id)
        self.runs.pop(generation_id)

    def update_generation(self, generation_id: str, *, status=None, stage=None, progress=None, warnings=None, error=None) -> ContentBriefRecord:
        current = self.get_generation(generation_id)
        updated = current.model_copy(update={
            "status": status or current.status, "stage": stage or current.stage,
            "progress": current.progress if progress is None else progress,
            "warnings": current.warnings if warnings is None else warnings,
            "error": error, "updated_at": utc_now(),
        }, deep=True)
        self.runs[generation_id] = updated
        return updated.model_copy(deep=True)

    def claim_generation(self, generation_id: str) -> ContentBriefRecord | None:
        current = self.get_generation(generation_id)
        if current.status != ContentBriefStatus.QUEUED:
            return None
        return self.update_generation(generation_id, status=ContentBriefStatus.RUNNING, stage=ContentBriefStage.NORMALIZING, progress=3)

    def save_draft(self, generation_id: str, draft: ContentBriefDraft) -> None:
        current = self.get_generation(generation_id)
        self.runs[generation_id] = current.model_copy(update={"draft": draft, "updated_at": utc_now()}, deep=True)

    def save_result(self, result: ContentBriefResult) -> None:
        current = self.get_generation(result.generation_id)
        self.runs[result.generation_id] = current.model_copy(update={
            "result": result, "status": ContentBriefStatus.COMPLETE,
            "stage": ContentBriefStage.COMPLETE, "progress": 100,
            "warnings": result.warnings, "error": None, "updated_at": utc_now(),
        }, deep=True)

    def retry_generation(self, generation_id: str) -> ContentBriefRecord:
        current = self.get_generation(generation_id)
        if current.status not in {ContentBriefStatus.COMPLETE, ContentBriefStatus.FAILED}:
            raise ValueError("Only failed or completed generations can be queued again")
        retried = current.model_copy(update={
            "status": ContentBriefStatus.QUEUED, "stage": ContentBriefStage.QUEUED,
            "progress": 0, "draft": None, "result": None, "warnings": [],
            "error": None, "updated_at": utc_now(),
        }, deep=True)
        self.runs[generation_id] = retried
        return retried.model_copy(deep=True)
