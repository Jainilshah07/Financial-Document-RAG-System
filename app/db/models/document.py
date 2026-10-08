from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, IntPrimaryKeyMixin, TimestampMixin
from app.db.models.enums import DocumentStatus, DocumentType, RunStatus, TextSource

# Column order convention (it becomes the physical table layout): id first, then the
# columns people look at most, then technical/lineage columns, then created_at/updated_at.


def str_enum(enum_cls: type, length: int = 20) -> Enum:
    """Store enum *values* as plain VARCHAR (not a native PG enum): adding a value later
    needs no migration at all. Python validates values on write (`validate_strings`)."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class IngestionRun(IntPrimaryKeyMixin, Base):
    """One execution of the ingestion pipeline. Ties derived rows (chunks) to the
    pipeline version that produced them."""

    __tablename__ = "ingestion_runs"
    __table_args__ = {
        "comment": "One execution of the ingestion pipeline; links derived rows (chunks) to "
        "the pipeline version that produced them."
    }

    status: Mapped[RunStatus] = mapped_column(
        str_enum(RunStatus),
        default=RunStatus.RUNNING,
        comment="running | succeeded | failed.",
    )
    pipeline_version: Mapped[str] = mapped_column(
        String(32),
        comment="Version label of the ingestion code/config (parser, chunker, embedder).",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="When the run started (UTC)."
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="When the run ended (UTC); NULL while running."
    )
    stats: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        comment="Free-form run metrics (documents, chunks, embeddings, errors).",
    )


class Document(IntPrimaryKeyMixin, TimestampMixin, Base):
    """One uploaded file. `content_hash` (sha256 of the bytes) makes uploads idempotent."""

    __tablename__ = "documents"
    __table_args__ = {
        "comment": "One uploaded file (purchase order or invoice). Canonical record of the source."
    }

    filename: Mapped[str] = mapped_column(String(255), comment="Original uploaded file name.")
    mime_type: Mapped[str] = mapped_column(String(100), comment="e.g. application/pdf, image/png.")
    doc_type: Mapped[DocumentType] = mapped_column(
        str_enum(DocumentType),
        default=DocumentType.UNKNOWN,
        comment="purchase_order | invoice | unknown. Stays unknown until extraction (Sprint 3).",
    )
    doc_number: Mapped[str | None] = mapped_column(
        String(100),
        comment="PO / invoice number as printed on the document; NULL until extracted.",
    )
    page_count: Mapped[int] = mapped_column(Integer, default=0, comment="Number of pages.")
    is_scanned: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="True if the content is image-only and needs OCR."
    )
    status: Mapped[DocumentStatus] = mapped_column(
        str_enum(DocumentStatus),
        default=DocumentStatus.PENDING,
        comment="pending | ingested | needs_ocr | empty | failed.",
    )
    status_detail: Mapped[str | None] = mapped_column(
        Text, comment="Human-readable reason for needs_ocr / empty / failed."
    )
    latest_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id"),
        comment="Most recent ingestion run that processed this file.",
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        comment="SHA-256 of the file bytes; uniqueness makes re-uploads idempotent.",
    )
    storage_uri: Mapped[str] = mapped_column(
        String(1024),
        comment="Where the raw file is stored (local path now; object store later).",
    )

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )


class DocumentPage(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    """One page. The page is the stable unit of citation (chunk ids change when
    chunking changes; pages do not)."""

    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number"),
        {"comment": "One page of a document with its extracted text; the stable unit of citation."},
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        comment="Owning document; pages are deleted with it.",
    )
    page_number: Mapped[int] = mapped_column(
        Integer, comment="1-based page number, as people cite pages."
    )
    text: Mapped[str] = mapped_column(
        Text, default="", comment="Normalised page text (text layer, form-field values or OCR)."
    )
    text_source: Mapped[TextSource] = mapped_column(
        str_enum(TextSource),
        default=TextSource.NATIVE,
        comment="native (PDF text/form fields) | ocr.",
    )
    ocr_mean_confidence: Mapped[float | None] = mapped_column(
        Float, comment="Mean OCR confidence 0-1; NULL for native text (used from Sprint 4)."
    )

    document: Mapped[Document] = relationship(back_populates="pages")
