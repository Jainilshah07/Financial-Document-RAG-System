# System Architecture

Status: **Proposed** (pending user approval). Principle: canonical data in PostgreSQL; every retrieval index is derived and rebuildable; every answer traces to document + page.

## 1. Big picture

```
                         INGESTION (offline, idempotent, incremental)
 PDF/image ─► register ─► page triage ─► text acquisition ─► normalise ─► segment ─┬─► chunk ─► embed ─► index
 (sha256)     (dedupe)    digital/scan   native | OCR(+conf)  (₹, dates,         │
                                                               whitespace)        └─► extract fields/tables ─► validate ─► relational tables
                                                                                        (Sprint 3+)            (Σ checks, conf threshold)
                                                                                                                  └─► PO↔Invoice matcher ─► mismatches

                         QUERY (online)  POST /ask
 question ─► Router ─┬─ structured ─► QueryPlan(JSON) ─► SQLAlchemy ─► rows ──────────────┐
             (LLM +  ├─ semantic   ─► Retriever(dense│bm25│hybrid│rerank) ─► chunks ─────┤► Answer composer ─► Verifier ─► response
              rules) └─ hybrid     ─► QueryPlan ─► doc_ids ─► Retriever(filter=doc_ids) ──┘   (LLM phrases;       (every number ∈ result set;
                                                                                               numbers injected)    citations resolve)
```

## 2. Module layout (final, refined from the brief; folders created only when their sprint starts)

```
app/
  api/            FastAPI routers (thin: parse → call service → serialise). No business logic.
  core/           settings (pydantic-settings), logging (structlog/JSON), DI wiring, errors
  db/             SQLAlchemy 2.0 models, session, repositories;  alembic/ at repo root
  schemas/        Pydantic request/response + domain DTOs (QueryPlan, Citation, ...)
  ingestion/      pipeline stages: register, triage, parse, ocr (S4), normalise, segment, chunk, embed, index
  extraction/     field/table extractors, validators, confidence, matcher (S3+)
  retrieval/      Retriever protocol + dense, bm25, hybrid(RRF), rerank decorators, filters
  routing/        router, QueryPlan compiler (plan → SQL), hybrid orchestrator (S5)
  llm/            LangChain chat-model factory, prompts (ChatPromptTemplate), answer composer, verifier
  services/       use-case orchestration: IngestionService, AskService
evals/            golden sets, router set, metrics, runner, CI entrypoint  (outside app/: not shipped)
tests/unit, tests/integration
scripts/          corpus generator, ingest-all, eval runner wrappers
data/raw|processed|sample   (git-ignored except sample)
```
Dependency rule: `api → services → {ingestion, retrieval, routing, llm, extraction} → db/schemas/core`. LangChain is confined to `llm/` and thin adapters in `retrieval/` (embeddings/vector store); domain code depends on our own protocols.

## 3. Key components

| Component | Responsibility | Sprint |
|---|---|---|
| Registry | sha256 + pipeline_version idempotency, ingestion_runs, incremental re-ingest | 1 |
| Triage | per-page: usable text layer? else OCR | 1 (detect) / 4 (OCR) |
| Parser | PyMuPDF/pdfplumber text + layout blocks + tables | 1 |
| Chunker | structure-aware (ADR-002) | 1 |
| Embedder | `Embeddings` interface, model recorded per vector | 1 |
| Index | pgvector (ADR-004) behind `VectorIndex` protocol | 1 |
| Retriever | `retrieve(query, filters, k) -> list[Hit]` | 1 |
| Answer chain | ChatPromptTemplate → configurable LLM; LCEL, no LangGraph | 1 |
| Extractor + validators | typed rows with per-field confidence & provenance | 3–4 |
| Router | structured / semantic / hybrid + plan | 5 |
| Verifier | numbers-in-answer ⊆ numbers-in-result; citations resolvable | 5–6 |
| Matcher | PO↔invoice mismatch detection | 6 |
| Eval harness | retrieval metrics, router accuracy, e2e, regression gate | 2 → 8 |

## 4. API

| Endpoint | Purpose | Sprint |
|---|---|---|
| `POST /upload` | multipart PDF/image → ingestion run → document ids, status | 1 |
| `POST /ask` | `{question, top_k?, filters?}` → `{answer, route, citations[{document, page, chunk_id/row_id, snippet}], computed?: {sql_ref, rows}, flags[], timings}` | 1 (semantic) → 5 (routed) |
| `GET /documents`, `GET /documents/{id}` | inspection, ingestion status | 1 |
| `GET /health` | liveness + DB | 1 |

`/ask` response always includes `route` and `trace_id` from Sprint 1 so later routing slots in without breaking the contract.

## 5. Cross-cutting

- **Config**: pydantic-settings, `.env`; providers/models/thresholds are settings, not code.
- **Logging**: structured JSON with `trace_id`, route, retrieval k, latency per stage, token counts (feeds ₹/query).
- **Testing**: unit (chunker, normaliser, RRF, plan compiler), integration (Postgres via Docker, API via TestClient, LLM faked), eval (real LLM, run in CI with cached fixtures where possible).
- **Migrations**: Alembic only; no `create_all` outside tests.
- **Cost accounting**: every LLM/embedding call logs tokens → ₹ (Part D budget report).

## 6. Explicitly *not* doing (until demonstrated need)

LangGraph/agents, microservices, a message queue, a separate vector DB server, fine-tuned models, a UI.
