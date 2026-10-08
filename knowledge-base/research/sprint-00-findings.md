# Sprint 0 Findings (spikes + research)

Spike code was throwaway (scratchpad, not in repo). Dates: 2026-10-07. Machine: Windows, Python 3.12.

## Spike A — Do embeddings separate numbers? (Gemini `gemini-embedding-001`, 768-d)

| Pair | Cosine similarity |
|---|---|
| `Rs. 5,00,000` vs `Rs. 4,99,000` | 0.955 |
| `Rs. 5,00,000` vs `Rs. 5,00,001` | 0.966 |
| `Rs. 5,00,000` vs `Rs. 50,000` (10× smaller) | **0.966** |
| `Rs. 5,00,000` vs `Rs. 9,00,000` | 0.940 |
| payment clause vs delivery clause (different meaning) | 0.830 |

**Reading:** all amounts sit at 0.94–0.97 — no usable ordering; a value 10× smaller is *closer* than one 1 % smaller. This confirms the problem statement's claim empirically: numeric filtering must be SQL. The same model does separate meaning (query "when do the goods have to arrive?" scored 0.786 vs the delivery clause and 0.665 vs the payment clause), so it is fit for the semantic side. Latency: 7 texts in one batch ≈ 2 s.

## Spike B — Parsing the 6 sample documents (PyMuPDF 1.28, pdfplumber 0.11)

| File | Finding |
|---|---|
| `PO_*.png` (×2) | No text layer → OCR required (Sprint 4). Excluded from Sprint 1 |
| `PO_23781.pdf` | Text layer has **labels only**; all values are in **99 AcroForm widgets** (52 filled), readable via `page.widgets()`. Placeholders like `<Company Name>`, `nn/dd/yyyy` are present as values → must be treated as missing |
| `PO_3600031165_SARS.pdf` | 2 pages: p1 structured tables (vendor, delivery, line item), p2 numbered T&C (≈3k chars). Tables extract as label/value grids; multi-line cells merge several values (vendor block) — need cell-aware parsing, not row-text |
| `PO_Sample.pdf` | Empty template (labels only, blank values) — useful as negative test ("no data") |
| `PO_Sample_123456.pdf` | Clean line-item table (item, desc, qty, unit price, total) extracted correctly by both libs |

**Decisions:** PyMuPDF = primary (text, blocks, widgets, `find_tables`, rasterisation for OCR); pdfplumber = secondary table cross-check. Page triage must consider *form fields* and *empty templates*, not just "has text". Both libs differ on table boundaries → keep raw page text as canonical and treat table parsing as an extractor concern (Sprint 3), not a parsing concern.

## Spike C — LLM / API availability

- **Groq** (key valid): current models include `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` (plus audio/guard models). `llama-3.3-70b-versatile` is **no longer listed**. Both gpt-oss models returned a **correct JSON query plan** (route, vendor, Jul–Sep date range for Q2, 500000 min, currency) in ≈0.9 s with `response_format=json_object`. Caveat: the model assumed `INR` and the hybrid question was routed `structured` — the router needs explicit hybrid guidance and few-shot examples (tracked in Sprint 5).
- **Gemini** (key valid): chat models available incl. `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3.5-flash`. Embeddings working. LLM rate limits not measured.

## Research notes (condensed; web-verified where marked ✔)

**Embeddings.** ✔ `gemini-embedding-001`: 3072-d default, MRL truncation (768/1536/3072 recommended), 2048-token input, free tier ≈100 RPM / 30k TPM / 1k RPD ([Google](https://developers.googleblog.com/en/gemini-embedding-available-gemini-api/)). ✔ NVIDIA `nv-embedqa-e5-v5`: 1024-d, finite trial credits ≈40 RPM. Use `RETRIEVAL_DOCUMENT` for chunks, `RETRIEVAL_QUERY` for questions. Implication of 1k RPD: **batch many texts per request** and cache by chunk hash.

**Chunking.** For 1–3-page POs most clauses are < 300 tokens; fixed/recursive splitters would mostly produce page-sized or arbitrary cuts. Structure-aware split on layout blocks/numbered clauses + contextual prefix is the v1; compare against recursive in Sprint 2 (ADR-002). Specific to our samples: SARS T&C is a numbered list (1–9) with nested dashes → natural clause boundaries; label/value grids (vendor block) should become key-value text, not raw table markdown.

**Vector store.** Qdrant embedded accepted (ADR-004, supersedes pgvector: user's Postgres 18 has no pgvector). At a few thousand chunks, exact search is fast; ANN tuning is Sprint 9.

**Retrieval.** Dense for paraphrase; BM25 for ids/names (PO `3600031165`, vendor `EMPIRE TODAY ENTERPRISE`); RRF to fuse; MMR only if boilerplate duplication harms results; rerank last. Sprint 7.

**OCR.** Two PNG samples are clean template renders (good for first tests; real scans will be harder). Candidates and per-field confidence plan in ADR-005; decide in Sprint 4 by bake-off on these + degraded variants.

**Evaluation.** See `evaluation/evaluation-strategy.md`.

## Risks surfaced
1. Real POs are heterogeneous (form-PDF, ZAR/USD, empty templates) → extraction must be per-field validated, not template-assumed.
2. Gemini free tier daily request cap → batching + caching are mandatory design elements, not optimisations.
3. LLM routing of hybrid questions is not automatic (see Spike C) → few-shot + rules + routing eval.
4. Groq model lineup changes (llama-3.3 gone) → model id stays in config, never in code.
