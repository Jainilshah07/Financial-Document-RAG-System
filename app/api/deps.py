from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.container import Container
from app.db.session import session_scope
from app.services.ingestion_service import IngestionService


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_ingestion_service(container: Container = Depends(get_container)) -> IngestionService:
    return container.ingestion_service


def get_session(container: Container = Depends(get_container)) -> Iterator[Session]:
    """A database session per request: committed on success, rolled back on error."""
    yield from session_scope(container.session_factory)
