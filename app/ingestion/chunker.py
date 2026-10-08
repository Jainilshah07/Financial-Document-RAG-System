"""Structure-aware chunking (ADR-002, chunker-v1).

Instead of cutting text every N characters, we cut along the document's own structure,
so a chunk is one idea a person could cite:

  * clause  - a numbered heading plus its body ("2. Price Basis: ...")
  * table   - consecutive line-item rows, with the header line above them
  * header  - the leading text of the document (parties, numbers, dates)
  * text    - any other run of paragraphs

Only when a single structural unit is too big do we fall back to size-based splitting
(with a little overlap, because that is the one case where we cut mid-thought).

Everything works on the *text* that the parser produced; no layout coordinates are used.
Known limitations: a clause that runs across a page break becomes two chunks; line items
printed one cell per line are not recognised as a table (they stay plain text).
"""

import hashlib
import re
from dataclasses import dataclass

from app.core.tokens import estimate_tokens
from app.db.models.enums import ChunkType
from app.ingestion.types import ParsedPage

CHUNKER_VERSION = "chunker-v1"

_CLAUSE_HEADING = re.compile(r"^\d{1,2}[.)]\s+\S")
_CLAUSE_NUMBER = re.compile(r"^\d{1,2}[.)]\s+")
# A money-like amount: 445.44, 1,366.96, 2,694.30
_AMOUNT = re.compile(r"\d[\d,]*\.\d{2}\b")


@dataclass(frozen=True)
class ChunkingConfig:
    """Tunable knobs. Sizes are approximate tokens (see `estimate_tokens`).

    Defaults follow ADR-002 (150-400 tokens, hard cap 512). They are a starting point:
    Sprint 2 compares them against alternatives using retrieval metrics.
    """

    max_tokens: int = 400  # structural units above this are split
    min_tokens: int = 30  # a text segment below this is merged into its neighbour
    overlap_tokens: int = 40  # overlap used only when splitting an oversized unit
    table_min_rows: int = 2  # consecutive amount-bearing lines needed to call it a table


@dataclass(frozen=True)
class DraftChunk:
    """A chunk before it is saved; maps onto the `chunks` table."""

    chunk_index: int
    page_start: int
    page_end: int
    section: str | None
    chunk_type: ChunkType
    text: str
    token_count: int
    content_hash: str


@dataclass
class _Segment:
    page: int
    kind: ChunkType
    section: str | None
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


def chunk_document(
    pages: list[ParsedPage], config: ChunkingConfig | None = None
) -> list[DraftChunk]:
    config = config or ChunkingConfig()

    segments: list[_Segment] = []
    for page in pages:
        if page.text:
            segments.extend(_segment_page(page, config))
    segments = _merge_small_text(segments, config)
    _label_header(segments)

    chunks: list[DraftChunk] = []
    for segment in segments:
        for piece in _split_oversized(segment.text, config):
            chunks.append(
                DraftChunk(
                    chunk_index=len(chunks),
                    page_start=segment.page,
                    page_end=segment.page,
                    section=segment.section,
                    chunk_type=segment.kind,
                    text=piece,
                    token_count=estimate_tokens(piece),
                    content_hash=hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                )
            )
    return chunks


# --- 1. split a page into structural segments ---------------------------------------


def _segment_page(page: ParsedPage, config: ChunkingConfig) -> list[_Segment]:
    lines = page.text.split("\n")
    is_row = [bool(len(_AMOUNT.findall(line)) >= 2) for line in lines]

    segments: list[_Segment] = []
    current: _Segment | None = None  # the open text or clause segment

    def flush() -> None:
        nonlocal current
        if current and current.text:
            segments.append(current)
        current = None

    i = 0
    while i < len(lines):
        line = lines[i]

        if _CLAUSE_HEADING.match(line):
            flush()
            current = _Segment(page.page_number, ChunkType.CLAUSE, _clause_title(line), [line])
            i += 1
            continue

        if is_row[i]:
            end = i
            while end < len(lines) and is_row[end]:
                end += 1
            if end - i >= config.table_min_rows and not _in_clause(current):
                header_line = _pop_last_line(current)  # column headers sit just above rows
                flush()
                rows = ([header_line] if header_line else []) + lines[i:end]
                segments.append(_Segment(page.page_number, ChunkType.TABLE, "Line items", rows))
                i = end
                continue

        if current is None:
            current = _Segment(page.page_number, ChunkType.TEXT, None, [])
        current.lines.append(line)
        i += 1

    flush()
    return segments


def _in_clause(segment: _Segment | None) -> bool:
    return segment is not None and segment.kind is ChunkType.CLAUSE


def _pop_last_line(segment: _Segment | None) -> str | None:
    if segment is None:
        return None
    while segment.lines and not segment.lines[-1].strip():
        segment.lines.pop()
    return segment.lines.pop() if segment.lines else None


def _clause_title(heading_line: str) -> str:
    return _CLAUSE_NUMBER.sub("", heading_line).rstrip(" :").strip()


# --- 2. tidy up ---------------------------------------------------------------------


def _merge_small_text(segments: list[_Segment], config: ChunkingConfig) -> list[_Segment]:
    """Fold tiny text segments (page numbers, a totals line) into the previous segment on
    the same page, or - if there is none - the following one."""
    merged: list[_Segment] = []
    carry: _Segment | None = None  # small segment waiting for a following neighbour
    for seg in segments:
        small_text = seg.kind is ChunkType.TEXT and estimate_tokens(seg.text) < config.min_tokens
        if small_text and merged and merged[-1].page == seg.page:
            merged[-1].lines.extend(["", *seg.lines])
        elif small_text:
            if carry:  # two small segments in a row: keep the earlier one, in order
                merged.append(carry)
            carry = seg
        else:
            if carry and carry.page == seg.page:
                seg.lines = [*carry.lines, "", *seg.lines]
            elif carry:
                merged.append(carry)
            carry = None
            merged.append(seg)
    if carry:
        merged.append(carry)
    return merged


def _label_header(segments: list[_Segment]) -> None:
    """Leading plain text of the first page = the document header (parties, numbers)."""
    if segments and segments[0].kind is ChunkType.TEXT:
        segments[0].kind = ChunkType.HEADER
        segments[0].section = "Header"


# --- 3. size fallback ---------------------------------------------------------------


def _split_oversized(text: str, config: ChunkingConfig) -> list[str]:
    """Return `text` unchanged if it fits; otherwise pack whole lines into pieces of at
    most `max_tokens`, repeating the last ~`overlap_tokens` of one piece at the start of
    the next so a sentence cut at the boundary still appears whole somewhere."""
    if estimate_tokens(text) <= config.max_tokens:
        return [text]

    max_chars = config.max_tokens * 4
    overlap_chars = config.overlap_tokens * 4
    units: list[str] = []
    for line in text.split("\n"):
        while len(line) > max_chars:  # a single enormous line: hard cut
            units.append(line[:max_chars])
            line = line[max_chars:]
        units.append(line)

    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for unit in units:
        if current and size + len(unit) + 1 > max_chars:
            pieces.append("\n".join(current).strip())
            current, size = _overlap_tail(current, overlap_chars)
        current.append(unit)
        size += len(unit) + 1
    if current and "\n".join(current).strip():
        pieces.append("\n".join(current).strip())
    return [p for p in pieces if p]


def _overlap_tail(lines: list[str], overlap_chars: int) -> tuple[list[str], int]:
    tail: list[str] = []
    size = 0
    for line in reversed(lines):
        if size + len(line) + 1 > overlap_chars:
            break
        tail.insert(0, line)
        size += len(line) + 1
    return tail, size
