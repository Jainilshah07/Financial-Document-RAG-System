# Sprint 1 — Semantic RAG Foundation (IN PROGRESS — one task at a time, user-paced)

**Objective:** a working, demonstrable Semantic RAG API in Swagger: upload PDFs → ask questions → cited answers. Foundation (DB, migrations, interfaces) built to carry Sprints 2–9.

## Scope (in)
1. Repo scaffold: `pyproject.toml`, `app/` layout (only folders used now), `.env.example`, extended `.gitignore`, Alembic against the user's local PostgreSQL 18 (dedicated `finrag` database/user; `DATABASE_URL` in `.env`). No Docker needed for Sprint 1.
2. Settings (pydantic-settings), structured JSON logging with `trace_id`.
3. DB models + first Alembic migration: `ingestion_runs`, `documents`, `document_pages`, `chunks`, `chunk_embeddings` (see `data-model/schema.md`).
4. Ingestion pipeline (idempotent by sha256): register → parse (PyMuPDF text + AcroForm widgets, placeholder filtering) → normalise → structure-aware chunker v1 + contextual prefix → batch embed (Gemini, 768-d, cached by chunk hash, backoff) → index (Qdrant embedded, collection per model; vectors cached in Postgres `chunk_embeddings`).
5. Retrieval: `VectorIndex` protocol + `QdrantVectorIndex` (+ `reindex` script), `Retriever` protocol + `DenseRetriever`; filters on document ids/type.
6. LLM: LangChain `ChatPromptTemplate` + config-selected chat model (default Groq `openai/gpt-oss-120b`; Gemini selectable); prompt forces grounded, cited answers and "not found" when context lacks the answer.
7. API: `POST /upload`, `POST /ask` (returns answer, `route:"semantic"`, citations[document, page, chunk_id, snippet], timings, trace_id), `GET /documents`, `GET /health`.
8. Tests: unit (normaliser, chunker, placeholder filter, RRF-free retriever with fake embeddings), integration (local Postgres test DB, in-memory Qdrant, API TestClient, fake LLM/embedder).
9. Docs: ADR updates, `sprint-01.md` completion report, README run instructions.

## Out of scope (do NOT implement)
OCR/PNG ingestion, SQL/structured extraction, router, BM25/hybrid/rerank, eval harness, vendors/PO/invoice tables.

## Corpus for the demo
4 PDFs in `dataset/` (the 2 PNGs are skipped with a clear "needs OCR" status; `PO_Sample.pdf` empty template tests the "no content" path).

## Demo script (acceptance for the sprint)
1. `alembic upgrade head` → `uvicorn app.main:app`.
2. Swagger: upload the 4 PDFs; re-upload one → no duplicate.
3. `/ask` "What are the payment terms?" → cites the right doc/page; "What is the delivery date for PO 3600031165?" → cited; unanswerable question → "not found in documents"; ask a numeric-sum question → documented limitation (route not available yet), does **not** guess.
4. `pytest` green.

## Risks
Gemini daily request cap (mitigated by batching + cache); Qdrant local mode allows a single process on the data path (stop the API before running scripts, or use `:memory:` in tests); fillable-form extraction edge cases.

## Task order
scaffold → DB/migrations → parser+normaliser (TDD) → chunker (TDD) → embedder+index → retriever → LLM chain → API → integration tests → docs.


## Task log
| # | Task | Status |
|---|---|---|
| 1 | Scaffold: pyproject, .venv, .gitignore, .env.example, `app/main.py` + `/health`, first test, `data/sample/` | ✅ 2026-10-08 — 1 test passing, ruff clean |
| 2 | Settings (pydantic-settings) + structured logging | ✅ 2026-10-08 |
| 3 | DB models + Alembic first migration | ✅ 2026-10-08 — 5 tables migrated to `finrag`; 14 tests passing (5 integration, isolated schema) |
| 4 | Parser + normaliser (PyMuPDF text, AcroForm widgets, placeholder filter) | ✅ 2026-10-08 — verified on samples by user (PNGs → needs_ocr; placeholders stripped; form text de-duplicated) |
| 5 | Structure-aware chunker v1 + embedding-input prefix | ✅ 2026-10-08 — verified on samples by user |
| 6 | Embedder (Gemini, batching, backoff), Qdrant index, Postgres embedding cache | code written 2026-10-08 — awaiting user check (`scripts/try_semantic_search.py`) |
| 7 | Ingestion service (register → parse → chunk → embed → index) + `POST /upload`, `GET /documents` | code written 2026-10-08 — awaiting user check (Swagger) |
| 8 | Retrieval + LLM chain (ChatPromptTemplate, Groq) + `POST /ask` with citations | next |
