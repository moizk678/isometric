"""Publish pending outbox events to the job queue."""

from __future__ import annotations

from isometric_persistence.db import DatabasePool
from isometric_persistence.repositories.outbox import OutboxRepository

from .queue import JobQueue


def dispatch_outbox(pool: DatabasePool, queue: JobQueue, *, limit: int = 100) -> int:
    outbox = OutboxRepository()
    published = 0
    with pool.connection() as conn:
        events = outbox.list_pending(conn, limit=limit)
        for event in events:
            job_id = event.payload.get("job_id")
            if not job_id:
                continue
            queue.enqueue(str(job_id))
            outbox.mark_published(conn, event.id)
            published += 1
        conn.commit()
    return published
