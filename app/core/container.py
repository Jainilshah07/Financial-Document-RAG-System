from dataclasses import dataclass
from pathlib import Path

from qdrant_client import QdrantClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.session import create_db_engine, create_session_factory
from app.embeddings.base import Embedder
from app.embeddings.factory import build_embedder
from app.ingestion.storage import LocalFileStorage
from app.retrieval.qdrant_index import QdrantVectorIndex, build_qdrant_client
from app.retrieval.vector_index import VectorIndex
from app.services.ingestion_service import IngestionService


@dataclass
class Container:
    """The app's long-lived objects, built once at startup and shared by requests.

    Explicit wiring in one place (instead of module-level globals) keeps dependencies
    visible and lets a different set be injected for scripts or tests.
    """

    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    embedder: Embedder
    qdrant_client: QdrantClient
    index: VectorIndex
    ingestion_service: IngestionService

    def close(self) -> None:
        self.qdrant_client.close()  # releases embedded Qdrant's folder lock
        self.engine.dispose()


def build_container(settings: Settings) -> Container:
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)
    embedder = build_embedder(settings)
    qdrant_client = build_qdrant_client(settings)
    index = QdrantVectorIndex(qdrant_client, embedder.model_id, embedder.dimension)
    storage = LocalFileStorage(Path(settings.storage_dir))
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        embedder=embedder,
        qdrant_client=qdrant_client,
        index=index,
        ingestion_service=IngestionService(session_factory, embedder, index, storage),
    )
