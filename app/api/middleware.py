import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response

TRACE_HEADER = "X-Trace-Id"
log = structlog.get_logger("http")


def add_trace_middleware(app: FastAPI) -> None:
    """Give every request a trace id and log one summary line per request."""

    @app.middleware("http")
    async def trace_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Accept an id from the caller (so a trace can span services) or make one.
        trace_id = request.headers.get(TRACE_HEADER) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        started = time.perf_counter()
        response = await call_next(request)
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        response.headers[TRACE_HEADER] = trace_id
        return response
