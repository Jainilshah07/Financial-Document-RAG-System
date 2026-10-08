from enum import StrEnum


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DocumentType(StrEnum):
    PURCHASE_ORDER = "purchase_order"
    INVOICE = "invoice"
    UNKNOWN = "unknown"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    INGESTED = "ingested"
    NEEDS_OCR = "needs_ocr"  # image/scanned pages; OCR arrives in Sprint 4
    EMPTY = "empty"  # parsed fine but contains no usable content (blank template)
    FAILED = "failed"


class TextSource(StrEnum):
    NATIVE = "native"  # text layer or form fields from the PDF itself
    OCR = "ocr"


class ChunkType(StrEnum):
    HEADER = "header"
    TABLE = "table"
    CLAUSE = "clause"
    TEXT = "text"
    FOOTER = "footer"
