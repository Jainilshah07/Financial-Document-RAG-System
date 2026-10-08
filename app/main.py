from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import documents, health
from app.api.middleware import add_trace_middleware
from app.core.config import get_settings
from app.core.container import build_container
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Build the shared objects once at startup; release them at shutdown."""
    container = build_container(get_settings())
    application.state.container = container
    try:
        yield
    finally:
        container.close()


def create_app() -> FastAPI:
    """Application factory: tests can build a fresh app; uvicorn uses `app` below."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)

    application = FastAPI(
        title="Financial Document RAG",
        version="0.1.0",
        description="Semantic RAG over purchase orders and invoices (Sprint 1).",
        lifespan=lifespan,
    )
    add_trace_middleware(application)
    application.include_router(health.router)
    application.include_router(documents.router)
    return application


app = create_app()
