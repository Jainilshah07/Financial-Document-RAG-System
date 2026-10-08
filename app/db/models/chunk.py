from typing import Any

from sqlalchemy import REAL, Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IntPrimaryKeyMixin
from app.db.models.document import str_enum
from app.db.models.enums import ChunkType


class Chunk(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    """A retrievable unit of text and the unit we cite. Canonical (Postgres owns it);
    the Qdrant index is derived from it."""

    __tablename__ = "chunks"
    __table_args__ = {
        "comment": "Retrievable unit of text and the unit we cite. Canonical; the Qdrant index "
        "is derived from it."
    }

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        comment="Owning document; chunks are deleted with it.",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, comment="0-based position of the chunk within its document."
    )
    page_start: Mapped[int] = mapped_column(
        Integer, comment="First page the chunk covers (1-based)."
    )
    page_end: Mapped[int] = mapped_column(Integer, comment="Last page the chunk covers (1-based).")
    section: Mapped[str | None] = mapped_column(
        String(200), comment="Section/clause heading, e.g. 'Payment Terms'; NULL if none."
    )
    chunk_type: Mapped[ChunkType] = mapped_column(
        str_enum(ChunkType),
        default=ChunkType.TEXT,
        comment="header | table | clause | text | footer.",
    )
    text: Mapped[str] = mapped_column(Text, comment="Chunk text exactly as shown in citations.")
    token_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="Approximate token count of the text."
    )
    parent_chunk_id: Mapped[int | None] = mapped_column(
        ForeignKey("chunks.id"),
        comment="Optional parent chunk for parent-child retrieval (unused in v1).",
    )
    content_hash: Mapped[str] = mapped_column(String(64), comment="SHA-256 of the chunk text.")
    pipeline_version: Mapped[str] = mapped_column(
        String(32), comment="Pipeline version that produced this chunk."
    )
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id"), comment="Ingestion run that produced this chunk."
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="False once superseded by a newer ingestion; inactive chunks are not searched.",
    )
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, comment="Extra structural metadata (e.g. contextual prefix fields)."
    )


class ChunkEmbedding(Base):
    """Embedding *cache*, not the search index (that is Qdrant, ADR-004).

    Gemini's free tier allows ~1k requests/day, so a vector is never recomputed if we
    already hold one for identical input text: lookups go by (embedding_model, input_hash).
    """

    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        Index("ix_chunk_embeddings_model_input_hash", "embedding_model", "input_hash"),
        {"comment": "Embedding cache (not the search index): one vector per chunk per model."},
    )

    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Embedded chunk; the vector is deleted with it.",
    )
    embedding_model: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="Model id, e.g. gemini-embedding-001."
    )
    input_hash: Mapped[str] = mapped_column(
        String(64),
        comment="SHA-256 of the exact text sent to the embedder (prefix + chunk text); "
        "cache key together with embedding_model.",
    )
    dim: Mapped[int] = mapped_column(Integer, comment="Vector dimensionality.")
    embedding: Mapped[list[float]] = mapped_column(
        ARRAY(REAL), comment="The embedding vector (float4 array)."
    )
