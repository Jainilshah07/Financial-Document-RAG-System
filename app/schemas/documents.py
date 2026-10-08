from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import DocumentStatus, DocumentType


class UploadResponse(BaseModel):
    document_id: int
    filename: str
    status: DocumentStatus = Field(description="ingested | needs_ocr | empty | failed")
    status_detail: str | None = None
    page_count: int
    chunk_count: int = Field(description="Searchable chunks created for this document")
    already_exists: bool = Field(
        description="True if an identical file was uploaded before (nothing was re-processed)"
    )


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    doc_type: DocumentType
    doc_number: str | None
    status: DocumentStatus
    status_detail: str | None
    page_count: int
    is_scanned: bool
    chunk_count: int
    created_at: datetime
