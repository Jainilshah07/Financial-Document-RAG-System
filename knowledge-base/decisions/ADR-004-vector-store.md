# ADR-004 — Vector store

**Status:** **Accepted 2026-10-08 — Qdrant (embedded local mode), user-confirmed.** Supersedes the 2026-10-07 acceptance of pgvector. · **Date:** 2026-10-06

## Context
PS2's defining workflow is *SQL filter → semantic retrieval over the filtered set*, plus later BM25, metadata filters and mismatch joins. PostgreSQL is mandatory from Sprint 3 as the canonical store. Scale: a few thousand chunks — ANN performance is irrelevant; filter semantics and hybrid support matter.

Environment findings (2026-10-08): the user has PostgreSQL 18 running locally **without pgvector**; there is no official Windows installer for pgvector (needs C++ build tools or community binaries). Docker Desktop exists but costs ~1–2 GB of an 8 GB machine.

## Options

| Option | For | Against |
|---|---|---|
| pgvector | one system, transactional hybrid path | not installable on the user's Postgres without a Windows build; otherwise needs Docker |
| Postgres only, `real[]` + numpy cosine | simplest, zero extra deps, exact | no native hybrid/sparse support; BM25/RRF hand-built in Sprint 7 |
| **Qdrant** | payload filtering (`document_id` any-of), native sparse vectors + RRF fusion (Sprint 7 head start), **embedded local mode via pip — no server/Docker**, identical API to server mode | second store → consistency to manage; local mode is documented for prototyping/small data (≈ tens of thousands of points — verify against current docs); single-process access to the local path |
| Chroma embedded | pip-only | weaker hybrid story; no advantage over Qdrant for us |
| FAISS | fast | no filtering/persistence layer |

## Decision
**Qdrant behind a `VectorIndex` protocol**, run in **embedded local mode** (`QdrantClient(path=...)`) for development and tests (`:memory:`), switchable by config to a server (`QDRANT_URL`, Docker) without code changes.

**Division of responsibility:**
- **PostgreSQL = canonical**: documents, pages, chunks (text, metadata), later structured tables.
- **`chunk_embeddings` stays in PostgreSQL** (`real[]`, keyed by `(chunk_id, embedding_model)`) as the **embedding cache**: Gemini's free tier (~1k requests/day) makes re-embedding expensive, so vectors are never recomputed when Qdrant is rebuilt.
- **Qdrant = derived retrieval index**, rebuildable from Postgres alone (`scripts/reindex`). Collection per `embedding_model` (+ dim). Point id = `chunk_id`.
- **Payload per point** (filter keys): `chunk_id, document_id, document_type, document_number, page_start, vendor_id, section, chunk_type, pipeline_version, embedding_model, is_active`.
- **Hybrid route**: SQL → `document_ids` → Qdrant filter `document_id ∈ ids`.
- **Consistency rule**: Postgres is written first; a chunk is `is_active` only after its point is upserted; a periodic `reindex --verify` compares counts/ids. Deactivated/deleted chunks are deleted from Qdrant by id.

## Trade-offs
Extra store and one more thing to keep in sync (mitigated by "index is rebuildable" and the verify command); in return, native hybrid search later and no Postgres extension on Windows.

## Reconsider if
Local mode proves slow/unstable (switch to Qdrant server via Docker — config only), the corpus grows well beyond local-mode limits, or sync bugs outnumber the benefits (fall back to Postgres `real[]` + numpy; the protocol makes it a one-file swap).
