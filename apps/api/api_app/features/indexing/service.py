from uuid import UUID, uuid4

from archyve_common.messages import ProcessDocumentJobPayload
from archyve_common.models import Document, Job, JobStatus, JobType


def build_process_document_job(
    *,
    company_id: UUID,
    document: Document,
    payload: dict | None = None,
) -> tuple[Job, ProcessDocumentJobPayload]:
    job = Job(
        id=uuid4(),
        job_type=JobType.PROCESS_DOCUMENT,
        company_id=company_id,
        payload=payload or {"document_id": str(document.id)},
        status=JobStatus.PENDING,
        attempts=0,
    )
    message = ProcessDocumentJobPayload(
        company_id=company_id,
        document_id=document.id,
    )
    return job, message
