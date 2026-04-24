from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy.sql.elements import BinaryExpression

from archyve_common.messages import ProcessDocumentJobPayload
from archyve_common.models import Document, DocumentStatus, Job, JobType

from api_app.features.documents import service as documents_service
from api_app.integrations.storage import StoredDocumentAsset


class RecordingSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False
        self.refreshed = []

    def add_all(self, items) -> None:
        self.added.extend(items)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, obj) -> None:
        self.refreshed.append(obj)


class RecordingScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class RecordingListSession:
    def __init__(self, items) -> None:
        self.items = items
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        return RecordingScalarResult(self.items)


class FakeDocumentStorage:
    def __init__(self) -> None:
        self.calls = []

    async def save_document_upload(self, **kwargs) -> StoredDocumentAsset:
        self.calls.append(kwargs)
        return StoredDocumentAsset(
            object_key="org/doc/source.txt",
            storage_path="/tmp/org/doc/source.txt",
        )


class FakeDispatcher:
    def __init__(self) -> None:
        self.messages = []

    def dispatch(self, message: ProcessDocumentJobPayload) -> None:
        self.messages.append(message)


@pytest.mark.anyio
async def test_create_document_from_upload_persists_records_and_dispatches(monkeypatch) -> None:
    session = RecordingSession()
    storage = FakeDocumentStorage()
    dispatcher = FakeDispatcher()
    company_id = uuid4()
    user_id = uuid4()
    upload = UploadFile(filename="notes.txt", file=BytesIO(b"hello world"))

    monkeypatch.setattr(documents_service, "get_document_storage", lambda: storage)
    monkeypatch.setattr(
        documents_service,
        "get_document_indexing_dispatcher",
        lambda: dispatcher,
    )

    document = await documents_service.create_document_from_upload(
        session,
        company_id=company_id,
        uploaded_by_user_id=user_id,
        file=upload,
    )

    assert document.status == DocumentStatus.UPLOADED
    assert document.storage_path == "/tmp/org/doc/source.txt"
    assert document.r2_key == "org/doc/source.txt"
    assert document.company_id == company_id
    assert document.uploaded_by_user_id == user_id
    assert session.committed is True
    assert session.refreshed == [document]

    persisted_document = next(item for item in session.added if isinstance(item, Document))
    persisted_job = next(item for item in session.added if isinstance(item, Job))

    assert persisted_document.id == document.id
    assert persisted_job.payload == {"document_id": str(document.id)}
    assert persisted_job.company_id == company_id
    assert persisted_job.job_type == JobType.PROCESS_DOCUMENT

    assert len(storage.calls) == 1
    assert storage.calls[0]["company_id"] == company_id
    assert storage.calls[0]["document_id"] == document.id

    assert dispatcher.messages == [
        ProcessDocumentJobPayload(
            company_id=company_id,
            document_id=document.id,
        )
    ]


def test_list_documents_for_company_filters_by_company_id() -> None:
    company_id = uuid4()
    documents = [
        Document(
            id=uuid4(),
            company_id=company_id,
            filename="report.txt",
            content_type="text/plain",
            storage_path="/tmp/report.txt",
            status=DocumentStatus.UPLOADED,
        )
    ]
    session = RecordingListSession(documents)

    result = documents_service.list_documents_for_company(session, company_id=company_id)

    assert result == documents
    where_clause = next(iter(session.statement._where_criteria))
    assert isinstance(where_clause, BinaryExpression)
    assert where_clause.right.value == company_id
