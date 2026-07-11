"""Document upload and analysis endpoints.

Findings and review live in ``app/api/routes/findings.py``, including the
document-derived ones. Both feature branches registered
``GET /sites/{site_id}/findings``; two handlers on one path means the router
included first wins and the other's findings silently disappear, so there is
exactly one owner of that path now.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.schemas.document import DocumentAnalysisResponse, DocumentResponse
from app.services.document_errors import DocumentError
from app.services.document_service import (
    build_analysis_response,
    get_document,
    list_documents_for_site,
    upload_document,
)
from app.services.pdf_parser import PdfValidationError
from app.workflows.permitting_graph import analyze_document

router = APIRouter(tags=["documents"])

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.post(
    "/sites/{site_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_site_document(
    site_id: str,
    file: Annotated[UploadFile, File()],
    db: DbSession,
    settings: AppSettings,
    response: Response,
) -> DocumentResponse:
    """Upload and validate one zoning/permitting PDF for a candidate site."""
    try:
        content = await file.read()
        result = upload_document(
            db,
            site_id=site_id,
            filename=file.filename or "document.pdf",
            mime_type=file.content_type or "",
            content=content,
            settings=settings,
        )
    except PdfValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DocumentError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if result.duplicate:
        response.status_code = status.HTTP_200_OK
    return DocumentResponse.model_validate(result.document)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_uploaded_document(document_id: str, db: DbSession) -> DocumentResponse:
    try:
        return DocumentResponse.model_validate(get_document(db, document_id))
    except DocumentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/documents/{document_id}/analyze", response_model=DocumentAnalysisResponse)
def analyze_uploaded_document(
    document_id: str,
    db: DbSession,
    settings: AppSettings,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DocumentAnalysisResponse:
    try:
        return analyze_document(
            db,
            document_id=document_id,
            settings=settings,
            idempotency_key=idempotency_key,
        )
    except DocumentError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/documents/{document_id}/analysis", response_model=DocumentAnalysisResponse)
def get_document_analysis(document_id: str, db: DbSession) -> DocumentAnalysisResponse:
    try:
        return build_analysis_response(db, document_id)
    except DocumentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/sites/{site_id}/documents", response_model=list[DocumentResponse])
def list_site_documents(site_id: str, db: DbSession) -> list[DocumentResponse]:
    """Every permitting document uploaded for a site, oldest first."""
    return [
        DocumentResponse.model_validate(document)
        for document in list_documents_for_site(db, site_id)
    ]
