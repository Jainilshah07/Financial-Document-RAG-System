# Evaluation Strategy

Principle: evaluate retrieval separately from generation, and arithmetic separately from both. Every number we report must be reproducible from a versioned dataset + a command.

## Artefacts (all under `evals/` in git, built incrementally)

| Artefact | Content | Size / due |
|---|---|---|
| `golden_set.jsonl` | `{id, question, class: structured\|semantic\|hybrid, type: standard\|adversarial, adversarial_kind?, expected_answer, expected_sources:[{document, page}], expected_numbers?, notes}` | 40 = 30 standard + 10 adversarial (Part D, wk 4); v0 of ~10 in Sprint 2 |
| `router_set.jsonl` | `{id, question, label}` | 40 (acceptance criterion); balanced across the 3 classes |
| `retrieval_set.jsonl` | question → relevant `chunk/page` ids | derived from golden set + extras |
| `extraction_truth/` | per-document ground-truth fields JSON | for the docs in the corpus; used from Sprint 3 |
| `ocr_truth/` | transcript/field truth for scanned docs | Sprint 4 |
| `mismatch_truth.json` | known injected PO↔invoice mismatches | Sprint 6 |

Ground truth is hand-verified against the source documents; with ~6–50 docs this is feasible, and any LLM-generated question is human-checked.

## Metrics

| Layer | Metric | Notes |
|---|---|---|
| Retrieval | Recall@K (K=3,5,10), Precision@K, MRR, hit-rate@K | relevance judged at **document+page** level (chunk ids change when chunking changes — page is the stable unit) |
| Router | accuracy, per-class precision/recall, confusion matrix | hybrid is the hard class |
| Extraction | per-field exact-match (normalised), per-document completeness | after normalisation of dates/amounts |
| OCR | per-field accuracy vs. confidence; calibration (accuracy of fields above threshold); coverage (fraction trusted) | pick threshold on a held-out split |
| Structured answers | numeric exact match against value computed from ground-truth rows | **tolerance 0** for money |
| Verifier | % of answer numbers present in result set (must be 100 %) | hard gate |
| Mismatch | precision/recall of detected injected mismatches | |
| E2E answer | correctness (rubric: expected facts present, no unsupported claim), citation correctness (cited doc/page contain the evidence) | LLM-judge only as a *helper* for semantic answers, with human spot-check; never to judge numbers |
| Operational | p50/p95 latency per route and per stage, tokens, ₹/query | feeds Budget report |

## Adversarial categories (10 in golden set)
unanswerable (not in corpus) · ambiguous scope ("delivery terms?" with many POs) · false premise (vendor/PO that does not exist) · currency trap (₹ question over USD docs) · low-confidence field (must flag) · empty template (placeholders ≠ values) · prompt injection inside a document · arithmetic request over flagged docs · conflicting documents · out-of-domain.

## Regression policy (CI, Part D)
- Fast tier on every commit: unit tests + retrieval metrics on cached embeddings + router eval with recorded LLM outputs (no live calls) → fails if any metric drops > configured tolerance vs. `evals/baseline.json`.
- Live tier (manual/nightly): real LLM e2e over golden set; results archived as JSON.
- Baselines updated only via a reviewed commit that states why.

## Ablation plan (Sprint 8)
Components toggled one at a time over the golden set: router on/off (always-semantic baseline), SQL path off, contextual prefix, structure-aware vs recursive chunking, BM25, RRF, reranker, OCR confidence flagging, verifier. Report score, latency, ₹/query — including changes that did not help.

## Corpus plan
Dev corpus grows as in `requirements/dataset-sources.md`; the 500+/50-scanned target is assembled for Sprint 8–9 evaluation. Every document gets a ground-truth JSON next to it (manifest: `doc_id, doc_type, fields, line_items, is_scanned, source, license`).
