from uuid import uuid4

from archyve_common.models import Document, DocumentStatus, JobStatus, JobType

from api_app.features.indexing.service import build_process_document_job


def test_build_process_document_job_keeps_job_and_message_ids_in_sync() -> None:
    company_id = uuid4()
    document = Document(
        id=uuid4(),
        company_id=company_id,
        filename="report.txt",
        content_type="text/plain",
        storage_path="/tmp/report.txt",
        status=DocumentStatus.UPLOADED,
    )

    job, message = build_process_document_job(
        company_id=company_id,
        document=document,
    )

    assert job.status == JobStatus.PENDING
    assert job.job_type == JobType.PROCESS_DOCUMENT
    assert job.company_id == company_id
    assert job.payload == {"document_id": str(document.id)}
    assert message.company_id == company_id
    assert message.document_id == document.id
