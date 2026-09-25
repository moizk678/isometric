"""Stable API error envelope."""

from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        super().__init__(message)


def error_response(
    request: Request, exc: ApiError, *, request_id: str | None = None
) -> JSONResponse:
    rid = request_id or getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": str(exc),
            "request_id": rid,
        },
    )
