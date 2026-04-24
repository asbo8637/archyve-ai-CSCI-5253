from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile

from archyve_common.db import get_session
from archyve_common.models import Document, DocumentStatus

from api_app.features.auth.service import get_current_principal
from api_app.features.documents import router as documents_router
from api_app.integrations.auth import AuthenticatedPrincipal


class FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self, items):
        self._items = items
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        return FakeScalarResult(self._items)


def build_document(filename: str = "report.txt") -> Document:
    return Document(
        id=uuid4(),
        company_id=uuid4(),
        filename=filename,
        content_type="text/plain",
        storage_path="/tmp/report.txt",
        status=DocumentStatus.UPLOADED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def build_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=uuid4(),
        auth0_user_id="auth0|user-1",
        company_id=uuid4(),
        membership_role="admin",
    )


def test_list_documents_returns_serialized_documents(api_client) -> None:
    documents = [build_document()]
    session = FakeSession(documents)
    api_client.app.dependency_overrides[get_session] = lambda: session
    api_client.app.dependency_overrides[get_current_principal] = build_principal

    response = api_client.get("/documents")

    assert response.status_code == 200
    assert response.json()[0]["filename"] == "report.txt"
    assert response.json()[0]["status"] == "uploaded"


def test_upload_document_creates_document(api_client, monkeypatch) -> None:
    session = object()
    principal = build_principal()
    created_document = build_document("notes.txt")

    async def fake_create_document_from_upload(
        current_session,
        *,
        company_id,
        uploaded_by_user_id,
        file,
    ):
        assert current_session is session
        assert company_id == principal.company_id
        assert uploaded_by_user_id == principal.user_id
        assert file.filename == "notes.txt"
        return created_document

    api_client.app.dependency_overrides[get_session] = lambda: session
    api_client.app.dependency_overrides[get_current_principal] = lambda: principal
    monkeypatch.setattr(
        documents_router,
        "create_document_from_upload",
        fake_create_document_from_upload,
    )

    response = api_client.post(
        "/documents",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "notes.txt"
    assert response.json()["status"] == "uploaded"


def test_upload_document_rejects_unsupported_file_type(api_client) -> None:
    api_client.app.dependency_overrides[get_current_principal] = build_principal

    response = api_client.post(
        "/documents",
        files={"file": ("payload.exe", b"binary", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type for the local bootstrap flow."


def test_upload_document_rejects_empty_multipart_filename(api_client) -> None:
    api_client.app.dependency_overrides[get_current_principal] = build_principal

    response = api_client.post(
        "/documents",
        files={"file": ("", b"hello world", "text/plain")},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_upload_document_handler_requires_filename() -> None:
    upload = UploadFile(filename="", file=BytesIO(b"hello world"))

    with pytest.raises(HTTPException) as exc_info:
        await documents_router.upload_document(
            file=upload,
            session=object(),
            principal=build_principal(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "A filename is required."


def test_documents_require_authentication(api_client) -> None:
    response = api_client.get("/documents")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "missing_token"
