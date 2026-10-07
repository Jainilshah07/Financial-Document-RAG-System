# ADR-001 — Data model and canonical-store separation

**Status:** Proposed · **Date:** 2026-10-06

## Context
Sprint 1 is semantic RAG, but the end system needs relational PO/invoice data, provenance and confidence. A retrieval-only schema would force rewrites.

## Decision
PostgreSQL is the canonical store. Hierarchy `documents → document_pages → chunks`; embeddings in a separate derived table keyed by `(chunk_id, embedding_model)`. Structured tables (`vendors`, `purchase_orders`, `invoices`, line items, `field_extractions`, `mismatches`) arrive in Sprints 3/6, not earlier. `document_pages.ocr_mean_confidence` and `documents.doc_type/doc_number` exist from Sprint 1 (nullable). Details: `data-model/schema.md`.

## Alternatives
1. **Vector DB as the only store** (typical tutorial): fast, but no exact filters/aggregates, no provenance; rejected — contradicts the core of PS2.
2. **All tables up front:** speculative, empty, wrong in detail; rejected.
3. **One generic `financial_documents` table / EAV for everything:** flexible but pushes integrity into code and makes SQL arithmetic awkward; EAV is used only for *provenance* (`field_extractions`), not for values.
4. **JSONB blobs for extracted fields:** quick, but weak typing for `NUMERIC` comparisons and constraints.

## Trade-offs
More up-front design; migrations to manage (Alembic). In return, no destructive rewrite between sprints, and flagged OCR fields can be structurally prevented from entering aggregates.

## Reconsider if
Corpus grows beyond what a single Postgres handles comfortably, or extraction schemas turn out highly heterogeneous per vendor.
