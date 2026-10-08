from collections.abc import Sequence
from typing import Protocol

from app.retrieval.types import IndexPoint, SearchFilters, SearchHit


class VectorIndex(Protocol):
    """A *derived* search index over chunk vectors (Postgres stays the source of truth).

    It can always be rebuilt from `chunks` + `chunk_embeddings`, so implementations are
    free to be local, remote or in memory. Qdrant is the first implementation (ADR-004).
    """

    def upsert(self, points: Sequence[IndexPoint]) -> None:
        """Insert or replace vectors by chunk id."""

    def delete(self, chunk_ids: Sequence[int]) -> None:
        """Remove vectors (e.g. when chunks are superseded)."""

    def search(
        self, vector: Sequence[float], k: int, filters: SearchFilters | None = None
    ) -> list[SearchHit]:
        """Return the `k` nearest active chunks, best first."""

    def count(self) -> int:
        """Number of vectors stored (used to verify the index matches Postgres)."""
