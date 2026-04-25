from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from archyve_common.models import Document, DocumentChunk, DocumentStatus

from api_app.integrations.llm import (
    AnswerRequest,
    AnswerResult,
    RetrievedChunk,
    get_answer_client,
    get_embeddings_client,
)

TOP_K = 5


def answer_question(
    session: Session,
    *,
    company_id: UUID,
    question: str,
) -> AnswerResult:
    embeddings_client = get_embeddings_client()
    [question_embedding] = embeddings_client.embed_texts([question])

    statement = (
        select(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.company_id == company_id)
        .where(DocumentChunk.embedding.isnot(None))
        .where(Document.status == DocumentStatus.READY)
        .order_by(DocumentChunk.embedding.cosine_distance(question_embedding))
        .limit(TOP_K)
    )
    chunks = list(session.scalars(statement).all())

    if not chunks:
        return AnswerResult(
            answer="No indexed documents found for this company. Upload and process some documents first.",
            cited_sources=(),
        )

    doc_ids = {chunk.document_id for chunk in chunks}
    documents = {
        doc.id: doc
        for doc in session.scalars(select(Document).where(Document.id.in_(doc_ids))).all()
    }

    context_chunks = tuple(
        RetrievedChunk(
            content=chunk.content,
            source_label=documents[chunk.document_id].filename
            if chunk.document_id in documents
            else "unknown",
        )
        for chunk in chunks
    )

    return get_answer_client().answer_question(
        AnswerRequest(question=question, context_chunks=context_chunks)
    )
