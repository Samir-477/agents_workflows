from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from agent_runtime.postgres import PostgresRepository
from meta_generator.models import (
    GenerationStage,
    GenerationStatus,
    MetadataGenerationCreate,
    MetadataGenerationRecord,
    MetadataGenerationResult,
    ParsedGenerationBrief,
    utc_now,
)


class MetadataGenerationNotFoundError(LookupError):
    pass


class MetadataGenerationRepository(PostgresRepository):
    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata_generations (
                    id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    parsed_brief_json TEXT,
                    result_json TEXT,
                    warnings_json TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_metadata_generations_created_at
                ON metadata_generations (created_at DESC)
                """
            )

    def create_generation(
        self, request: MetadataGenerationCreate
    ) -> MetadataGenerationRecord:
        generation = MetadataGenerationRecord(prompt=request.prompt)
        with self.connect() as connection:
            self._execute(
                connection,
                """
                INSERT INTO metadata_generations (
                    id, prompt, status, stage, progress, parsed_brief_json,
                    result_json, warnings_json, error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generation.id,
                    generation.prompt,
                    generation.status.value,
                    generation.stage.value,
                    generation.progress,
                    None,
                    None,
                    "[]",
                    None,
                    generation.created_at.isoformat(),
                    generation.updated_at.isoformat(),
                ),
            )
        return generation

    def get_generation(self, generation_id: str) -> MetadataGenerationRecord:
        with self.connect() as connection:
            row = self._execute(
                connection,
                "SELECT * FROM metadata_generations WHERE id = ?",
                (generation_id,),
            ).fetchone()
        if row is None:
            raise MetadataGenerationNotFoundError(generation_id)
        return self._from_row(row)

    def list_generations(
        self, limit: int = 20, offset: int = 0, query: str | None = None
    ) -> list[MetadataGenerationRecord]:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                rows = self._execute(
                    connection,
                    "SELECT * FROM metadata_generations WHERE prompt LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (pattern, limit, offset),
                ).fetchall()
            else:
                rows = self._execute(
                    connection,
                    "SELECT * FROM metadata_generations ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
        return [self._from_row(row) for row in rows]

    def count_generations(self, query: str | None = None) -> int:
        pattern = f"%{query.strip()}%" if query and query.strip() else None
        with self.connect() as connection:
            if pattern:
                row = self._execute(
                    connection,
                    "SELECT COUNT(*) AS total FROM metadata_generations WHERE prompt LIKE ?",
                    (pattern,),
                ).fetchone()
            else:
                row = self._execute(
                    connection,
                    "SELECT COUNT(*) AS total FROM metadata_generations",
                ).fetchone()
        return int(row["total"])

    def delete_generation(self, generation_id: str) -> None:
        self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(
                connection,
                "DELETE FROM metadata_generations WHERE id = ?",
                (generation_id,),
            )

    def update_generation(
        self,
        generation_id: str,
        *,
        status: GenerationStatus | None = None,
        stage: GenerationStage | None = None,
        progress: int | None = None,
        warnings: list[str] | None = None,
        error: str | None = None,
    ) -> MetadataGenerationRecord:
        current = self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(
                connection,
                """
                UPDATE metadata_generations
                SET status = ?, stage = ?, progress = ?, warnings_json = ?,
                    error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    (status or current.status).value,
                    (stage or current.stage).value,
                    current.progress if progress is None else progress,
                    json.dumps(current.warnings if warnings is None else warnings),
                    error,
                    utc_now().isoformat(),
                    generation_id,
                ),
            )
        return self.get_generation(generation_id)

    def claim_generation(self, generation_id: str) -> MetadataGenerationRecord | None:
        with self.connect() as connection:
            updated = self._execute(
                connection,
                """
                UPDATE metadata_generations
                SET status = ?, stage = ?, progress = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (
                    GenerationStatus.RUNNING.value,
                    GenerationStage.PARSING.value,
                    2,
                    utc_now().isoformat(),
                    generation_id,
                    GenerationStatus.QUEUED.value,
                ),
            )
            if updated.rowcount != 1:
                return None
        return self.get_generation(generation_id)

    def save_brief(
        self, generation_id: str, brief: ParsedGenerationBrief
    ) -> MetadataGenerationRecord:
        self.get_generation(generation_id)
        with self.connect() as connection:
            self._execute(
                connection,
                """
                UPDATE metadata_generations
                SET parsed_brief_json = ?, warnings_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    brief.model_dump_json(),
                    json.dumps(brief.warnings),
                    utc_now().isoformat(),
                    generation_id,
                ),
            )
        return self.get_generation(generation_id)

    def save_result(self, result: MetadataGenerationResult) -> None:
        self.get_generation(result.generation_id)
        with self.connect() as connection:
            self._execute(
                connection,
                """
                UPDATE metadata_generations
                SET result_json = ?, status = ?, stage = ?, progress = 100,
                    warnings_json = ?, error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (
                    result.model_dump_json(),
                    GenerationStatus.COMPLETE.value,
                    GenerationStage.COMPLETE.value,
                    json.dumps(result.batch_warnings),
                    utc_now().isoformat(),
                    result.generation_id,
                ),
            )

    def retry_generation(self, generation_id: str) -> MetadataGenerationRecord:
        current = self.get_generation(generation_id)
        if current.status not in {GenerationStatus.COMPLETE, GenerationStatus.FAILED}:
            raise ValueError("Only failed or completed generations can be queued again")
        with self.connect() as connection:
            self._execute(
                connection,
                """
                UPDATE metadata_generations
                SET status = ?, stage = ?, progress = 0, parsed_brief_json = NULL,
                    result_json = NULL, warnings_json = '[]', error = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    GenerationStatus.QUEUED.value,
                    GenerationStage.QUEUED.value,
                    utc_now().isoformat(),
                    generation_id,
                ),
            )
        return self.get_generation(generation_id)

    @staticmethod
    def _from_row(row: Any) -> MetadataGenerationRecord:
        return MetadataGenerationRecord(
            id=row["id"],
            prompt=row["prompt"],
            status=row["status"],
            stage=row["stage"],
            progress=row["progress"],
            parsed_brief=(
                ParsedGenerationBrief.model_validate_json(row["parsed_brief_json"])
                if row["parsed_brief_json"]
                else None
            ),
            result=(
                MetadataGenerationResult.model_validate_json(row["result_json"])
                if row["result_json"]
                else None
            ),
            warnings=json.loads(row["warnings_json"]),
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
