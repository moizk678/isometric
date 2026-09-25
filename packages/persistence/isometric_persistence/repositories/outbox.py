"""Outbox event dispatch repository."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from psycopg import Connection


@dataclass(frozen=True)
class OutboxEvent:
    id: uuid.UUID
    event_type: str
    aggregate_id: uuid.UUID
    event_key: str
    payload: dict[str, Any]


class OutboxRepository:
    def list_pending(
        self, conn: Connection[Any], *, limit: int = 100
    ) -> list[OutboxEvent]:
        rows = conn.execute(
            """
            SELECT id, event_type, aggregate_id, event_key, payload
            FROM drawing.outbox_events
            WHERE publish_state = 'pending'
            ORDER BY created_at
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
        return [
            OutboxEvent(
                id=row["id"],
                event_type=row["event_type"],
                aggregate_id=row["aggregate_id"],
                event_key=row["event_key"],
                payload=row["payload"],
            )
            for row in rows
        ]

    def mark_published(self, conn: Connection[Any], event_id: uuid.UUID) -> None:
        conn.execute(
            """
            UPDATE drawing.outbox_events
            SET publish_state = 'published', published_at = now()
            WHERE id = %s AND publish_state = 'pending'
            """,
            (event_id,),
        )
