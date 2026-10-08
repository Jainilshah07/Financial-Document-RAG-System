# Prerequisites

Checked on this machine (2026-10-06): Python 3.12.7 ✅ · Docker 29.7.2 ✅ · Git ✅ · Node ✅ · PostgreSQL 18 service running locally ✅ (no pgvector — not needed, ADR-004) · **Tesseract ✗**.

## Status (2026-10-07)
✅ Groq key in `.env` (⚠ currently named `OPENAI_API_KEY`; rename to `GROQ_API_KEY`) · ✅ Git repo · ✅ Docker Desktop running · ✅ 6 sample POs in `dataset/` · ✅ Parts A/B waived · ⏳ Tesseract (not needed before Sprint 4) · ⚠ `.gitignore` only contains `.env` — extend (`.venv/`, `__pycache__/`, `data/`, `*.pyc`, `.pytest_cache/`, docker volumes).

## Needed for Sprint 0–1
| Item | Why | Action |
|---|---|---|
| **Groq API key** | LLM answers (ADR-005). Embeddings are local, so no OpenAI key needed | In `.env` as `GROQ_API_KEY`. Never paste in chat or commit |
| PostgreSQL 18 (local) | canonical store | Create DB `finrag` + user; put `DATABASE_URL` in `.env` (never in chat) |
| Docker Desktop | **not needed until Sprint 9** (containerising the API; optional Qdrant server) | — |
| Python 3.12 venv | isolation | I'll create `.venv` in Sprint 1 |
| **Gemini API key** (Google AI Studio, free) | Embeddings (ADR-003 Update 2) | `GEMINI_API_KEY` in `.env` |

## Needed later
| Item | Sprint | Notes |
|---|---|---|
| Tesseract OCR (Windows installer, UB-Mannheim build) | 4 | add to PATH; or we use PaddleOCR/docTR via pip |
| GitHub account + Actions | 2/8 | CI eval pipeline; needs OpenAI key as repo secret (or cached/mocked LLM calls in CI) |
| Optional: Azure Document Intelligence / AWS Textract trial | 4 | only if comparing hosted OCR |
| Optional: a local embedding model download (~100–500 MB) | 2 | for the ADR-003 benchmark |

## Not needed
GPU, cloud hosting, LangSmith (optional, nice for tracing), any vector DB account.
