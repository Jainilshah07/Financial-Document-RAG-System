"""The ingestion pipeline: file bytes in -> searchable, cited chunks out.

    register (hash, dedupe, store file)
      -> parse -> save pages
      -> chunk -> save chunks (inactive)
      -> embed (cache first) -> commit
      -> upsert to the vector index -> activate chunks

Write order matters (ADR-004): Postgres is the source of truth and is written first. A
chunk only becomes `is_active` after its vector is in the index, so a crash half-way
leaves harmless inactive rows, never a searchable chunk that Postgres does not know.
Re-running after a failure is cheap because vectors are cached by input text.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Chunk, Document, DocumentPage, IngestionRun
from app.db.models.enums import DocumentStatus, RunStatus
from app.embeddings.base import Embedder
from app.ingestion.chunker import CHUNKER_VERSION, chunk_document
from app.ingestion.embedding_cache import embed_chunks
from app.ingestion.embedding_text import build_embedding_input
from app.ingestion.pdf_parser import parse_document
from app.ingestion.storage import LocalFileStorage
from app.ingestion.types import ParsedDocument
from app.retrieval.types import IndexPoint
from app.retrieval.vector_index import VectorIndex

log = structlog.get_logger("ingestion")

# Bump when parsing/normalising/chunking behaviour changes (recorded on every chunk).
PIPELINE_VERSION = CHUNKER_VERSION
# A document in one of these states is done; re-uploading it is a no-op.
_FINAL_STATUSES = {DocumentStatus.INGESTED, DocumentStatus.NEEDS_OCR, DocumentStatus.EMPTY}
_MAX_DETAIL = 1000


@dataclass(frozen=True)
class IngestResult:
    document_id: int
    filename: str
    status: DocumentStatus
    status_detail: str | None
    page_count: int
    chunk_count: int
    already_exists: bool = False
    unreadable: bool = False  # the file itself could not be opened (client error)
    internal_error: bool = False  # something on our side failed after the file was fine


class IngestionService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        embedder: Embedder,
        index: VectorIndex,
        storage: LocalFileStorage,
    ) -> None:
        self._session_factory = session_factory
        self._embedder = embedder
        self._index = index
        self._storage = storage

    def ingest(self, filename: str, content: bytes, mime_type: str) -> IngestResult:
        content_hash = hashlib.sha256(content).hexdigest()
        with self._session_factory() as session:
            document = session.scalar(select(Document).where(Document.content_hash == content_hash))
            if document is not None and document.status in _FINAL_STATUSES:
                log.info("ingest_skipped_duplicate", document_id=document.id)
                return self._result(session, document, already_exists=True)

            if document is None:
                document, created = self._register(
                    session, filename, content, mime_type, content_hash
                )
                if not created:  # another request registered the same file first
                    return self._result(session, document, already_exists=True)

            document_id = document.id
            run = IngestionRun(
                started_at=datetime.now(UTC),
                pipeline_version=PIPELINE_VERSION,
                status=RunStatus.RUNNING,
            )
            session.add(run)
            session.flush()
            run_id = run.id
            document.latest_run_id = run_id
            session.commit()  # the attempt is on record even if the steps below crash

            try:
                unreadable = self._process(session, document, run, content, mime_type)
            except Exception as exc:  # noqa: BLE001 - record any failure, never lose a document
                session.rollback()
                log.exception("ingestion_failed", document_id=document_id)
                detail = f"{exc.__class__.__name__}: {exc}"[:_MAX_DETAIL]
                self._mark_failed(session, document_id, run_id, detail)
                return self._result(
                    session, session.get(Document, document_id), internal_error=True
                )
            return self._result(session, document, unreadable=unreadable)

    # --- steps -------------------------------------------------------------------

    def _register(
        self, session: Session, filename: str, content: bytes, mime_type: str, content_hash: str
    ) -> tuple[Document, bool]:
        document = Document(
            content_hash=content_hash,
            filename=filename[:255],
            storage_uri=self._storage.save(content_hash, filename, content),
            mime_type=mime_type,
            status=DocumentStatus.PENDING,
        )
        session.add(document)
        try:
            session.flush()
        except IntegrityError:  # unique(content_hash): lost a race with a parallel upload
            session.rollback()
            existing = session.scalar(select(Document).where(Document.content_hash == content_hash))
            return existing, False
        return document, True

    def _process(
        self,
        session: Session,
        document: Document,
        run: IngestionRun,
        content: bytes,
        mime_type: str,
    ) -> bool:
        """Returns True if the file could not be opened at all."""
        parsed = parse_document(content, mime_type)
        self._replace_pages(session, document, parsed)
        document.page_count = parsed.page_count
        document.is_scanned = parsed.is_scanned

        superseded = self._deactivate_existing_chunks(session, document)
        chunk_count = 0
        if parsed.status is DocumentStatus.INGESTED:
            chunk_count = self._chunk_embed_index(session, document, run, parsed)

        # The final status is set last. If the process dies earlier, the document stays
        # `pending` and the next upload of the same file reprocesses it.
        document.status = parsed.status
        document.status_detail = parsed.status_detail

        unreadable = parsed.status is DocumentStatus.FAILED
        run.status = RunStatus.FAILED if unreadable else RunStatus.SUCCEEDED
        run.finished_at = datetime.now(UTC)
        run.stats = {
            "pages": parsed.page_count,
            "chunks": chunk_count,
            "status": parsed.status.value,
        }
        session.commit()

        self._index.delete(superseded)  # after the commit that deactivated them
        log.info(
            "ingested", document_id=document.id, status=parsed.status.value, chunks=chunk_count
        )
        return unreadable

    def _replace_pages(self, session: Session, document: Document, parsed: ParsedDocument) -> None:
        # Bulk delete first (not via the relationship) so re-ingesting a page number never
        # collides with the old row in the same flush.
        session.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
        session.expire(document, ["pages"])
        session.add_all(
            DocumentPage(
                document_id=document.id,
                page_number=p.page_number,
                text=p.text,
                text_source=p.text_source,
            )
            for p in parsed.pages
        )

    def _deactivate_existing_chunks(self, session: Session, document: Document) -> list[int]:
        """Tombstone (not delete) chunks from an earlier run. Their cached embeddings stay
        reusable, so a retry after a failure does not pay for the API again."""
        old = list(
            session.scalars(
                select(Chunk).where(Chunk.document_id == document.id, Chunk.is_active.is_(True))
            )
        )
        for chunk in old:
            chunk.is_active = False
        return [chunk.id for chunk in old]

    def _chunk_embed_index(
        self, session: Session, document: Document, run: IngestionRun, parsed: ParsedDocument
    ) -> int:
        drafts = chunk_document(parsed.pages)
        chunks = [
            Chunk(
                document_id=document.id,
                chunk_index=d.chunk_index,
                page_start=d.page_start,
                page_end=d.page_end,
                section=d.section,
                chunk_type=d.chunk_type,
                text=d.text,
                token_count=d.token_count,
                content_hash=d.content_hash,
                pipeline_version=PIPELINE_VERSION,
                run_id=run.id,
                is_active=False,
            )
            for d in drafts
        ]
        session.add_all(chunks)
        session.flush()  # assigns chunk ids

        inputs = [build_embedding_input(document.filename, d) for d in drafts]
        vectors = embed_chunks(session, self._embedder, list(zip(chunks, inputs, strict=True)))
        session.commit()  # chunks (inactive) + embeddings are durable before touching the index

        self._index.upsert(
            [
                IndexPoint(
                    chunk_id=c.id,
                    vector=vectors[c.id],
                    payload={
                        "chunk_id": c.id,
                        "document_id": document.id,
                        "document_type": document.doc_type.value,
                        "document_number": document.doc_number,
                        "page_start": c.page_start,
                        "section": c.section,
                        "chunk_type": c.chunk_type.value,
                        "pipeline_version": c.pipeline_version,
                        "embedding_model": self._embedder.model_id,
                        "is_active": True,
                    },
                )
                for c in chunks
            ]
        )
        for chunk in chunks:
            chunk.is_active = True
        return len(chunks)

    def _mark_failed(self, session: Session, document_id: int, run_id: int, detail: str) -> None:
        document = session.get(Document, document_id)
        run = session.get(IngestionRun, run_id)
        document.status = DocumentStatus.FAILED
        document.status_detail = detail
        run.status = RunStatus.FAILED
        run.finished_at = datetime.now(UTC)
        run.stats = {"error": detail[:500]}
        session.commit()

    def _result(self, session: Session, document: Document, **flags: bool) -> IngestResult:
        chunk_count = session.scalar(
            select(func.count(Chunk.id)).where(
                Chunk.document_id == document.id, Chunk.is_active.is_(True)
            )
        )
        return IngestResult(
            document_id=document.id,
            filename=document.filename,
            status=document.status,
            status_detail=document.status_detail,
            page_count=document.page_count,
            chunk_count=chunk_count or 0,
            **flags,
        )
