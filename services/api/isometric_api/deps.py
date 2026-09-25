"""FastAPI dependencies and application state."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Request
from isometric_persistence.artifacts import FilesystemArtifactStore
from isometric_persistence.db import DatabasePool
from isometric_worker.queue import JobQueue

from .errors import ApiError
from .settings import ApiSettings


@dataclass
class AppState:
    settings: ApiSettings
    pool: DatabasePool
    store: FilesystemArtifactStore
    queue: JobQueue


def get_state(request: Request) -> AppState:
    return request.app.state.runtime  # type: ignore[attr-defined]


def get_owner_id(request: Request) -> str:
    state = get_state(request)
    owner_id = request.headers.get("X-Owner-Id")
    if owner_id:
        return owner_id
    if state.settings.require_owner_header:
        raise ApiError(401, "unauthorized", "X-Owner-Id header is required")
    return "dev-owner"


def new_request_id() -> str:
    return str(uuid.uuid4())
