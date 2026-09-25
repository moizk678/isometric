"""Durable queue adapters."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections import deque


class JobQueue(ABC):
    @abstractmethod
    def enqueue(self, job_id: str) -> None: ...

    @abstractmethod
    def dequeue(self) -> str | None: ...


class LocalJobQueue(JobQueue):
    def __init__(self) -> None:
        self._items: deque[str] = deque()
        self._lock = threading.Lock()

    def enqueue(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._items:
                self._items.append(job_id)

    def dequeue(self) -> str | None:
        with self._lock:
            if not self._items:
                return None
            return self._items.popleft()


class ProductionJobQueue(JobQueue):
    """Production adapter; requires QUEUE_URL (Run 19)."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "Production queue adapter is not implemented in Run 04; use LocalJobQueue"
        )

    def enqueue(self, job_id: str) -> None:
        raise NotImplementedError

    def dequeue(self) -> str | None:
        raise NotImplementedError


def load_queue() -> JobQueue:
    return LocalJobQueue()
