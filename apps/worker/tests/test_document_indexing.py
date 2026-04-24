from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from archyve_common.models import (
    Document,
    DocumentStatus,
    Job,
    JobStatus,
    JobType,
)

from worker_app.jobs import document_indexing


class LocalStorageResolverStub:
    def materialize(self, document: Document):
        return nullcontext(Path(document.storage_path))


class BeginContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class SessionLocalStub:
    def __init__(self, session):
        self.session = session

    def begin(self):
        return BeginContext(self.session)


class ExecuteResult:
    def __init__(self, job):
        self.job = job

    def scalar_one_or_none(self):
        return self.job


class ClaimSession:
    def __init__(self, job=None, document=None):
        self.job = job
        self.document = document

    def execute(self, statement):
        return ExecuteResult(self.job)

    def get(self, model, primary_key):
        if model is Document:
            return self.document
        return None


class ProcessSession:
    def __init__(self, *, job, document):
        self.job = job
        self.document = document
        self.added = []
        self.executed = []

    def get(self, model, primary_key):
        if model is Job and primary_key == self.job.id:
            return self.job
        if model is Document and primary_key == self.document.id:
            return self.document
        return None

    def execute(self, statement):
        self.executed.append(statement)
        return None

    def add(self, obj) -> None:
        self.added.append(obj)


def build_job() -> tuple[Job, Document]:
    document = Document(
        id=uuid4(),
        company_id=uuid4(),
        filename="report.txt",
        content_type="text/plain",
        storage_path="/tmp/report.txt",
        status=DocumentStatus.UPLOADED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    job = Job(
        id=uuid4(),
        job_type=JobType.PROCESS_DOCUMENT,
        company_id=document.company_id,
        payload={"document_id": str(document.id)},
        status=JobStatus.PENDING,
        attempts=0,
    )
    return job, document


def test_claim_next_job_returns_none_when_no_pending_jobs(monkeypatch) -> None:
    monkeypatch.setattr(
        document_indexing,
        "SessionLocal",
        SessionLocalStub(ClaimSession()),
    )

    assert document_indexing.claim_next_job() is None


def test_claim_next_job_marks_job_and_document_processing(monkeypatch) -> None:
    job, document = build_job()
    monkeypatch.setattr(
        document_indexing,
        "SessionLocal",
        SessionLocalStub(ClaimSession(job=job, document=document)),
    )

    claimed_job_id = document_indexing.claim_next_job()

    assert claimed_job_id == job.id
    assert job.status == JobStatus.PROCESSING
    assert job.attempts == 1
    assert job.locked_at is not None
    assert job.locked_by is not None
    assert document.status == DocumentStatus.PROCESSING
    assert document.failure_reason is None


def test_process_job_marks_document_ready_and_adds_chunks(monkeypatch) -> None:
    job, document = build_job()
    session = ProcessSession(job=job, document=document)

    monkeypatch.setattr(document_indexing, "SessionLocal", SessionLocalStub(session))
    monkeypatch.setattr(
        document_indexing,
        "get_document_storage_resolver",
        lambda current_document: LocalStorageResolverStub(),
    )
    monkeypatch.setattr(document_indexing, "extract_text_from_path", lambda path: "alpha beta")
    monkeypatch.setattr(document_indexing, "chunk_text", lambda text: ["chunk-1", "chunk-2"])
    monkeypatch.setattr(document_indexing, "estimate_token_count", lambda text: len(text))

    document_indexing.process_job(job.id)

    assert document.status == DocumentStatus.READY
    assert document.failure_reason is None
    assert job.status == JobStatus.COMPLETED
    assert job.last_error is None
    assert job.completed_at is not None
    assert len(session.added) == 2
    assert session.added[0].chunk_index == 0
    assert session.added[0].token_count == len("chunk-1")
    assert session.added[0].company_id == document.company_id
    assert session.added[0].chunk_metadata == {"source_path": document.storage_path}


def test_process_job_marks_job_failed_when_metadata_is_missing(monkeypatch) -> None:
    job, document = build_job()
    job.payload = {}
    session = ProcessSession(job=job, document=document)

    monkeypatch.setattr(document_indexing, "SessionLocal", SessionLocalStub(session))
    monkeypatch.setattr(
        document_indexing,
        "get_document_storage_resolver",
        lambda current_document: LocalStorageResolverStub(),
    )

    document_indexing.process_job(job.id)

    assert job.status == JobStatus.FAILED
    assert job.last_error == "Document metadata was missing."
    assert job.completed_at is not None
    assert document.status == DocumentStatus.UPLOADED


def test_process_job_marks_document_failed_when_extraction_raises(monkeypatch) -> None:
    job, document = build_job()
    session = ProcessSession(job=job, document=document)

    monkeypatch.setattr(document_indexing, "SessionLocal", SessionLocalStub(session))
    monkeypatch.setattr(
        document_indexing,
        "get_document_storage_resolver",
        lambda current_document: LocalStorageResolverStub(),
    )

    def raise_extraction_error(_path):
        raise ValueError("unable to read file")

    monkeypatch.setattr(document_indexing, "extract_text_from_path", raise_extraction_error)

    document_indexing.process_job(job.id)

    assert job.status == JobStatus.FAILED
    assert job.last_error == "unable to read file"
    assert job.completed_at is not None
    assert document.status == DocumentStatus.FAILED
    assert document.failure_reason == "unable to read file"


def test_run_once_processes_claimed_job(monkeypatch) -> None:
    job_id = uuid4()
    processed_ids = []

    monkeypatch.setattr(document_indexing, "claim_next_job", lambda: job_id)
    monkeypatch.setattr(
        document_indexing,
        "process_job",
        lambda current_job_id: processed_ids.append(current_job_id),
    )

    assert document_indexing.run_once() is True
    assert processed_ids == [job_id]


def test_run_once_returns_false_when_no_job_is_available(monkeypatch) -> None:
    monkeypatch.setattr(document_indexing, "claim_next_job", lambda: None)
    monkeypatch.setattr(
        document_indexing,
        "process_job",
        lambda current_job_id: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    assert document_indexing.run_once() is False
