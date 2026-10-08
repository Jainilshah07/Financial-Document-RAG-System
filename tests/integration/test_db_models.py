import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Chunk, ChunkEmbedding, Document, DocumentPage
from app.db.models.enums import DocumentStatus, DocumentType

pytestmark = pytest.mark.integration


def make_document(content_hash: str = "a" * 64) -> Document:
    return Document(
        content_hash=content_hash,
        filename="po.pdf",
        storage_uri="storage/po.pdf",
        mime_type="application/pdf",
    )


def test_document_defaults(session: Session) -> None:
    doc = make_document()
    session.add(doc)
    session.flush()
    session.refresh(doc)

    assert doc.doc_type is DocumentType.UNKNOWN
    assert doc.status is DocumentStatus.PENDING
    assert doc.created_at is not None


def test_content_hash_is_unique(session: Session) -> None:
    session.add(make_document("b" * 64))
    session.flush()
    session.add(make_document("b" * 64))

    with pytest.raises(IntegrityError):
        session.flush()


def test_page_number_is_unique_per_document(session: Session) -> None:
    doc = make_document("c" * 64)
    doc.pages = [DocumentPage(page_number=1, text="a"), DocumentPage(page_number=1, text="b")]
    session.add(doc)

    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_document_cascades_to_pages_chunks_and_embeddings(session: Session) -> None:
    doc = make_document("d" * 64)
    doc.pages = [DocumentPage(page_number=1, text="Payment within 30 days.")]
    session.add(doc)
    session.flush()
    chunk = Chunk(
        document_id=doc.id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        text="Payment within 30 days.",
        content_hash="h",
        pipeline_version="v1",
    )
    session.add(chunk)
    session.flush()
    session.add(
        ChunkEmbedding(
            chunk_id=chunk.id,
            embedding_model="m",
            input_hash="i",
            dim=3,
            embedding=[0.1, 0.2, 0.3],
        )
    )
    session.flush()

    session.delete(doc)
    session.flush()

    assert session.scalars(select(DocumentPage)).all() == []
    assert session.scalars(select(Chunk)).all() == []
    assert session.scalars(select(ChunkEmbedding)).all() == []


def test_embedding_round_trips_as_float_array(session: Session) -> None:
    doc = make_document("e" * 64)
    session.add(doc)
    session.flush()
    chunk = Chunk(
        document_id=doc.id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        text="x",
        content_hash="h",
        pipeline_version="v1",
    )
    session.add(chunk)
    session.flush()
    session.add(
        ChunkEmbedding(
            chunk_id=chunk.id,
            embedding_model="m",
            input_hash="i",
            dim=2,
            embedding=[0.5, -0.25],
        )
    )
    session.flush()
    session.expire_all()

    stored = session.scalars(select(ChunkEmbedding)).one()

    assert stored.embedding == [0.5, -0.25]
