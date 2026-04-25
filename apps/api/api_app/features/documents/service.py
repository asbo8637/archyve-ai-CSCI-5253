from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from archyve_common.models import Document, DocumentStatus

from api_app.features.indexing.service import build_process_document_job
from api_app.integrations.queue import get_document_indexing_dispatcher
from api_app.integrations.storage import get_document_storage


def list_documents_for_company(session: Session, *, company_id: UUID) -> list[Document]:
    statement = (
        select(Document)
        .where(Document.company_id == company_id)
        .order_by(Document.created_at.desc())
    )
    return list(session.scalars(statement).all())


def reindex_document(
    session: Session,
    *,
    document_id: UUID,
    company_id: UUID,
) -> Document | None:
    document = session.scalar(
        select(Document)
        .where(Document.id == document_id)
        .where(Document.company_id == company_id)
    )
    if document is None:
        return None

    document.status = DocumentStatus.UPLOADED
    document.failure_reason = None

    job, message = build_process_document_job(company_id=company_id, document=document)
    session.add(job)
    session.commit()
    session.refresh(document)

    get_document_indexing_dispatcher().dispatch(message)
    return document


async def create_document_from_upload(
    session: Session,
    *,
    company_id: UUID,
    uploaded_by_user_id: UUID,
    file: UploadFile,
) -> Document:
    document = Document(
        id=uuid4(),
        company_id=company_id,
        uploaded_by_user_id=uploaded_by_user_id,
        filename=file.filename or "untitled",
        content_type=file.content_type,
        storage_path="",
        status=DocumentStatus.UPLOADED,
    )

    storage = get_document_storage()
    stored_asset = await storage.save_document_upload(
        company_id=company_id,
        document_id=document.id,
        file=file,
    )
    document.storage_path = stored_asset.storage_path
    document.r2_bucket = stored_asset.bucket_name
    document.r2_key = stored_asset.object_key

    job, message = build_process_document_job(
        company_id=company_id,
        document=document,
    )

    session.add_all([document, job])
    session.commit()
    session.refresh(document)

    dispatcher = get_document_indexing_dispatcher()
    dispatcher.dispatch(message)
    return document
