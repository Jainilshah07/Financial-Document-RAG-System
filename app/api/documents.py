import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_container, get_ingestion_service, get_session
from app.core.container import Container
from app.schemas.documents import DocumentOut, UploadResponse
from app.services import documents as document_queries
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["documents"])

ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}
MB = 1024 * 1024


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a PDF or image and make it searchable",
    responses={
        200: {"description": "Identical file was uploaded before; nothing re-processed"},
        201: {"description": "File ingested"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        422: {"description": "File could not be opened"},
        500: {"description": "Processing failed after the file was accepted"},
    },
)
def upload(  # sync on purpose: ingestion blocks (network calls) and runs in a worker thread
    file: UploadFile,
    response: Response,
    container: Container = Depends(get_container),
    service: IngestionService = Depends(get_ingestion_service),
) -> UploadResponse:
    mime_type = _resolve_mime_type(file)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(415, f"Unsupported file type {mime_type!r}. Use PDF, PNG or JPEG.")

    limit = container.settings.max_upload_mb * MB
    content = file.file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, f"File is larger than {container.settings.max_upload_mb} MB.")
    if not content:
        raise HTTPException(422, "File is empty.")

    result = service.ingest(file.filename or "upload", content, mime_type)

    if result.unreadable:
        raise HTTPException(422, result.status_detail or "File could not be opened.")
    if result.internal_error:
        raise HTTPException(
            500,
            detail={
                "message": "Ingestion failed; the file was kept and can be retried.",
                "document_id": result.document_id,
                "detail": result.status_detail,
            },
        )
    response.status_code = 200 if result.already_exists else 201
    return UploadResponse(
        document_id=result.document_id,
        filename=result.filename,
        status=result.status,
        status_detail=result.status_detail,
        page_count=result.page_count,
        chunk_count=result.chunk_count,
        already_exists=result.already_exists,
    )


@router.get("/documents", response_model=list[DocumentOut], summary="List ingested documents")
def list_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[DocumentOut]:
    return document_queries.list_documents(session, limit, offset)


@router.get("/documents/{document_id}", response_model=DocumentOut, summary="One document")
def get_document(document_id: int, session: Session = Depends(get_session)) -> DocumentOut:
    document = document_queries.get_document(session, document_id)
    if document is None:
        raise HTTPException(404, f"Document {document_id} not found.")
    return document


def _resolve_mime_type(file: UploadFile) -> str:
    declared = (file.content_type or "").lower()
    if declared and declared != "application/octet-stream":
        return "image/jpeg" if declared == "image/jpg" else declared
    return mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
