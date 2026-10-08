from collections.abc import Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, ChunkEmbedding
from app.embeddings.base import Embedder
from app.ingestion.embedding_text import input_hash

log = structlog.get_logger("ingestion.embeddings")


def embed_chunks(
    session: Session, embedder: Embedder, items: Sequence[tuple[Chunk, str]]
) -> dict[int, list[float]]:
    """Return a vector for every chunk, calling the embedding API only when necessary.

    `items` pairs each saved chunk (it must already have an id) with the exact text to
    embed. A vector is reused when ANY chunk already has one for the same model and the
    same input text (re-uploads, identical boilerplate in different documents, re-runs
    after a crash). Only unseen texts go to the API - that is what protects the free
    tier's ~1k requests/day. New cache rows are added to the session; the caller commits.
    """
    model_id = embedder.model_id
    hashed = [(chunk, text, input_hash(text)) for chunk, text in items]

    wanted = {h for _, _, h in hashed}
    cached: dict[str, list[float]] = {
        row.input_hash: list(row.embedding)
        for row in session.scalars(
            select(ChunkEmbedding).where(
                ChunkEmbedding.embedding_model == model_id,
                ChunkEmbedding.input_hash.in_(wanted),
            )
        )
    }

    to_embed = {h: text for _, text, h in hashed if h not in cached}  # de-duplicated
    if to_embed:
        vectors = embedder.embed_documents(list(to_embed.values()))
        cached.update(zip(to_embed.keys(), vectors, strict=True))
    log.info(
        "embeddings_resolved",
        chunks=len(hashed),
        from_cache=len(wanted) - len(to_embed),
        sent_to_api=len(to_embed),
        model=model_id,
    )

    chunk_ids = [chunk.id for chunk, _, _ in hashed]
    already_stored = set(
        session.scalars(
            select(ChunkEmbedding.chunk_id).where(
                ChunkEmbedding.embedding_model == model_id,
                ChunkEmbedding.chunk_id.in_(chunk_ids),
            )
        )
    )
    for chunk, _, h in hashed:
        if chunk.id not in already_stored:
            session.add(
                ChunkEmbedding(
                    chunk_id=chunk.id,
                    embedding_model=model_id,
                    input_hash=h,
                    dim=embedder.dimension,
                    embedding=cached[h],
                )
            )
    return {chunk.id: cached[h] for chunk, _, h in hashed}
