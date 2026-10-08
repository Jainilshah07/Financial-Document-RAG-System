"""Importing this package registers every model on `Base.metadata` (Alembic relies on it)."""

from app.db.models.chunk import Chunk, ChunkEmbedding
from app.db.models.document import Document, DocumentPage, IngestionRun

__all__ = ["Chunk", "ChunkEmbedding", "Document", "DocumentPage", "IngestionRun"]
