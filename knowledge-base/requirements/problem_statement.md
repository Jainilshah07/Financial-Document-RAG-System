Read three sections: **Part A** (what everyone builds), **Part B** (the common requirements), and **your problem** in Part C.

**The rule that matters:** your problem statement is deliberately underspecified in places. Finding the ambiguity and deciding how to resolve it is part of the work, not a reason to wait for clarification. Write down each decision you make and why — that goes in your final writeup and it is the part the mentor will question hardest.

## Problem - Structured and unstructured routing over financial documents

**Scenario**
Finance asks both *"which POs from Q2 exceeded ₹5 lakh for vendor X?"* and *"what delivery terms did we agree with them?"* — two questions needing two entirely different mechanisms.

**Corpus**
500+ invoices and purchase orders. At least 50 must be scanned images.

**Why this is hard**
Vector search is close to useless on numbers — ₹5,00,000 and ₹4,99,000 sit next to each other in embedding space, and that difference is the whole question. Aggregation and filtering need extracted tables in a relational store queried with SQL. Semantic questions need retrieval. You have to classify the incoming question and route it, then handle the ones that need both.

**What you need to do beyond Part A**
1. Build structured extraction — tables and fields out of documents into a relational store
2. Build a query router that classifies incoming questions as structured, semantic, or hybrid
3. Route arithmetic to SQL. **Computed answers only — never let the model generate a total**
4. Add an OCR pipeline for the scanned subset, with per-field confidence scores
5. Decide and document your confidence threshold: below it, flag the field rather than trusting it
6. Handle hybrid queries — filter numerically first, then answer semantically over the filtered set

**Acceptance criteria**
- Router accuracy measured on a 40-question test set
- All arithmetic computed from the structured store, verifiable against source documents
- OCR confidence scores present; low-confidence fields flagged, not guessed
- 5+ hybrid questions answered correctly
- PO/invoice mismatches detected and reported


# Part D — What you deliver

Seven artifacts, identical for all six problems, so the demos stay comparable.

| # | Artifact | Due |
|---|---|---|
| 1 | Ingestion pipeline — re-runnable from scratch, incremental on update | Week 2, refined through 9 |
| 2 | FastAPI `/ask` endpoint — cited answers, containerised, structured logging | Week 3 |
| 3 | Golden set — 40 questions (30 standard, 10 adversarial), with expected answers and sources | Week 4 |
| 4 | CI eval pipeline — runs on every commit, fails on regression | Week 4 |
| 5 | Ablation table — score with and without each component | Week 8 |
| 6 | Budget report — p95 latency and ₹/query, declared week 4, measured week 9 | Week 9 |
| 7 | Technical writeup, 2 pages | Week 9 |

**The writeup must cover:**
- The ambiguity you found in your problem statement, and how you resolved it
- What broke, and what you tried before it worked
- What your numbers say, including the changes that didn't help
- What you would do differently with another month