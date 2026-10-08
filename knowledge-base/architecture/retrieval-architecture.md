# Retrieval Architecture

Status: **Proposed**. Sprint 1 ships only dense retrieval, behind interfaces that admit everything else.

## Target pipeline

```
Query ─► Query analysis (route, entities: vendor, doc no., dates, amounts)
      ─► ┌ Metadata/SQL filter (doc_ids) ┐
         │ Dense (embeddings)            │ ─► Fusion (RRF) ─► Rerank (cross-encoder) ─► Context selection ─► LLM
         └ Lexical (BM25)                ┘
```

## Interface (Sprint 1)

```python
class Retriever(Protocol):
    def retrieve(
        self, query: str, *, k: int, filters: RetrievalFilters | None = None
    ) -> list[Hit]: ...


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    document_id: int
    page_start: int
    text: str
    score: float
    retriever: str  # "dense" | "bm25" | "rrf" | "rerank"
```
- `RetrievalFilters`: `document_ids`, `document_type`, `vendor_id`, `date_range` — compiled to SQL.
- Later: `HybridRetriever(retrievers=[...], fuser=RRF())` and `Reranked(inner, reranker)` are decorators/compositions; no caller changes.

## Technique notes for financial documents (to be validated by evals, not assumed)

| Technique | Helps with | Limits here |
|---|---|---|
| Dense | Paraphrase: "when must goods arrive" ≈ "delivery within 30 days" | Numbers/ids nearly indistinguishable; PO-0113 vs PO-0131 look alike |
| BM25 | Exact tokens: PO numbers, GSTIN, vendor names, clause keywords | No synonymy; tokenisation of `₹5,00,000` and `INV/24-25/0091` needs care |
| Metadata filtering | Scoping to vendor/doc/date before ranking — the core of the hybrid route | Only as good as extraction quality |
| RRF | Rank fusion without score calibration | Needs both lists to be reasonable |
| MMR | Diversity when many near-duplicate chunks (repeated T&C boilerplate across POs) | May drop a needed duplicate-looking clause from a *different* PO; evaluate before enabling |
| Reranker | Precision at top-3 | Latency + cost; ablate |
| Contextual prefix on chunks (`PO-123 · Vendor X · Delivery Terms`) | Makes boilerplate chunks distinguishable per document | Larger embeddings input; evaluate |

## Context selection

Cap by token budget, not just k; always keep document/page for citation; de-duplicate identical boilerplate clauses *only* when attribution is preserved (S7).

## Boilerplate problem (specific risk)

500 POs probably share near-identical T&C. "What are the delivery terms?" without a vendor/doc scope is therefore under-determined → the router/answer composer must ask for scope or answer per-document, not blend. Tracked as an adversarial golden question category.
