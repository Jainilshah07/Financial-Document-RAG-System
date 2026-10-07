# Functional Requirements Document (FRD)

Tags: `[SRC]` problem statement · `[DEC]` engineering decision · `[FUT]` future · `[ASSUME]` assumption (see `ambiguities.md`).

## 1. Problem statement `[SRC]`

Structured and unstructured routing over financial documents. Finance asks both *"which POs from Q2 exceeded ₹5 lakh for vendor X?"* (filter + aggregate, numeric) and *"what delivery terms did we agree with them?"* (semantic, textual). Vector search cannot discriminate ₹5,00,000 from ₹4,99,000, so numeric questions need extracted tables in a relational store queried with SQL; semantic questions need retrieval; the system must classify and route, and handle questions needing both.

> **Gap:** the statement says "read Part A, Part B and Part C" but only Part C (our problem) and Part D (deliverables) were supplied. Part A ("what everyone builds") and Part B ("common requirements") are **missing** and may add requirements (e.g. citation format, latency targets, auth). Tracked as ambiguity A-01.

## 2. Business scenario

A finance/procurement team holds 500+ purchase orders (POs) and invoices, some born-digital PDFs, at least 50 scanned images. They ask ad-hoc questions in natural language and need answers that are (a) correct to the rupee, (b) traceable to a source document and page, (c) honest when the source is unreadable.

## 3. Users

| User | Typical need |
|---|---|
| Finance analyst | Filtered/aggregated numeric queries ("total invoiced for vendor X in Q2") |
| Procurement officer | Terms and clauses ("delivery terms agreed with X"), PO status |
| Auditor / controller | Mismatches between PO and invoice; trace any number to source page |
| Evaluator / mentor (this project) | Comparable demo, golden-set scores, ablations |

## 4. Document corpus `[SRC]`

- 500+ invoices and POs; **≥ 50 scanned images** (rest assumed born-digital PDFs `[ASSUME]`).
- Corpus is **not supplied**; we must source or generate it `[ASSUME]` — see A-02 (recommended: synthetic generator with ground-truth manifest, ₹ and Indian digit grouping, optional public samples).

## 5. Question types

| Class | Example | Mechanism `[SRC]` |
|---|---|---|
| Structured | POs from Q2 over ₹5 lakh for vendor X; sum of invoices for vendor Y | SQL over extracted tables |
| Semantic | Delivery terms agreed with vendor X; warranty clause | Retrieval over text |
| Hybrid | Among POs over ₹5 lakh, what are the payment terms? | SQL filter first → semantic retrieval restricted to filtered docs |
| Adversarial (golden set) | Unanswerable, ambiguous, false-premise, injected-instruction | Must refuse / flag, not guess |

## 6. Functional requirements

| ID | Requirement | Source |
|---|---|---|
| FR-1 | Structured extraction: tables and fields from documents into a relational store | `[SRC]` |
| FR-2 | Query router classifies each question as structured / semantic / hybrid | `[SRC]` |
| FR-3 | All arithmetic computed by SQL/code from the structured store; **the LLM never generates a total**; results verifiable against source docs | `[SRC]` |
| FR-4 | OCR pipeline for scanned subset with **per-field confidence scores** | `[SRC]` |
| FR-5 | Documented confidence threshold; below it the field is **flagged, not trusted/guessed** | `[SRC]` |
| FR-6 | Hybrid queries: numeric filter first, then semantic answering over the filtered set | `[SRC]` |
| FR-7 | PO ↔ invoice mismatches detected and reported | `[SRC]` |
| FR-8 | Ingestion pipeline re-runnable from scratch and incremental on update | `[SRC]` Part D |
| FR-9 | `/ask` endpoint returns cited answers; containerised; structured logging | `[SRC]` Part D |
| FR-10 | Golden set: 40 questions (30 standard, 10 adversarial) with expected answers + sources | `[SRC]` Part D |
| FR-11 | CI eval pipeline on every commit; fails on regression | `[SRC]` Part D |
| FR-12 | Ablation table: score with/without each component | `[SRC]` Part D |
| FR-13 | Budget report: p95 latency and ₹/query (declared wk 4, measured wk 9) | `[SRC]` Part D |
| FR-14 | 2-page technical writeup (ambiguity, what broke, numbers incl. non-wins, next month) | `[SRC]` Part D |
| FR-15 | `/upload` endpoint for PDF ingestion via Swagger | `[DEC]` (user milestone) |
| FR-16 | Every answer carries source document + page (+ chunk or row id) | `[DEC]` extends FR-9 |
| FR-17 | Answers distinguish "computed from N documents; M excluded for low-confidence fields" | `[DEC]` follows FR-5 |

## 7. Non-functional requirements

| ID | Requirement | Source |
|---|---|---|
| NFR-1 | Router accuracy measured on a **40-question** labelled test set | `[SRC]` |
| NFR-2 | 5+ hybrid questions answered correctly | `[SRC]` |
| NFR-3 | Retrieval evaluated separately from generation (Recall@K, Precision@K, MRR) | `[DEC]` |
| NFR-4 | Provider-swappable LLM and embedding model via config | `[DEC]` |
| NFR-5 | Idempotent ingestion keyed by content hash + pipeline version | `[DEC]` |
| NFR-6 | Money stored as `NUMERIC` + currency, never float | `[DEC]` |
| NFR-7 | No secrets in code; config via env | `[DEC]` |
| NFR-8 | p95 latency and ₹/query targets — values **declared at Week 4**, measured at Week 9 | `[SRC]` (targets TBD) |

## 8. Constraints

- Currency is ₹; numbers use Indian grouping (₹5,00,000 = 5 lakh); queries may say "lakh"/"crore".
- Deadlines per Part D (ingestion wk 2, `/ask` wk 3, golden set + CI wk 4, ablation wk 8, budget + writeup wk 9).
- Windows dev machine; Python 3.12, Docker available.
- Learning project: code must stay readable; no technology without a recorded reason.

## 9. Acceptance criteria `[SRC]`

1. Router accuracy reported on a 40-question test set.
2. All arithmetic computed from the structured store, verifiable against source documents.
3. OCR confidence scores present; low-confidence fields flagged, not guessed.
4. 5+ hybrid questions answered correctly.
5. PO/invoice mismatches detected and reported.

## 10. Future scope `[FUT]`

Multi-currency/FX, GRN (3-way match), approval workflows, auth/multi-tenancy, UI beyond Swagger, vision-LLM extraction fallback, fine-tuned embeddings, streaming answers.

## 11. Explicit assumptions

Listed with resolutions in [`ambiguities.md`](ambiguities.md). Key ones: fiscal quarters are Indian FY (Q2 = Jul–Sep), "exceeded ₹X" refers to document grand total incl. tax unless stated, corpus is synthetic.
