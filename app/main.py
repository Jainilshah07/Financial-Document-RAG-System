from fastapi import FastAPI

from app.api import health
from app.api.middleware import add_trace_middleware
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Application factory: tests can build a fresh app; uvicorn uses `app` below."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)

    application = FastAPI(
        title="Financial Document RAG",
        version="0.1.0",
        description="Semantic RAG over purchase orders and invoices (Sprint 1).",
    )
    add_trace_middleware(application)
    application.include_router(health.router)
    return application


app = create_app()
