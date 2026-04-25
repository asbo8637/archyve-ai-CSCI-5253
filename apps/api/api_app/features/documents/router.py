from pathlib import Path

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from archyve_common.db import get_session
from archyve_common.models import Document

from api_app.features.documents.constants import SUPPORTED_DOCUMENT_SUFFIXES
from api_app.features.documents.schemas import DocumentRead
from api_app.features.documents.service import (
    create_document_from_upload,
    list_documents_for_company,
    reindex_document,
)
from api_app.features.auth.service import get_current_principal
from api_app.integrations.auth import AuthenticatedPrincipal

router = APIRouter()


@router.get("/documents", response_model=list[DocumentRead])
def list_documents(
    session: Session = Depends(get_session),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> list[Document]:
    return list_documents_for_company(session, company_id=principal.company_id)


@router.post("/documents", response_model=DocumentRead, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Document:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type for the local bootstrap flow.",
        )

    return await create_document_from_upload(
        session,
        company_id=principal.company_id,
        uploaded_by_user_id=principal.user_id,
        file=file,
    )


@router.post("/documents/{document_id}/reindex", response_model=DocumentRead)
def reindex(
    document_id: UUID,
    session: Session = Depends(get_session),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Document:
    document = reindex_document(
        session,
        document_id=document_id,
        company_id=principal.company_id,
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document
