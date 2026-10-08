"""Inspect how documents are chunked. Prints only; never writes to the database.

Usage:
    python scripts/chunk_document.py data/sample
    python scripts/chunk_document.py data/sample/PO_3600031165_SARS.pdf --full
    python scripts/chunk_document.py data/sample --embed-input   # show the embedded text
"""

import argparse
import mimetypes
from pathlib import Path

from app.ingestion.chunker import CHUNKER_VERSION, chunk_document
from app.ingestion.embedding_text import build_embedding_input
from app.ingestion.pdf_parser import parse_document

PREVIEW_CHARS = 300


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("path", type=Path, help="a file or a folder")
    parser.add_argument("--full", action="store_true", help="print full chunk text")
    parser.add_argument("--embed-input", action="store_true", help="print the embedded text")
    args = parser.parse_args()

    files = (
        sorted(p for p in args.path.iterdir() if p.is_file()) if args.path.is_dir() else [args.path]
    )
    print(f"chunker: {CHUNKER_VERSION}")
    for file in files:
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        doc = parse_document(file.read_bytes(), mime)
        chunks = chunk_document(doc.pages)
        print("=" * 78)
        print(f"{file.name}: status={doc.status.value}, {len(chunks)} chunks")
        for c in chunks:
            print(
                f"--- #{c.chunk_index} p.{c.page_start} {c.chunk_type.value:<7} "
                f"~{c.token_count} tok  section={c.section!r}"
            )
            text = build_embedding_input(file.name, c) if args.embed_input else c.text
            shown = text if args.full else text[:PREVIEW_CHARS]
            print(shown + ("..." if len(text) > len(shown) else ""))


if __name__ == "__main__":
    main()
