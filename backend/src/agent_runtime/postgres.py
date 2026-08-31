from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Any, Iterator


class PostgresRepository:
    """Small shared PostgreSQL adapter used by agent-specific repositories."""

    def __init__(self, database_url: str | None):
        if not database_url:
            raise ValueError("DATABASE_URL is required for persisted agent runs.")
        self.database_url = database_url

    @contextmanager
    def connect(self) -> Iterator[Any]:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL requires the 'psycopg[binary]' package"
            ) from exc
        connection = psycopg.connect(
            self.database_url,
            row_factory=dict_row,
            prepare_threshold=None,
        )
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _sql(statement: str, params: Any = None) -> str:
        if isinstance(params, dict):
            return re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"%(\1)s", statement)
        return statement.replace("?", "%s")

    def _execute(self, connection: Any, statement: str, params: Any = None):
        sql = self._sql(statement, params)
        return (
            connection.execute(sql)
            if params is None
            else connection.execute(sql, params)
        )
