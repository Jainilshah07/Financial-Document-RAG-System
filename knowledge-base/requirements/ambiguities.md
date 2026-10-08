# Ambiguities, Resolutions, Open Questions

The statement says finding and resolving ambiguity is part of the work and the mentor will question it hardest. Status: `Proposed` until the user approves. Entries feed the final writeup.

| ID | Ambiguity | Proposed resolution | What would change it |
|---|---|---|---|
| A-01 | **Parts A and B not supplied.** They may impose requirements (citation format, latency, etc.). | Proceed with Part C + D. **Ask user for Parts A/B before Sprint 1 ends.** | Their content. |
| A-02 | **No corpus provided.** 500+ docs, ≥50 scanned. | Build a **synthetic generator** (Faker + ReportLab/HTML→PDF, several vendor templates) emitting PDFs *and a ground-truth JSON manifest*; produce scanned versions by rasterising + noise/skew/blur/JPEG artefacts. Ground truth is what makes extraction, OCR-threshold and mismatch evaluation possible. Optionally mix a few public invoices (SROIE/CORD-style) for realism. | User has a real/provided corpus. |
| A-03 | **"Q2"**: calendar or fiscal? | Indian fiscal year (Apr–Mar): **Q2 = Jul–Sep**. Router/plan resolves quarters via one config; ambiguous phrasing triggers a stated assumption in the answer. | Part A/B or user says calendar. |
| A-04 | **"Exceeded ₹5 lakh"**: which amount — PO grand total, pre-tax, or any line? | Document **grand total incl. tax**; plan schema exposes `amount_basis` (`total`/`subtotal`/`line`) and the answer states which was used. | Domain preference. |
| A-05 | **Confidence threshold** value and scope. | Per-field-type thresholds calibrated on the labelled scanned set (maximise precision of "trusted" fields); start point ~0.85, tuned in Sprint 4. Amounts/ids stricter than free text. Arithmetic cross-checks (Σ lines = subtotal, subtotal+tax = total) can *raise* confidence or *flag* a doc. | Calibration curve. |
| A-06 | **What does a flagged field do to an aggregate?** | Excluded from SQL aggregation by default; answer reports "computed over N docs, M flagged/excluded" with ids. Never imputed. | User preference for include-with-warning. |
| A-07 | **Mismatch definition** (PO vs invoice). | Link by referenced PO number (fuzzy fallback on vendor+amount+date). Report types: unmatched invoice, vendor mismatch, line qty/price mismatch, total mismatch beyond tolerance (default ₹1 or 0.5 %), tax mismatch, duplicate invoice, over-billing vs PO cumulative, invoice before PO date. Partial/multiple invoices per PO supported. Corpus generator injects known mismatches. | Domain rules. |
| A-08 | **Born-digital vs scanned**: "scanned images" may be PNG/JPG or image-only PDFs. | Accept PDF + common images; detect per page (text layer present and sane?) rather than per file. | — |
| A-09 | **Vendor identity**: "vendor X" has spelling variants (Pvt Ltd / Private Limited). | Normalise + `vendors` table with aliases; match by GSTIN when present, else fuzzy. | — |
| A-10 | **How does the LLM take part in structured questions without generating totals?** | LLM emits a **validated JSON query plan** (Pydantic: filters, group-by, aggregate op), *code* compiles it to SQL via SQLAlchemy, DB computes, answer text is templated/verified so every number in the output exists in the result set. No free-form text-to-SQL. | Plan language too limiting on golden set. |
| A-11 | **Router test set vs golden set**: same 40 questions? | Separate artefacts: a 40-question **router set** (labelled structured/semantic/hybrid) and a 40-question **golden set** (30 std + 10 adversarial, end-to-end answers). Overlap allowed, labels independent. | Part A/B. |
| A-12 | **Endpoint naming**: user brief says `/query`, Part D says `/ask`. | `/ask` is canonical; `/upload` for ingestion. `/query` not created unless wanted. | User preference. |
| A-13 | **Latency/cost targets** are "declared week 4" but not given. | Propose in Sprint 2 (e.g. p95 ≤ 8 s semantic, ≤ 12 s hybrid; ≤ ₹1/query) and revisit with data. | Part A/B. |
| A-14 | **Language/format**: English only? Hindi/regional scanned docs? | English only `[ASSUME]`; Indian number formats and ₹/Rs/INR variants handled. | Corpus. |
| A-15 | **Scope of "tables"**: line items only, or also tax breakdown, payment schedule tables? | Header fields + line items + tax/total summary; payment schedule as text clause unless needed. | Golden questions. |

## Additional ambiguities found in the real sample documents (2026-10-07)

| ID | Finding | Resolution |
|---|---|---|
| A-16 | Samples are **not ₹**: USD (US template), ZAR (SARS PO). "Exceeded ₹5 lakh" is currency-specific. | Store currency per document; amount filters compare only within a currency; no FX (`[FUT]`). Router plan has an explicit `currency` filter; answer states it. Part of the corpus may be re-templated to ₹ later. |
| A-17 | `PO_23781.pdf` is a **fillable-form PDF**: the visible values live in AcroForm fields, *not* in the text layer (raw text shows only labels). | Parser must read form-field values (PyMuPDF widgets) in addition to text; triage rule: "text layer present" ≠ "contains the data". |
| A-18 | Some fields are template placeholders (`<Company Name>`, `nn/dd/yyyy`). | Treat as missing (NULL + flagged), never as values. |
| A-19 | Dates differ by format (`14/12/2023`, `14.12.2023`, `22ND SEPTEMBER, 2022`, `2023/12/14`). | Normaliser with explicit parse rules; ambiguous day/month flagged. |
| A-20 | A PO's "delivery terms" may be a *date* (SARS), a *shipping term* (FOB) or absent. Boilerplate T&C pages (SARS p.2) are identical across that buyer's POs. | Matches the boilerplate risk in `retrieval-architecture.md`; clause chunks carry doc number + vendor prefix. |

## Resolved by the user (2026-10-07)

| Item | Answer | Effect |
|---|---|---|
| Parts A/B | Skipped, not required | A-01 closed; revisit only if a requirement surfaces |
| Synthetic corpus | Not needed now; 6 real samples in `dataset/` (5 PO + no invoices yet); public datasets for more | A-02 revised: see `dataset-sources.md`. A small generator may still be needed in Sprint 3/6 for PO↔invoice pairs (no public set has linked pairs) — decide then |
| Postgres/pgvector vs Chroma | "Whatever suits best" | ADR-004 → pgvector accepted, then **superseded 2026-10-08: Qdrant (embedded)** because local Postgres has no pgvector |
| Embeddings | Unsure; user uses **Groq** | Groq has no embeddings endpoint → ADR-003 revised: **local embeddings** |
| Indian FY quarters | Yes | A-03 confirmed |

## Still open
1. OCR engine choice — decided in Sprint 4 by bake-off (Tesseract vs RapidOCR).
2. Where to get ≥500 docs incl. ≥50 scanned and PO/invoice pairs — see `dataset-sources.md`; decide before Sprint 3.
