"""Bounded PostgreSQL connection pool."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import DatabaseSettings


class DatabasePool:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._pool = ConnectionPool(
            conninfo=settings.url,
            min_size=settings.min_pool_size,
            max_size=settings.max_pool_size,
            kwargs={"row_factory": dict_row, "autocommit": False},
            open=True,
        )

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        with self._pool.connection() as conn:
            yield conn

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        with self._pool.connection() as conn:
            with conn.transaction():
                yield conn
