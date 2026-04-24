from pathlib import Path
from uuid import uuid4

from archyve_common.models import Document, DocumentStatus

from worker_app.integrations import storage as storage_module


class R2SettingsStub:
    r2_bucket = "archyve-dev"
    r2_configured = True


class FakeR2Client:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls = []

    def download_fileobj(self, bucket_name, object_key, fileobj) -> None:
        self.calls.append(
            {
                "bucket_name": bucket_name,
                "object_key": object_key,
            }
        )
        fileobj.write(self.body)
        fileobj.flush()


def build_document() -> Document:
    return Document(
        id=uuid4(),
        company_id=uuid4(),
        filename="report.txt",
        content_type="text/plain",
        storage_path="r2://archyve-dev/companies/company/documents/doc/source.txt",
        r2_bucket="archyve-dev",
        r2_key="companies/company/documents/doc/source.txt",
        status=DocumentStatus.UPLOADED,
    )


def test_local_storage_resolver_yields_existing_path() -> None:
    document = build_document()
    document.storage_path = "/tmp/example.txt"

    with storage_module.LocalDocumentStorageResolver().materialize(document) as path:
        assert path == Path("/tmp/example.txt")


def test_r2_storage_resolver_downloads_to_temp_file_and_cleans_up(monkeypatch) -> None:
    document = build_document()
    client = FakeR2Client(body=b"hello from r2")

    monkeypatch.setattr(storage_module, "get_settings", lambda: R2SettingsStub())
    monkeypatch.setattr(storage_module, "get_r2_client", lambda: client)

    with storage_module.R2DocumentStorageResolver().materialize(document) as path:
        assert path.read_bytes() == b"hello from r2"
        temp_path = path

    assert client.calls == [
        {
            "bucket_name": "archyve-dev",
            "object_key": "companies/company/documents/doc/source.txt",
        }
    ]
    assert temp_path.exists() is False


def test_get_document_storage_resolver_uses_r2_for_r2_backed_documents() -> None:
    document = build_document()

    resolver = storage_module.get_document_storage_resolver(document)

    assert isinstance(resolver, storage_module.R2DocumentStorageResolver)


def test_get_document_storage_resolver_uses_local_for_local_documents() -> None:
    document = build_document()
    document.storage_path = "/tmp/example.txt"
    document.r2_bucket = None
    document.r2_key = None

    resolver = storage_module.get_document_storage_resolver(document)

    assert isinstance(resolver, storage_module.LocalDocumentStorageResolver)
