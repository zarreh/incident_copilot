"""FastAPI application wiring for the Incident Investigation Copilot."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, Response
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from oncall.api.middleware import MaxBodySizeMiddleware
from oncall.api.rate_limit import limiter
from oncall.api.routes import health
from oncall.observability import configure_logging
from oncall.settings import get_settings

settings = get_settings()
configure_logging(settings.environment)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Prepare durable directories and an async SQLite checkpointer for the
    app's lifetime. The real investigation graph is built lazily on first use."""
    Path(settings.checkpoint_db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.run_store_path).parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as saver:
        _app.state.checkpointer = saver
        yield


app = FastAPI(
    title="Incident Investigation Copilot",
    description=(
        "An on-call assistant that retrieves logs, runs sandboxed diagnostics, "
        "and drafts incident reports. Uses fully synthetic data."
    ),
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(MaxBodySizeMiddleware, max_body_bytes=settings.max_request_body_bytes)


@app.middleware("http")
async def bind_correlation_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Bind a per-request correlation id for structured logging."""
    request_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
    structlog.contextvars.bind_contextvars(correlation_id=request_id)
    try:
        response = await call_next(request)
    finally:
        structlog.contextvars.unbind_contextvars("correlation_id")
    response.headers["X-Correlation-ID"] = request_id
    return response


app.include_router(health.router)
