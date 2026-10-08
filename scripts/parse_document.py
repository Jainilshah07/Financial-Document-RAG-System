"""Inspect what the parser extracts from files. Prints, never writes to the database.

Usage:
    python scripts/parse_document.py data/sample              # every file in a folder
    python scripts/parse_document.py data/sample/PO_23781.pdf # one file
    python scripts/parse_document.py data/sample/PO_23781.pdf --full   # show whole page text
"""

import argparse
import mimetypes
from pathlib import Path

from app.ingestion.pdf_parser import parse_document

PREVIEW_CHARS = 600


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("path", type=Path, help="a file or a folder")
    parser.add_argument("--full", action="store_true", help="print full page text")
    args = parser.parse_args()

    files = (
        sorted(p for p in args.path.iterdir() if p.is_file()) if args.path.is_dir() else [args.path]
    )
    for file in files:
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        doc = parse_document(file.read_bytes(), mime)
        print("=" * 78)
        print(f"{file.name}  [{mime}]")
        print(f"status={doc.status.value}  pages={doc.page_count}  scanned={doc.is_scanned}")
        if doc.status_detail:
            print(f"detail: {doc.status_detail}")
        for page in doc.pages:
            print(
                f"--- page {page.page_number}: {len(page.text)} chars, "
                f"{page.form_field_count} form-field lines, needs_ocr={page.needs_ocr}"
            )
            shown = page.text if args.full else page.text[:PREVIEW_CHARS]
            print(shown + ("..." if len(page.text) > len(shown) else ""))


if __name__ == "__main__":
    main()
