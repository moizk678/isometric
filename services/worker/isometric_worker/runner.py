"""Worker loop: outbox dispatch and job processing."""

from __future__ import annotations

import uuid

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.db import DatabasePool
from isometric_persistence.repositories.jobs import JobRepository

from .dispatcher import dispatch_outbox
from .processor import process_job
from .queue import JobQueue


def run_once(pool: DatabasePool, store: ArtifactStore, queue: JobQueue) -> int:
    dispatch_outbox(pool, queue)
    jobs = JobRepository()
    with pool.connection() as conn:
        recovered = jobs.recover_expired_leases(conn)
        conn.commit()
    for recovered_id in recovered:
        queue.enqueue(str(recovered_id))
    processed = 0
    while True:
        job_id = queue.dequeue()
        if job_id is None:
            break
        process_job(pool, store, uuid.UUID(job_id), queue=queue)
        processed += 1
    return processed
