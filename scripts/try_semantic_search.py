"""Try the whole retrieval stack WITHOUT touching PostgreSQL.

parse -> chunk -> embed (real Gemini API call) -> in-memory Qdrant -> search

It makes real API calls (a handful of chunks = 1 batched request) and prints the top hits
for some questions, so you can see semantic search working on your sample documents.

Usage:
    python scripts/try_semantic_search.py
    python scripts/try_semantic_search.py --query "when must goods be delivered?" -k 3
    python scripts/try_semantic_search.py --path data/sample --query "payment terms"
"""

import argparse
import mimetypes
import time
from pathlib import Path

from qdrant_client import QdrantClient

from app.core.config import get_settings
from app.embeddings.factory import build_embedder
from app.ingestion.chunker import chunk_document
from app.ingestion.embedding_text import build_embedding_input
from app.ingestion.pdf_parser import parse_document
from app.retrieval.qdrant_index import QdrantVectorIndex
from app.retrieval.types import IndexPoint

DEFAULT_QUERIES = [
    "What are the payment terms?",
    "When is the delivery date?",
    "Which exchange rate applies?",
    "How should invoices be submitted?",
    "What is the total amount?",
]
SNIPPET_CHARS = 160


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--path", type=Path, default=Path("data/sample"))
    parser.add_argument("--query", action="append", help="repeatable; defaults to a few examples")
    parser.add_argument("-k", type=int, default=3, help="hits per query")
    args = parser.parse_args()

    settings = get_settings()
    embedder = build_embedder(settings)

    # 1. parse + chunk every file; keep what we need to display results later
    texts: list[str] = []
    meta: list[dict] = []
    for file in sorted(p for p in args.path.iterdir() if p.is_file()):
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        doc = parse_document(file.read_bytes(), mime)
        for chunk in chunk_document(doc.pages):
            texts.append(build_embedding_input(file.name, chunk))
            meta.append(
                {
                    "file": file.name,
                    "page": chunk.page_start,
                    "section": chunk.section,
                    "chunk_type": chunk.chunk_type.value,
                    "text": chunk.text,
                }
            )
    print(f"{len(texts)} chunks to embed with {embedder.model_id}")

    # 2. embed (one real API request per batch of up to 50 chunks)
    started = time.perf_counter()
    vectors = embedder.embed_documents(texts)
    print(f"embedded in {time.perf_counter() - started:.1f}s")

    # 3. index in memory (nothing is written to disk)
    index = QdrantVectorIndex(QdrantClient(":memory:"), embedder.model_id, embedder.dimension)
    index.upsert(
        [
            IndexPoint(
                chunk_id=i,
                vector=vector,
                payload={"is_active": True, "document_id": hash(m["file"]) % 10_000, **m},
            )
            for i, (vector, m) in enumerate(zip(vectors, meta, strict=True))
        ]
    )
    print(f"index holds {index.count()} vectors\n")

    # 4. search
    for query in args.query or DEFAULT_QUERIES:
        print(f"Q: {query}")
        for hit in index.search(embedder.embed_query(query), k=args.k):
            m = hit.payload
            snippet = " ".join(m["text"].split())[:SNIPPET_CHARS]
            print(f"   {hit.score:.3f}  {m['file']} p.{m['page']} [{m['section']}]  {snippet}")
        print()


if __name__ == "__main__":
    main()
