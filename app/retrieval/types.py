from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IndexPoint:
    """One vector to store. `chunk_id` is the Postgres chunk id (also the Qdrant point id);
    `payload` carries the filter keys so searches can be narrowed (ADR-004)."""

    chunk_id: int
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    score: float  # cosine similarity: higher is closer
    payload: dict[str, Any]


@dataclass(frozen=True)
class SearchFilters:
    """Restrictions applied *before* ranking. Inactive chunks are always excluded."""

    document_ids: Sequence[int] | None = None  # the hybrid route passes the SQL result here
    document_type: str | None = None
