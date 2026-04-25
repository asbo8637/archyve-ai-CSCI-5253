from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select

from archyve_common.db import SessionLocal
from archyve_common.indexing import chunk_text, estimate_token_count, extract_text_from_path
from archyve_common.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    Job,
    JobStatus,
    JobType,
)
from archyve_common.settings import get_settings

from worker_app.integrations.embeddings import get_embeddings_client
from worker_app.integrations.storage import get_document_storage_resolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("archyve-worker")


def load_document_id(job: Job) -> UUID | None:
    raw_document_id = job.payload.get("document_id")
    if raw_document_id is None:
        return None

    if isinstance(raw_document_id, UUID):
        return raw_document_id

    try:
        return UUID(str(raw_document_id))
    except ValueError:
        return None


def claim_next_job() -> UUID | None:
    with SessionLocal.begin() as session:
        statement = (
            select(Job)
            .where(Job.status == JobStatus.PENDING)
            .where(Job.job_type == JobType.PROCESS_DOCUMENT)
            .where(Job.run_at <= datetime.now(UTC))
            .order_by(Job.run_at.asc(), Job.created_at.asc())
            .with_for_update(skip_locked=True)
        )
        job = session.execute(statement).scalar_one_or_none()

        if job is None:
            return None

        document_id = load_document_id(job)
        document = session.get(Document, document_id) if document_id is not None else None
        if document is None:
            return None

        job.status = JobStatus.PROCESSING
        job.locked_at = datetime.now(UTC)
        job.locked_by = get_settings().worker_name
        job.attempts += 1
        document.status = DocumentStatus.PROCESSING
        document.failure_reason = None
        return job.id


def _embed_chunks(chunk_objects: list[DocumentChunk]) -> None:
    try:
        client = get_embeddings_client()
        embeddings = client.embed_texts([c.content for c in chunk_objects])
        for chunk_obj, embedding in zip(chunk_objects, embeddings):
            chunk_obj.embedding = embedding
        logger.info("Generated embeddings for %d chunks", len(chunk_objects))
    except Exception as exc:
        logger.warning("Embedding generation skipped: %s", exc)


def process_job(job_id: UUID) -> None:
    with SessionLocal.begin() as session:
        job = session.get(Job, job_id)
        if job is None:
            return

        document_id = load_document_id(job)
        document = session.get(Document, document_id) if document_id is not None else None

        if document is None:
            job.status = JobStatus.FAILED
            job.last_error = "Document metadata was missing."
            job.completed_at = datetime.now(UTC)
            if document is not None:
                document.status = DocumentStatus.FAILED
                document.failure_reason = job.last_error
            return

        try:
            with get_document_storage_resolver(document).materialize(document) as local_path:
                text = extract_text_from_path(Path(local_path))
            chunks = chunk_text(text)

            session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == document.id
                )
            )

            chunk_objects = []
            for index, chunk in enumerate(chunks):
                dc = DocumentChunk(
                    document_id=document.id,
                    company_id=document.company_id,
                    chunk_index=index,
                    content=chunk,
                    token_count=estimate_token_count(chunk),
                    chunk_metadata={"source_path": document.storage_path},
                )
                session.add(dc)
                chunk_objects.append(dc)

            _embed_chunks(chunk_objects)

            document.status = DocumentStatus.READY
            document.failure_reason = None
            job.status = JobStatus.COMPLETED
            job.last_error = None
            job.completed_at = datetime.now(UTC)
            logger.info("Indexed document %s into %s chunks", document.id, len(chunks))
        except Exception as exc:  # pragma: no cover - defensive operational path
            job.status = JobStatus.FAILED
            job.last_error = str(exc)
            job.completed_at = datetime.now(UTC)
            document.status = DocumentStatus.FAILED
            document.failure_reason = str(exc)
            logger.exception("Failed to index document %s", document.id)


def run_once() -> bool:
    job_id = claim_next_job()
    if job_id is None:
        return False

    process_job(job_id)
    return True


def run_forever() -> None:
    settings = get_settings()
    logger.info(
        "Worker started with batch size %s and poll interval %ss",
        settings.worker_batch_size,
        settings.worker_poll_interval_seconds,
    )

    while True:
        processed_any = False
        for _ in range(settings.worker_batch_size):
            processed = run_once()
            processed_any = processed_any or processed
            if not processed:
                break

        if not processed_any:
            time.sleep(settings.worker_poll_interval_seconds)
