# ADR-004 — Vector store

**Status:** **Accepted 2026-10-07** (user: "whatever suits best" → pgvector) · **Date:** 2026-10-06

## Context
The brief says "Chroma initially if justified." PS2's defining workflow is *SQL filter → semantic retrieval over the filtered set*, plus later BM25, metadata filters and mismatch joins. PostgreSQL is mandatory by Sprint 3 regardless. Scale: 500+ docs ≈ a few thousand chunks — ANN performance is irrelevant; correctness and filter semantics matter.

## Options

| Option | For | Against |
|---|---|---|
| **pgvector in PostgreSQL** | one system; hybrid path = a single transaction (SQL filter + vector rank); no metadata duplication/drift; chunks, embeddings and provenance joinable; exact or HNSW search; BM25-ish via FTS later | Docker/Postgres needed from Sprint 1 (already installed Docker; no local psql); fewer vector-specific features; tutorials less common |
| Chroma (embedded) | zero setup, fastest to first demo; `where` filters incl. `$in` on doc ids | second store → duplicated metadata, ids must be synced, hybrid path = two systems; no relational joins; sprint-4 migration or permanent dual-store |
| Qdrant / Weaviate / Pinecone | rich filtering, hybrid built in | extra service/cost; unjustified at this scale |
| FAISS | fast, simple | no metadata/filter story, no persistence layer — we'd rebuild what Postgres gives |

## Provisional decision
**pgvector in the same PostgreSQL**, accessed through a `VectorIndex` protocol (SQLAlchemy + `pgvector` type; LangChain `PGVector` adapter optional). Docker Compose with the `pgvector/pgvector` image. Chroma remains a valid Sprint-1 *fallback* if Docker/Postgres friction is unacceptable — the protocol makes it a ~1-file swap, at the cost of a later migration.

## Trade-offs
Slightly slower start (Compose + Alembic from day 1) vs. avoiding a guaranteed re-platform and a consistency problem on the hybrid route. Fixed cost, paid once.

## Reconsider if
Corpus grows to millions of chunks, or vector-specific features (multi-vector, sparse-native hybrid) become necessary.
