# ADR-005 — Stack choices; how structured questions are executed

**Status:** Accepted 2026-10-07. LLM default: Groq `openai/gpt-oss-120b` (verified live, correct JSON plan in ≈0.9 s); Gemini `gemini-2.5-flash` selectable. Embeddings use Gemini (ADR-003) · **Date:** 2026-10-06

## Stack (provisional)
Python 3.12 · FastAPI · Pydantic v2 / pydantic-settings · SQLAlchemy 2.0 + Alembic · PostgreSQL 18 (local) + Qdrant (`qdrant-client`, embedded) · LangChain (`langchain-core`, `langchain-openai`) used for **LLM + prompt + embeddings abstraction only** · PyMuPDF (text/layout/rasterise; AGPL — fine for this learning project, pdfplumber as alternative for tables) · pytest · Docker Compose · structlog. No LangGraph.

**LLM provider (update 2026-10-07): Groq** via `langchain-groq`, selected by config (`LLM_PROVIDER`, `LLM_MODEL`); model id to be verified against Groq's current list in Sprint 0 (needs reliable JSON/tool output for the query plan). Watch free-tier rate limits for eval runs/CI, and Groq per-token pricing for the ₹/query report. `.env` key should be named `GROQ_API_KEY`.

Why LangChain only at the edges: user wants provider switch via config and `ChatPromptTemplate`; domain logic (chunking, routing, plans, verification) stays plain Python for debuggability and learning.

## Structured-question execution (supports FR-3)
**LLM → validated JSON `QueryPlan` → code compiles to SQL (SQLAlchemy Core) → DB computes → answer text built from result rows → verifier checks every number in the answer exists in the result set.**

Alternatives: (a) free-form text-to-SQL — flexible, but injection/hallucinated-column risk and harder to audit; (b) fixed templates only — safest, too rigid for 40 varied questions. Chosen middle path: a small, closed plan vocabulary (filters on vendor/date/amount/doc_type, group-by, `sum|count|avg|min|max|list`) that can grow when the golden set demands.

## OCR (decided in Sprint 4, listed here for awareness)
Candidates: Tesseract (TSV word confidences, free, needs install), PaddleOCR / docTR (better on some scans, heavier), hosted Azure Document Intelligence / Textract (field-level confidence, cost). Field confidence = aggregate of word confidences (min/mean) combined with validation checks (Σ lines = subtotal). Vision-LLM extraction lacks calibrated confidence → not primary.

## Reconsider if
A dependency (PyMuPDF licence, Qdrant local mode) blocks progress.
