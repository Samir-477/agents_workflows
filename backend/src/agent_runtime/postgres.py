from __future__ import annotations

import re
import time
from contextlib import contextmanager
from threading import RLock
from typing import Any, Iterator


def is_transient_database_error(error: BaseException) -> bool:
    try:
        import psycopg
    except ImportError:
        return False
    return isinstance(error, (psycopg.OperationalError, psycopg.InterfaceError))


class _RetryingConnection:
    """Retry one interrupted read on a fresh PostgreSQL connection."""

    def __init__(self, connection: Any, reconnect, retryable_errors: tuple[type[BaseException], ...]):
        self._connection = connection
        self._reconnect = reconnect
        self._retryable_errors = retryable_errors

    def execute(self, statement: str, params: Any = None):
        try:
            return self._connection.execute(statement) if params is None else self._connection.execute(statement, params)
        except self._retryable_errors:
            # Reads are safe to repeat. Retrying writes could duplicate an insert
            # when the server committed it before the connection was interrupted.
            if not statement.lstrip().upper().startswith(("SELECT", "WITH", "SHOW")):
                raise
            try:
                self._connection.close()
            except Exception:
                pass
            time.sleep(0.15)
            self._connection = self._reconnect()
            return self._connection.execute(statement) if params is None else self._connection.execute(statement, params)

    def __getattr__(self, name: str):
        return getattr(self._connection, name)


class PostgresRepository:
    """Small shared PostgreSQL adapter used by agent-specific repositories."""

    _pools: dict[str, Any] = {}
    _pool_lock = RLock()

    def __init__(self, database_url: str | None):
        if not database_url:
            raise ValueError("DATABASE_URL is required for persisted agent runs.")
        self.database_url = database_url

    def _connection_pool(self):
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        with self._pool_lock:
            pool = self._pools.get(self.database_url)
            if pool is None:
                pool = ConnectionPool(
                    self.database_url,
                    min_size=0,
                    max_size=8,
                    timeout=8,
                    open=True,
                    kwargs={
                        "row_factory": dict_row,
                        "prepare_threshold": None,
                        "connect_timeout": 8,
                    },
                )
                self._pools[self.database_url] = pool
            return pool

    @contextmanager
    def connect(self) -> Iterator[Any]:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL requires the 'psycopg[binary]' package"
            ) from exc
        def open_connection():
            return psycopg.connect(
                self.database_url,
                row_factory=dict_row,
                prepare_threshold=None,
                connect_timeout=8,
            )

        pool = self._connection_pool()
        with pool.connection() as raw_connection:
            connection = _RetryingConnection(
                raw_connection,
                open_connection,
                (psycopg.OperationalError, psycopg.InterfaceError),
            )
            try:
                yield connection
                connection.commit()
            except Exception:
                try:
                    connection.rollback()
                except Exception:
                    # Preserve the operation error when the server has already dropped
                    # the connection and rollback is no longer possible.
                    pass
                raise
            finally:
                # A retried read owns its direct replacement connection. The
                # original pooled connection is returned (or discarded if closed)
                # by the pool context itself.
                if connection._connection is not raw_connection:
                    try:
                        connection.close()
                    except Exception:
                        pass

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
