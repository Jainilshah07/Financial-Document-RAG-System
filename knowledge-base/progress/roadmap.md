# Roadmap (Proposed)

Refined from the brief's initial roadmap against Part D deadlines. **Changes and why:**

1. **Golden set + CI eval are due Week 4** (Part D), so the eval harness starts in Sprint 2, not Sprint 8. Sprint 8 becomes ablation/adversarial/regression hardening.
2. **Corpus generation is a hidden dependency** (no corpus supplied, ground truth needed for extraction/OCR/mismatch). Made explicit in Sprints 1–2.
3. **Structured extraction + SQL moved before BM25/hybrid.** The statement's core is structured vs. semantic routing; BM25 is an enhancement. BM25, hybrid and reranking merge into one retrieval-quality sprint (S7). *If you prefer the original order (BM25 at S3), it's a cheap swap — nothing depends on it.*
4. **OCR before router:** the router/hybrid tests need the full corpus incl. scanned docs queryable.
5. **PO/invoice mismatch detection** (an acceptance criterion) gets its own sprint, combined with the numeric verifier.

| Sprint | Theme | Key deliverables | Part D tie-in |
|---|---|---|---|
| **0** | Research & architecture | Approve ADRs 001–005, research notes, corpus strategy, eval strategy, env setup | — |
| **1** | Semantic RAG foundation | local Postgres + Qdrant embedded, Alembic base schema, `/upload`, `/ask` (semantic only), structure-aware chunker v1, embeddings, ChatPromptTemplate + configurable LLM, citations; ~20-doc seed corpus; Swagger demo | Ingestion pipeline (wk 2), `/ask` (wk 3) |
| **2** | Corpus & retrieval evaluation | Full synthetic generator (500+, ≥50 scanned, manifest, injected mismatches); golden set v0 + router set draft; Recall@K/P@K/MRR runner; chunking & embedding comparison; top-K/MMR/metadata filters; declare latency & ₹ budgets | Golden set + CI eval skeleton (wk 4), budget declared |
| **3** | Structured extraction + SQL | Extractors for born-digital docs, validators (Σ checks), vendors/PO/invoice tables, query-plan compiler, SQL arithmetic, field provenance | FR-1, FR-3 |
| **4** | OCR + confidence | Page triage, OCR engine bake-off, per-field confidence, threshold calibration, flagging, scanned set into the store | FR-4, FR-5 |
| **5** | Query router + hybrid | Router (LLM + rules), routing eval on 40 Qs, hybrid orchestration (SQL → filtered retrieval), unified `/ask` | FR-2, FR-6, NFR-1/2 |
| **6** | Verification + mismatches | Numeric answer verifier, PO↔invoice matcher, mismatch report endpoint | FR-7 |
| **7** | Lexical / hybrid / rerank | BM25, RRF, reranker, context selection, dedup-with-attribution | ablation inputs |
| **8** | Eval hardening | 10 adversarial Qs, regression gate in CI, ablation table, end-to-end eval | Ablation (wk 8), CI gate |
| **9** | Productionisation | Latency/₹ measurement, caching, ANN tuning, concurrency, observability, Docker finalisation, 2-page writeup | Budget (wk 9), writeup |

Each sprint ends with: updated `progress/sprint-XX.md`, ADR updates, tests, and a "how to test it" note. Only one sprint is worked on at a time.

## Sprint 0 recommended scope → see `sprint-00.md`
