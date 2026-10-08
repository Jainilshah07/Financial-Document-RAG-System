import re
from collections.abc import Sequence

from qdrant_client import QdrantClient
from qdrant_client import models as q

from app.core.config import Settings
from app.retrieval.types import IndexPoint, SearchFilters, SearchHit

UPSERT_BATCH = 128


def build_qdrant_client(settings: Settings) -> QdrantClient:
    """Embedded (on-disk, no server) unless QDRANT_URL points at a Qdrant server.

    Embedded mode keeps a lock on its folder: only ONE process may use it at a time
    (stop the API before running a script that opens the same path)."""
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url)
    return QdrantClient(path=settings.qdrant_path)


def collection_name(model_id: str) -> str:
    """One collection per embedding model+dimension, so models can be compared side by side."""
    return "chunks_" + re.sub(r"[^a-zA-Z0-9_-]", "_", model_id)


class QdrantVectorIndex:
    def __init__(self, client: QdrantClient, model_id: str, dimension: int) -> None:
        self._client = client
        self._collection = collection_name(model_id)
        if not client.collection_exists(self._collection):
            client.create_collection(
                self._collection,
                vectors_config=q.VectorParams(size=dimension, distance=q.Distance.COSINE),
            )

    def upsert(self, points: Sequence[IndexPoint]) -> None:
        for start in range(0, len(points), UPSERT_BATCH):
            batch = points[start : start + UPSERT_BATCH]
            self._client.upsert(
                self._collection,
                points=[
                    q.PointStruct(id=p.chunk_id, vector=p.vector, payload=p.payload) for p in batch
                ],
            )

    def delete(self, chunk_ids: Sequence[int]) -> None:
        if chunk_ids:
            self._client.delete(
                self._collection, points_selector=q.PointIdsList(points=list(chunk_ids))
            )

    def search(
        self, vector: Sequence[float], k: int, filters: SearchFilters | None = None
    ) -> list[SearchHit]:
        result = self._client.query_points(
            self._collection,
            query=list(vector),
            limit=k,
            query_filter=_build_filter(filters),
            with_payload=True,
        )
        return [
            SearchHit(chunk_id=int(p.id), score=p.score, payload=p.payload or {})
            for p in result.points
        ]

    def count(self) -> int:
        return self._client.count(self._collection, exact=True).count


def _build_filter(filters: SearchFilters | None) -> q.Filter:
    # Superseded chunks must never be returned.
    must: list[q.Condition] = [
        q.FieldCondition(key="is_active", match=q.MatchValue(value=True)),
    ]
    if filters and filters.document_ids is not None:
        must.append(
            q.FieldCondition(key="document_id", match=q.MatchAny(any=list(filters.document_ids)))
        )
    if filters and filters.document_type:
        must.append(
            q.FieldCondition(key="document_type", match=q.MatchValue(value=filters.document_type))
        )
    return q.Filter(must=must)
