from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from archyve_common.db import SessionLocal
from archyve_common.models import (
    Document,
    DocumentStatus,
    Job,
    JobStatus,
    JobType,
)
from archyve_common.settings import get_settings

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


def process_job(job_id: UUID) -> None:
    # Processing not yet implemented — job has been claimed and logged.
    logger.info("Job %s claimed, processing not yet implemented", job_id)


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
