"""Turn file bytes (PDF or image) into normalised per-page text.

Three things make real purchase orders harder than "just call get_text()":
  1. Fillable-form PDFs keep their values in form fields, not in the text layer
     (the layer then holds only labels like "P.O. NUMBER"). We read the fields too.
  2. Templates are full of unfilled slots ("<Company Name>", "nn/dd/yyyy") that must
     not be indexed as facts.
  3. Scanned pages/images have no text at all. We detect them and flag `needs_ocr`
     instead of silently producing empty pages (OCR is Sprint 4).
"""

from dataclasses import dataclass

import pymupdf

from app.db.models.enums import DocumentStatus
from app.ingestion.normalise import normalise_text
from app.ingestion.placeholders import is_placeholder, strip_placeholders
from app.ingestion.types import ParsedDocument, ParsedPage

MIN_TEXT_CHARS = 20  # below this a page "has no text" for triage purposes
ROW_TOLERANCE = 4.0  # points: form fields whose centres differ less sit on the same row
LABEL_MAX_GAP_LEFT = 160.0  # max distance (pt) to a label on the left of a field
LABEL_MAX_GAP_ABOVE = 22.0  # max distance (pt) to a label above a field
WORD_JOIN_GAP = 12.0  # words closer than this belong to the same label
TABLE_ROW_MIN_FIELDS = 3  # a row with this many filled fields is rendered as a table row
FIELD_COVERAGE_THRESHOLD = 0.5  # share of field values already in the page text to skip them

# (x0, y0, x1, y1, word, ...) as returned by page.get_text("words")
Word = tuple


@dataclass(frozen=True)
class _FilledField:
    rect: pymupdf.Rect
    value: str


def parse_document(data: bytes, mime_type: str) -> ParsedDocument:
    """Parse a PDF or image. Never raises for bad input: a broken file becomes a
    FAILED ParsedDocument so one bad upload cannot crash a batch ingestion."""
    try:
        document = pymupdf.open(stream=data, filetype=_filetype(mime_type))
    except (pymupdf.FileDataError, ValueError, RuntimeError) as exc:
        return ParsedDocument(
            status=DocumentStatus.FAILED, status_detail=f"Cannot open file: {exc}"
        )

    # PyMuPDF does not list the picture of an image file as a page image, so image
    # files are treated as "image-only" explicitly.
    is_image_file = mime_type.startswith("image/")
    with document:
        pages = [_parse_page(page, is_image_file) for page in document]
    return _summarise(pages)


def _filetype(mime_type: str) -> str:
    return {"application/pdf": "pdf", "image/jpg": "jpeg"}.get(mime_type, mime_type.split("/")[-1])


def _parse_page(page: pymupdf.Page, is_image_file: bool = False) -> ParsedPage:
    filled = _filled_fields(page)
    # sort=True orders text by position, which puts a form value next to its printed
    # label. On ordinary multi-column pages it interleaves the columns, so only use
    # it for pages that have filled form fields.
    raw = page.get_text("text", sort=bool(filled))
    body = normalise_text(strip_placeholders(raw))

    # PyMuPDF normally already includes form-field values in the page text. Only when
    # it does not (fields without a drawn appearance) do we add them ourselves.
    field_lines = [] if _body_covers_fields(body, filled) else _form_field_lines(page, filled)

    # `body` is already normalised. Do not normalise the combined text again: the
    # label-joining step is not idempotent and a second pass would join labels the
    # first pass deliberately left alone.
    text = body
    if field_lines:
        text = (
            f"{body}\n\nForm fields:\n" + "\n".join(field_lines) if body else "\n".join(field_lines)
        )

    has_images = is_image_file or bool(page.get_images())
    needs_ocr = len(text) < MIN_TEXT_CHARS and has_images
    return ParsedPage(
        page_number=page.number + 1,
        text="" if needs_ocr else text,
        needs_ocr=needs_ocr,
        form_field_count=len(field_lines),
    )


# --- form fields -------------------------------------------------------------------


def _body_covers_fields(body: str, filled: list[_FilledField]) -> bool:
    """True if the page text already contains (most of) the filled field values."""
    if not filled:
        return True
    flat_body = " ".join(body.split())
    found = sum(1 for f in filled if " ".join(f.value.split()) in flat_body)
    return found / len(filled) >= FIELD_COVERAGE_THRESHOLD


def _form_field_lines(page: pymupdf.Page, filled: list[_FilledField]) -> list[str]:
    if not filled:
        return []
    words = page.get_text("words")
    return [line for row in _group_rows(filled) if (line := _render_row(row, words))]


def _filled_fields(page: pymupdf.Page) -> list[_FilledField]:
    result = []
    for widget in page.widgets() or []:
        raw = widget.field_value
        if raw is None or isinstance(raw, bool):  # unchecked/checked boxes carry no text
            continue
        value = normalise_text(str(raw))
        if value and not is_placeholder(value):
            result.append(_FilledField(pymupdf.Rect(widget.rect), value))
    return result


def _group_rows(fields: list[_FilledField]) -> list[list[_FilledField]]:
    """Group fields that sit on the same visual line, ordered left to right."""
    ordered = sorted(fields, key=lambda f: ((f.rect.y0 + f.rect.y1) / 2, f.rect.x0))
    rows: list[list[_FilledField]] = []
    row_y = 0.0
    for f in ordered:
        centre_y = (f.rect.y0 + f.rect.y1) / 2
        if rows and abs(centre_y - row_y) <= ROW_TOLERANCE:
            rows[-1].append(f)
        else:
            rows.append([f])
            row_y = centre_y
    return [sorted(r, key=lambda f: f.rect.x0) for r in rows]


def _render_row(row: list[_FilledField], words: list[Word]) -> str:
    values = [f.value.replace("\n", ", ") for f in row]
    if len(row) >= TABLE_ROW_MIN_FIELDS:
        # Line-item row: the column headers are already in the text layer.
        return " | ".join(values)

    # Few fields: attach a nearby printed label ("Subtotal ($): 1366.96").
    parts: list[tuple[str | None, list[str]]] = []
    for f, value in zip(row, values, strict=True):
        label = _label_for(f.rect, words)
        if parts and parts[-1][0] == label:
            parts[-1][1].append(value)
        else:
            parts.append((label, [value]))
    return " ; ".join(
        f"{label}: {' | '.join(vals)}" if label else " | ".join(vals) for label, vals in parts
    )


def _label_for(rect: pymupdf.Rect, words: list[Word]) -> str | None:
    return _label_left(rect, words) or _label_above(rect, words)


def _label_left(rect: pymupdf.Rect, words: list[Word]) -> str | None:
    """Printed words on the same line, immediately to the left of the field."""
    candidates = [
        w
        for w in words
        if w[3] > rect.y0 + 1
        and w[1] < rect.y1 - 1  # vertical overlap with the field
        and w[2] <= rect.x0 + 2
        and rect.x0 - w[2] <= LABEL_MAX_GAP_LEFT
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda w: w[2], reverse=True)  # nearest first
    chain = [candidates[0]]
    for word in candidates[1:]:
        if chain[-1][0] - word[2] <= WORD_JOIN_GAP:
            chain.append(word)
        else:
            break
    return " ".join(w[4] for w in reversed(chain))


def _label_above(rect: pymupdf.Rect, words: list[Word]) -> str | None:
    """The nearest printed line directly above the field, overlapping it horizontally."""
    candidates = [
        w
        for w in words
        if w[3] <= rect.y0 + 2
        and rect.y0 - w[3] <= LABEL_MAX_GAP_ABOVE
        and w[2] > rect.x0
        and w[0] < rect.x1
    ]
    if not candidates:
        return None
    nearest_bottom = max(w[3] for w in candidates)
    line = sorted((w for w in candidates if nearest_bottom - w[3] < 3), key=lambda w: w[0])
    return " ".join(w[4] for w in line)


# --- document-level triage ---------------------------------------------------------


def _summarise(pages: list[ParsedPage]) -> ParsedDocument:
    if not pages:
        return ParsedDocument(status=DocumentStatus.FAILED, status_detail="File has no pages.")

    ocr_pages = [p.page_number for p in pages if p.needs_ocr]
    if len(ocr_pages) == len(pages):
        return ParsedDocument(
            pages=pages,
            status=DocumentStatus.NEEDS_OCR,
            status_detail="All pages are image-only; OCR is required (planned for Sprint 4).",
        )
    if not any(p.text for p in pages):
        return ParsedDocument(
            pages=pages, status=DocumentStatus.EMPTY, status_detail="No extractable text."
        )
    detail = f"Pages {ocr_pages} are image-only and were skipped (need OCR)." if ocr_pages else None
    return ParsedDocument(pages=pages, status=DocumentStatus.INGESTED, status_detail=detail)
