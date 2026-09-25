"""Persistence-layer errors with stable codes."""

from __future__ import annotations


class PersistenceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ConflictError(PersistenceError):
    def __init__(self, message: str) -> None:
        super().__init__("revision_conflict", message)
