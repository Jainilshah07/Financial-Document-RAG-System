# Data Model (Proposed)

SQLAlchemy 2.0 declarative models + Alembic migrations. Auto-increment integer PKs (identity columns starting at 1; decided 2026-10-08 for readability in citations), `created_at/updated_at` on all tables. Money = `NUMERIC(18,2)` + `currency CHAR(3)`; never float. Tables are introduced **only in the sprint that needs them**.

## Introduced in Sprint 1 (semantic foundation)

| Table | Key columns | Notes |
|---|---|---|
| `ingestion_runs` | id, started_at, finished_at, pipeline_version, status, stats JSONB | One per upload or batch; ties derived rows to the code that made them |
| `documents` | id, `content_hash` UNIQUE, filename, storage_uri, mime, doc_type (`purchase_order`\|`invoice`\|`unknown`), doc_number NULL, page_count, status_detail NULL, is_scanned, status (`ingested`\|`failed`\|…), latest_run_id | `doc_type`/`doc_number` start nullable; filled by classifier/extractor later. Kept here (not in a typed table) because retrieval filters need them early |
| `document_pages` | id, document_id, page_number, text, text_source (`native`\|`ocr`), ocr_mean_confidence NULL, UNIQUE(document_id, page_number) | Page = unit of citation; OCR confidence column present from day 1 (nullable) to avoid a later migration |
| `chunks` | id, document_id, chunk_index, page_start, page_end, section NULL, chunk_type (`header`\|`table`\|`clause`\|`text`\|`footer`), text, token_count, parent_chunk_id NULL, content_hash, pipeline_version, run_id, is_active, meta JSONB | Canonical units of citation. `parent_chunk_id` supports parent-child without committing to it |
| `chunk_embeddings` | chunk_id FK, embedding_model, `input_hash` (sha256 of exact embedded text), dim, `embedding REAL[]`, PK(chunk_id, embedding_model), index(embedding_model, input_hash) | **Embedding cache**, looked up by `(embedding_model, input_hash)` so identical text is never re-embedded (API quota is scarce), not the search index. The search index is a Qdrant collection built from this table (ADR-004). Changing model = new rows, not a migration |

Justification of *not* adding more now: no vendor/PO/invoice tables until extraction exists (S3); adding empty tables invites speculative design.

## Introduced in Sprint 3 (structured extraction)

| Table | Key columns |
|---|---|
| `vendors` | id, canonical_name, gstin NULL UNIQUE, normalised_name, `vendor_aliases` (separate small table: vendor_id, alias) |
| `purchase_orders` | id, document_id UNIQUE, po_number, vendor_id, po_date, currency, subtotal, tax_total, grand_total, delivery_terms_text NULL, payment_terms_text NULL, status |
| `po_line_items` | id, po_id, line_no, description, quantity, unit, unit_price, line_total, tax_rate |
| `invoices` | id, document_id UNIQUE, invoice_number, vendor_id, po_id NULL, po_number_ref (as written), invoice_date, due_date, currency, subtotal, tax_total, grand_total |
| `invoice_line_items` | same shape as `po_line_items`, + `po_line_id` NULL |
| `field_extractions` | id, document_id, entity_table, entity_id, field_name, raw_text, normalised_value, confidence, source_page, bbox JSONB NULL, extractor, is_flagged, flag_reason | **Provenance + confidence per field.** Typed columns hold trusted values; flagged fields are NULL in the typed column and visible here — so SQL aggregates cannot silently use a doubtful number |

Why separate PO/invoice tables rather than one `financial_documents`: different keys, different relationships (invoice→PO), different mismatch logic; line-item shapes diverge. Shared columns are cheap to duplicate.

## Introduced in Sprint 6 (mismatch)

`mismatches`: id, invoice_id, po_id NULL, type, field, expected, actual, delta, severity, detected_at, run_id. Recomputable (derived) — truncate-and-rebuild is safe.

## Deliberately absent / deferred

- `users`, auth: out of scope.
- `query_log`: structured logs first; table only if eval/budget reporting needs it (S9).
- Section as its own table: `chunks.section` string is enough until a golden question needs section-level entities.

## Entity sketch

```
ingestion_runs 1─* documents 1─* document_pages
                       │1─* chunks 1─* chunk_embeddings
                       │1─1 purchase_orders 1─* po_line_items        (S3)
                       │1─1 invoices ─*─1 purchase_orders            (S3)
                       │ *  field_extractions (provenance)           (S3/S4)
vendors 1─* purchase_orders / invoices     invoices 1─* mismatches   (S6)
```
