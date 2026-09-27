"""Stable API error envelope."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from .schemas import ErrorResponse

_ERROR_DESCRIPTIONS = {
    400: "Invalid request",
    401: "Missing caller identity",
    403: "Forbidden",
    404: "Not found",
    405: "Method not allowed",
    409: "Conflict",
    428: "Precondition required",
    413: "Payload too large",
    415: "Unsupported media type",
    500: "Internal server error",
}

HTTP_ERROR_CODES = {
    404: ("not_found", "resource not found"),
    405: ("method_not_allowed", "method not allowed"),
}


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    return {
        status: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[status]}
        for status in statuses
    }


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        super().__init__(message)


def envelope_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None = None,
) -> JSONResponse:
    rid = request_id or getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "request_id": rid,
        },
        headers={"X-Request-Id": rid},
    )


def error_response(
    request: Request, exc: ApiError, *, request_id: str | None = None
) -> JSONResponse:
    rid = request_id or getattr(request.state, "request_id", str(uuid.uuid4()))
    return envelope_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        request_id=rid,
    )
