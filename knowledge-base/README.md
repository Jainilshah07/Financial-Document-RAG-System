# Knowledge Base — Financial Document RAG System (Problem 2)

Long-term project memory. If a decision, requirement or result is not here, it does not exist.

## Conventions

- **Source tags** are used everywhere to keep provenance honest:
  - `[SRC]` — stated in the official problem statement (`requirements/problem_statement.md`)
  - `[DEC]` — engineering decision we made (recorded in an ADR)
  - `[FUT]` — future enhancement, explicitly out of current scope
  - `[ASSUME]` — assumption we made to resolve an ambiguity; must be listed in `requirements/ambiguities.md`
- **ADR status**: `Proposed` (leaning, research pending) → `Accepted` (user-approved, backed by evidence) → `Superseded`.
- One sprint file per sprint in `progress/`. The roadmap is the only place sprint order lives.

## Map

| Path | Purpose |
|---|---|
| `requirements/problem_statement.md` | Official PS2 text (primary source of truth, never edited) |
| `requirements/frd.md` | Functional requirements document |
| `requirements/ambiguities.md` | Every ambiguity, our resolution, and what would change it |
| `architecture/system-architecture.md` | End-to-end architecture, module boundaries, API |
| `architecture/data-architecture.md` | Source of truth vs. retrieval index; what lives where |
| `architecture/retrieval-architecture.md` | Retriever interface, routing, hybrid path, evolution to BM25/rerank |
| `data-model/schema.md` | Entities, columns, and *which sprint introduces each table* |
| `decisions/ADR-*.md` | Architecture decision records |
| `progress/roadmap.md` | Sprint roadmap (refined against Part D deadlines) |
| `progress/sprint-00.md` | Sprint 0 scope, research questions, exit criteria |
| `prerequisites.md` | Accounts, keys, software to install |
| `research/sprint-00-findings.md` | Spike results + condensed research |
| `evaluation/evaluation-strategy.md` | Metrics, golden/router sets, regression policy, ablation plan |
| `requirements/dataset-sources.md` | Where to get more documents |

## Status

Sprint 0 complete. Sprint 1 planned (`progress/sprint-01.md`), awaiting go-ahead. No application code yet.
