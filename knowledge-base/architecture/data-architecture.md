# Data Architecture — Source of Truth vs. Retrieval Index

Status: **Proposed**.

## Principle

> Canonical data (documents, pages, chunks text, extracted fields, provenance) lives in PostgreSQL. Vector and lexical indexes are **derived**: deleting them and re-running the index stage must restore them exactly.

## Lifecycle

```
Document ─► Page ─► Section (logical unit: header, line-items table, clause, totals, footer) ─► Chunk ─► Embedding
   │                                      │
   └──────────── (Sprint 3+) ─────────────┴─► extracted PO / Invoice / line items (typed, with confidence + provenance)
```

## What lives where

| Data | Store | Why |
|---|---|---|
| Raw file bytes | filesystem / object-store path (`storage_uri`), sha256 | Large, immutable; DB holds pointer + hash |
| Documents, pages, page text, OCR conf | PostgreSQL | Canonical, queryable, referential integrity |
| Chunk text + structural metadata (section, type, pages, parent) | PostgreSQL `chunks` | Chunks are canonical *units of citation*; chunking can be re-run and versioned |
| Embedding cache | Postgres `chunk_embeddings(chunk_id, embedding_model, dim, embedding real[])` | Expensive-to-recompute (API quota); keyed by model so we can A/B models |
| Vector index | Qdrant collection per embedding model (embedded local mode), point id = chunk_id | Derived; rebuilt from the cache with `reindex`; native payload filters + later sparse/RRF |
| Lexical index (BM25) | Built from `chunks.text` (in-memory `rank_bm25` or PG FTS/ParadeDB — decide Sprint 7) | Derived |
| Typed financial fields, line items, vendors | PostgreSQL relational tables (Sprint 3+) | Exact filtering/aggregation, constraints, `NUMERIC` money |
| Field-level confidence + bbox + extractor | PostgreSQL provenance table | Needed for flagging and "verify against source" |
| Mismatch findings | PostgreSQL | Auditable, re-computable |
| Golden sets, eval results | files in `evals/` (git) | Versioned with code; results as JSON artefacts |

## Vector-side metadata (filter keys)

Qdrant is a separate store, so filter keys **are denormalised into the point payload** (and kept in sync by the write-order rule in ADR-004). Payload per vector:
`chunk_id, document_id, document_type, document_number, page_start, vendor_id, section, chunk_type, pipeline_version, embedding_model`.

## Idempotency & versioning

- `documents.content_hash` unique → re-upload of identical bytes is a no-op (returns existing).
- `chunks.pipeline_version` / `ingestion_run_id`: changing chunker/normaliser version creates new chunks for affected docs; old ones are tombstoned in the same transaction as the new embeddings are written → incremental update without corpus rebuild.
- "Re-runnable from scratch": `scripts/ingest_all` truncates derived tables and rebuilds from `data/raw` (documents rows keyed by hash, so ids are stable).

## Hybrid-query data path

`SQL filter → set of document_ids → retriever(filter={document_id IN ...})`. Two stores, so the two steps can disagree only if the index is stale; the `is_active` payload flag and `reindex --verify` guard this.
