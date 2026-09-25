"""FastAPI application factory."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from isometric_persistence.artifacts import FilesystemArtifactStore
from isometric_persistence.config import load_database_settings
from isometric_persistence.db import DatabasePool
from isometric_worker.queue import load_queue
from starlette.exceptions import HTTPException as StarletteHTTPException

from .deps import AppState, new_request_id
from .errors import ApiError, envelope_response, error_response
from .routes import router
from .settings import load_settings


def create_app() -> FastAPI:
    settings = load_settings()
    pool = DatabasePool(load_database_settings())
    store = FilesystemArtifactStore(settings.artifact_root)
    queue = load_queue()
    app = FastAPI(title="Isometric API", version="0.1.0")
    app.state.runtime = AppState(settings=settings, pool=pool, store=store, queue=queue)
    app.include_router(router)

    if os.environ.get("ENABLE_API_TEST_HOOKS") == "1":

        @app.get("/api/v1/__test__/internal-error")
        def _test_internal_error() -> None:
            raise RuntimeError("test internal error hook")

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request.state.request_id = new_request_id()
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return envelope_response(
            request,
            status_code=400,
            code="invalid_request",
            message="request validation failed",
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception):
        if isinstance(exc, StarletteHTTPException):
            raise exc
        return envelope_response(
            request,
            status_code=500,
            code="internal_error",
            message="internal server error",
        )

    return app


app = create_app()
