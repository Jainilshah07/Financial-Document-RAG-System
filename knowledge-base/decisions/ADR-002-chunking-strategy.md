# ADR-002 — Chunking strategy

**Status:** Accepted as *v1 baseline* 2026-10-07; sizes/overlap to be validated by the Sprint 2 comparison (not final) · **Date:** 2026-10-06

## Context
Corpus = short (1–3 page) POs/invoices with: header block (numbers, dates, parties), line-item tables, totals, terms/clauses (delivery, payment, warranty), footers. Facts that must stay together: `doc number + vendor + clause text`; a table row's cells; a clause and its heading. Boilerplate T&C repeats across POs. Numbers are *not* answered by retrieval (SQL does that), so chunks mainly serve **semantic/text questions** and hybrid answers.

## Options compared

| Strategy | Pros | Cons for this corpus |
|---|---|---|
| Fixed-size (tokens/chars) | trivial, predictable | cuts mid-clause/mid-row; splits table from header |
| Recursive character | respects paragraph/sentence breaks heuristically | no notion of tables or clause headings; the tutorial default |
| Sentence/paragraph | clean semantic units | clauses with sub-points get fragmented; tables become noise |
| **Structure-aware** (layout blocks → header / table / clause / footer) | aligns with how questions are asked ("payment terms") and with citation | needs layout parsing; per-template variance |
| Semantic (embedding-similarity breakpoints) | adaptive | costs embedding calls at ingest; unstable; docs are already short and structured |
| Parent-child | precise child match + fuller parent context | extra complexity; useful once clauses are long |

## Provisional decision
**Structure-aware chunking with a contextual prefix**, recursive splitting only as a fallback inside an over-long block:

- **Unit:** one chunk per logical section — header block; each clause (heading + body); tables (see below); totals/footer kept as separate small chunks flagged `footer`/`header` so they rarely pollute retrieval.
- **Size:** target 150–400 tokens, hard cap ~512 (well below embedding limits; keeps one idea per vector). Documents are short, so most clauses fit whole. *Numbers to be confirmed by Sprint 2 experiment, not by convention.*
- **Overlap:** 0 across structural boundaries (overlap between unrelated sections adds noise); ~10–15 % only in fallback splits of long prose.
- **Tables:** line-item table serialised as markdown/key-value rows with column headers repeated; if over the cap, split by rows with header repeated in each chunk. Authoritative table data goes to SQL (S3), the table chunk exists so semantic questions about "what was ordered" still work.
- **Contextual prefix** embedded with every chunk: `[PO PO-24-0113 | Vendor: Acme Pvt Ltd | Section: Delivery Terms | p.2]`. Stored in `chunks.meta`/derived at embed time, not baked into canonical `text`.
- **Parent link:** `parent_chunk_id` populated for clause → section when a section is split; parent-child retrieval deferred, field retained.
- **Metadata:** see `data-model/schema.md` (`section`, `chunk_type`, pages, pipeline_version).

## Known limitations
Template variance can break section detection (fallback = recursive); scanned docs with poor OCR yield fragmented blocks; prefix inflates embedding input.

## Evaluation plan (Sprint 2)
Compare fixed / recursive / structure-aware / structure-aware+prefix on the golden set: Recall@K, MRR, chunk count, ingest cost.

## Reconsider if
Structure-aware does not beat recursive+prefix by a meaningful margin on our own metrics.
