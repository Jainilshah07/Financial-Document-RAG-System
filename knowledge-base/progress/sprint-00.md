# Sprint 0 — Research & Architecture

**Status:** Proposed (not started) · **Goal:** turn the `Proposed` ADRs into evidence-backed `Accepted` ones and unblock Sprint 1. No application code, except throwaway spikes under a scratch folder.

## Scope

1. **Resolve blockers** (`requirements/ambiguities.md`): Parts A/B, corpus approach, Postgres-vs-Chroma, hosted-embedding OK, fiscal quarter.
2. **Research notes** in `research/` (short, decision-oriented, with current sources; verify model names/prices live):
   - chunking (fixed, recursive, sentence, structure-aware, semantic, parent-child) on *our* document shapes
   - embeddings (OpenAI small/large vs BGE/E5/GTE/M3): dims, cost, numeric handling
   - vector stores (pgvector vs Chroma vs Qdrant) incl. Windows/Docker setup
   - retrieval: dense, BM25, hybrid, RRF, MMR, reranking
   - OCR engines + confidence extraction (Tesseract TSV, PaddleOCR, docTR, hosted)
   - evaluation: retrieval metrics, router accuracy, numeric-answer checking, LLM-judge pitfalls
3. **Two small spikes** (throwaway, results recorded):
   - *Spike A — embeddings vs numbers:* embed ₹5,00,000 vs ₹4,99,000 style strings; record cosine similarity to demonstrate/quantify the problem statement's claim.
   - *Spike B — parsing:* run PyMuPDF/pdfplumber on 3 hand-made PO/invoice PDFs; check text order, table extraction, layout blocks.
4. **Corpus design:** document templates (≥4 vendor layouts × PO/invoice), fields, number formats, mismatch injection catalogue, manifest schema, scan-degradation recipe.
5. **Eval strategy:** golden-set format (question, class, expected answer, expected doc/page/chunk, adversarial type), metrics, regression policy → `evaluation/evaluation-strategy.md`.
6. **Finalise** ADR-001…005 (Accepted or revised), write `progress/sprint-01.md` plan with task list, repo scaffolding checklist.

## Exit criteria
- ADRs 001–005 `Accepted`; all ★ questions answered.
- Corpus design + eval strategy documents exist.
- Sprint 1 task list agreed.
- Prerequisites installed (below).

## Research questions to answer (checklist)
- What chunk size/overlap works for 1–3-page POs? (hypothesis: whole clauses, ≤400 tok)
- Does a contextual prefix help differentiate boilerplate across POs?
- Which embedding model, at what cost per 1k docs / per query?
- pgvector HNSW vs exact scan at 5k chunks (expect: exact is fine)?
- How is Indian number formatting (`5,00,000`, `₹`, `Rs.`, `lakh`) normalised, and how does BM25 tokenise it?
- How do OCR word confidences map to field confidence? How do we calibrate a threshold?
- What mismatch types are realistic, and how will the generator inject each?
