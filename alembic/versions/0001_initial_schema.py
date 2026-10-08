"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-08

Creates all Sprint 1 tables with table and column comments (visible in DBeaver, pgAdmin, psql).
Column order is deliberate: id first, important columns next, created_at/updated_at last.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('ingestion_runs',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False, comment='Surrogate primary key (auto-increment from 1).'),
    sa.Column('status', sa.Enum('running', 'succeeded', 'failed', name='runstatus', native_enum=False, length=20), nullable=False, comment='running | succeeded | failed.'),
    sa.Column('pipeline_version', sa.String(length=32), nullable=False, comment='Version label of the ingestion code/config (parser, chunker, embedder).'),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, comment='When the run started (UTC).'),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True, comment='When the run ended (UTC); NULL while running.'),
    sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Free-form run metrics (documents, chunks, embeddings, errors).'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ingestion_runs')),
    comment='One execution of the ingestion pipeline; links derived rows (chunks) to the pipeline version that produced them.'
    )
    op.create_table('documents',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False, comment='Surrogate primary key (auto-increment from 1).'),
    sa.Column('filename', sa.String(length=255), nullable=False, comment='Original uploaded file name.'),
    sa.Column('mime_type', sa.String(length=100), nullable=False, comment='e.g. application/pdf, image/png.'),
    sa.Column('doc_type', sa.Enum('purchase_order', 'invoice', 'unknown', name='documenttype', native_enum=False, length=20), nullable=False, comment='purchase_order | invoice | unknown. Stays unknown until extraction (Sprint 3).'),
    sa.Column('doc_number', sa.String(length=100), nullable=True, comment='PO / invoice number as printed on the document; NULL until extracted.'),
    sa.Column('page_count', sa.Integer(), nullable=False, comment='Number of pages.'),
    sa.Column('is_scanned', sa.Boolean(), nullable=False, comment='True if the content is image-only and needs OCR.'),
    sa.Column('status', sa.Enum('pending', 'ingested', 'needs_ocr', 'empty', 'failed', name='documentstatus', native_enum=False, length=20), nullable=False, comment='pending | ingested | needs_ocr | empty | failed.'),
    sa.Column('status_detail', sa.Text(), nullable=True, comment='Human-readable reason for needs_ocr / empty / failed.'),
    sa.Column('latest_run_id', sa.Integer(), nullable=True, comment='Most recent ingestion run that processed this file.'),
    sa.Column('content_hash', sa.String(length=64), nullable=False, comment='SHA-256 of the file bytes; uniqueness makes re-uploads idempotent.'),
    sa.Column('storage_uri', sa.String(length=1024), nullable=False, comment='Where the raw file is stored (local path now; object store later).'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Row creation time (UTC).'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Time of the last update to this row (UTC).'),
    sa.ForeignKeyConstraint(['latest_run_id'], ['ingestion_runs.id'], name=op.f('fk_documents_latest_run_id_ingestion_runs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_documents')),
    sa.UniqueConstraint('content_hash', name=op.f('uq_documents_content_hash')),
    comment='One uploaded file (purchase order or invoice). Canonical record of the source.'
    )
    op.create_table('chunks',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False, comment='Surrogate primary key (auto-increment from 1).'),
    sa.Column('document_id', sa.Integer(), nullable=False, comment='Owning document; chunks are deleted with it.'),
    sa.Column('chunk_index', sa.Integer(), nullable=False, comment='0-based position of the chunk within its document.'),
    sa.Column('page_start', sa.Integer(), nullable=False, comment='First page the chunk covers (1-based).'),
    sa.Column('page_end', sa.Integer(), nullable=False, comment='Last page the chunk covers (1-based).'),
    sa.Column('section', sa.String(length=200), nullable=True, comment="Section/clause heading, e.g. 'Payment Terms'; NULL if none."),
    sa.Column('chunk_type', sa.Enum('header', 'table', 'clause', 'text', 'footer', name='chunktype', native_enum=False, length=20), nullable=False, comment='header | table | clause | text | footer.'),
    sa.Column('text', sa.Text(), nullable=False, comment='Chunk text exactly as shown in citations.'),
    sa.Column('token_count', sa.Integer(), nullable=False, comment='Approximate token count of the text.'),
    sa.Column('is_active', sa.Boolean(), nullable=False, comment='False once superseded by a newer ingestion; inactive chunks are not searched.'),
    sa.Column('parent_chunk_id', sa.Integer(), nullable=True, comment='Optional parent chunk for parent-child retrieval (unused in v1).'),
    sa.Column('run_id', sa.Integer(), nullable=True, comment='Ingestion run that produced this chunk.'),
    sa.Column('pipeline_version', sa.String(length=32), nullable=False, comment='Pipeline version that produced this chunk.'),
    sa.Column('content_hash', sa.String(length=64), nullable=False, comment='SHA-256 of the chunk text.'),
    sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Extra structural metadata (e.g. contextual prefix fields).'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Row creation time (UTC).'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name=op.f('fk_chunks_document_id_documents'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_chunk_id'], ['chunks.id'], name=op.f('fk_chunks_parent_chunk_id_chunks')),
    sa.ForeignKeyConstraint(['run_id'], ['ingestion_runs.id'], name=op.f('fk_chunks_run_id_ingestion_runs')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chunks')),
    comment='Retrievable unit of text and the unit we cite. Canonical; the Qdrant index is derived from it.'
    )
    op.create_table('document_pages',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False, comment='Surrogate primary key (auto-increment from 1).'),
    sa.Column('document_id', sa.Integer(), nullable=False, comment='Owning document; pages are deleted with it.'),
    sa.Column('page_number', sa.Integer(), nullable=False, comment='1-based page number, as people cite pages.'),
    sa.Column('text', sa.Text(), nullable=False, comment='Normalised page text (text layer, form-field values or OCR).'),
    sa.Column('text_source', sa.Enum('native', 'ocr', name='textsource', native_enum=False, length=20), nullable=False, comment='native (PDF text/form fields) | ocr.'),
    sa.Column('ocr_mean_confidence', sa.Float(), nullable=True, comment='Mean OCR confidence 0-1; NULL for native text (used from Sprint 4).'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Row creation time (UTC).'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name=op.f('fk_document_pages_document_id_documents'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_document_pages')),
    sa.UniqueConstraint('document_id', 'page_number', name=op.f('uq_document_pages_document_id')),
    comment='One page of a document with its extracted text; the stable unit of citation.'
    )
    op.create_table('chunk_embeddings',
    sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False, comment='Surrogate primary key (auto-increment from 1).'),
    sa.Column('chunk_id', sa.Integer(), nullable=False, comment='Embedded chunk; the vector is deleted with it.'),
    sa.Column('embedding_model', sa.String(length=100), nullable=False, comment='Model id and dimension, e.g. gemini-embedding-001:768.'),
    sa.Column('dim', sa.Integer(), nullable=False, comment='Vector dimensionality.'),
    sa.Column('embedding', postgresql.ARRAY(sa.REAL()), nullable=False, comment='The embedding vector (float4 array).'),
    sa.Column('input_hash', sa.String(length=64), nullable=False, comment='SHA-256 of the exact text sent to the embedder (prefix + chunk text); cache key together with embedding_model.'),
    sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id'], name=op.f('fk_chunk_embeddings_chunk_id_chunks'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chunk_embeddings')),
    sa.UniqueConstraint('chunk_id', 'embedding_model', name=op.f('uq_chunk_embeddings_chunk_id')),
    comment='Embedding cache (not the search index): one vector per chunk per model.'
    )
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_pages_document_id'), 'document_pages', ['document_id'], unique=False)
    op.create_index('ix_chunk_embeddings_model_input_hash', 'chunk_embeddings', ['embedding_model', 'input_hash'], unique=False)


def downgrade() -> None:
    op.drop_table('chunk_embeddings')
    op.drop_table('document_pages')
    op.drop_table('chunks')
    op.drop_table('documents')
    op.drop_table('ingestion_runs')
