from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.schemas.documents import DocumentOut


def _query_with_chunk_count():
    """Documents plus the number of their *active* chunks, in one query."""
    return (
        select(Document, func.count(Chunk.id).filter(Chunk.is_active.is_(True)))
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
    )


def _to_out(document: Document, chunk_count: int) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        doc_type=document.doc_type,
        doc_number=document.doc_number,
        status=document.status,
        status_detail=document.status_detail,
        page_count=document.page_count,
        is_scanned=document.is_scanned,
        chunk_count=chunk_count,
        created_at=document.created_at,
    )


def list_documents(session: Session, limit: int, offset: int) -> list[DocumentOut]:
    rows = session.execute(
        _query_with_chunk_count().order_by(Document.id).limit(limit).offset(offset)
    ).all()
    return [_to_out(document, count) for document, count in rows]


def get_document(session: Session, document_id: int) -> DocumentOut | None:
    row = session.execute(_query_with_chunk_count().where(Document.id == document_id)).first()
    return _to_out(*row) if row else None
