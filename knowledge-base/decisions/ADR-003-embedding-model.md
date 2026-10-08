# ADR-003 — Embedding model

**Status:** Accepted 2026-10-07 — Gemini `gemini-embedding-001` @768-d (verified live; Spike A confirmed it separates meaning, not numbers). Re-benchmark vs local BGE in Sprint 2 · **Date:** 2026-10-06

## Context
Embeddings serve only the semantic/text side (clauses, terms). They are known to be weak on numbers, which is why SQL exists. Corpus is small (thousands of chunks), English, short chunks. Need: good clause-level semantic quality, cheap (₹/query budget), swappable, compatible with Qdrant (any dimension; smaller is faster/cheaper).

## Candidates

| Option | Dim | Hosting | Notes |
|---|---|---|---|
| OpenAI `text-embedding-3-small` | 1536 (shortenable) | hosted | cheap, strong baseline, no local GPU; we already need an OpenAI key |
| OpenAI `text-embedding-3-large` | 3072 (shortenable) | hosted | better, ~6× cost; likely overkill for short English clauses |
| BGE-small/base, E5, GTE (sentence-transformers) | 384–768 | local | free per call, reproducible offline, CPU-OK at this scale; CPU latency at ingest, model download |
| BGE-M3 | 1024 | local | multilingual + sparse/dense; heavier; relevant only if multilingual becomes in scope |

## Update 2 2026-10-07 — user prefers a hosted free API (supersedes the local-model update below)
User: local model is not a task requirement; use a free external API. Researched (web, 2026-10-07):
- **Gemini `gemini-embedding-001`** — free tier ≈ 100 RPM, 30k tokens/min, 1k requests/day; default 3072-d, Matryoshka-truncatable (768/1536/3072 recommended); 2048-token input. Paid fallback ≈ $0.15/1M tokens.
- **NVIDIA NIM `nv-embedqa-e5-v5`** — 1024-d, but trial is a finite credit pool (≈1000–5000) at ≈40 RPM; credits would run out under repeated eval re-embedding.

**Provisional decision: Gemini `gemini-embedding-001` at 768 dimensions** (small vectors, fits pgvector, MRL-recommended size), behind the `Embedder` interface. Mitigations for the 30k TPM cap: batch requests, throttle + exponential backoff, and **cache by `chunks.content_hash` + model** so re-runs/evals never re-embed unchanged chunks. Note task type (`RETRIEVAL_DOCUMENT` vs `RETRIEVAL_QUERY`) must be set correctly. Privacy: free-tier data may be used by the provider — fine for public/sample documents, **revisit before any real financial data**. Local BGE remains the offline fallback.

## Update 1 2026-10-07 — (superseded by Update 2)
The user's LLM provider is **Groq**, which does not offer an embeddings API. Rather than add a second paid vendor, embeddings run **locally**: ~0 cost, no data leaves the machine, reproducible, and corpus scale (thousands of chunks) is trivial for CPU.

**Provisional decision:** a local BGE model (`bge-small-en-v1.5`, 384-d, or `bge-base-en-v1.5`, 768-d — pick in Sprint 1 by a quick check on the sample docs, full benchmark in Sprint 2) through an `Embedder` interface. Runtime: `fastembed` (ONNX, small install, no PyTorch) preferred over `sentence-transformers` (pulls PyTorch, ~GBs on Windows) unless fastembed lacks a needed model. **Model name stored with every vector** (`chunk_embeddings.embedding_model`), so switching (incl. to OpenAI) is a re-embed, not a migration.

*(Original leaning was OpenAI `text-embedding-3-small`; kept as the hosted comparison candidate.)*

## Trade-offs
Hosted: network dependency, per-token cost, data leaves the machine (acceptable for synthetic corpus; **revisit for real financial data**). Local: free, private, slower to set up.

## Reconsider if
Benchmark shows local ≥ hosted; data-privacy constraint appears; budget report shows embeddings dominate cost (unlikely: queries embed a single short string).
