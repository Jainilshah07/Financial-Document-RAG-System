from dataclasses import dataclass, field

from app.db.models.enums import DocumentStatus, TextSource


@dataclass(frozen=True)
class ParsedPage:
    """What the parser learned about one page (not yet saved anywhere)."""

    page_number: int  # 1-based
    text: str  # normalised; empty if the page has no usable text
    text_source: TextSource = TextSource.NATIVE
    needs_ocr: bool = False  # no text but the page holds an image -> scanned content
    form_field_count: int = 0  # filled AcroForm fields that contributed to `text`


@dataclass(frozen=True)
class ParsedDocument:
    pages: list[ParsedPage] = field(default_factory=list)
    status: DocumentStatus = DocumentStatus.INGESTED
    status_detail: str | None = None

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def is_scanned(self) -> bool:
        """True when every page is image-only, so nothing can be read without OCR."""
        return bool(self.pages) and all(p.needs_ocr for p in self.pages)
