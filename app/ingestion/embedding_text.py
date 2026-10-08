import hashlib

from app.ingestion.chunker import DraftChunk


def build_embedding_input(filename: str, chunk: DraftChunk) -> str:
    """The exact text we send to the embedding model: a context prefix plus the chunk.

    Many POs share identical boilerplate ("Payment shall be 30 days ..."). Without the
    prefix, the same clause from two different documents embeds to the same vector and
    cannot be told apart. The prefix is NOT stored in `chunks.text` (citations show the
    original text); it exists only in what is embedded. Sprint 3 adds the PO number and
    vendor once extraction can supply them.
    """
    pages = (
        f"p.{chunk.page_start}"
        if chunk.page_start == chunk.page_end
        else f"pp.{chunk.page_start}-{chunk.page_end}"
    )
    parts = [f"Document: {filename}", pages]
    if chunk.section:
        parts.append(f"Section: {chunk.section}")
    return f"[{' | '.join(parts)}]\n{chunk.text}"


def input_hash(embedding_input: str) -> str:
    """Cache key for `chunk_embeddings.input_hash`: identical input -> never re-embed."""
    return hashlib.sha256(embedding_input.encode("utf-8")).hexdigest()
