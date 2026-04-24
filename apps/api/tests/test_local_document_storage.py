from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import UploadFile

from api_app.integrations import storage as storage_module


class SettingsStub:
    def __init__(self, storage_root_path: Path) -> None:
        self.storage_root_path = storage_root_path
        self.r2_bucket = None
        self.r2_configured = False


class R2SettingsStub:
    r2_bucket = "archyve-dev"
    r2_configured = True


class FakeR2Client:
    def __init__(self) -> None:
        self.calls = []

    def upload_fileobj(self, fileobj, bucket_name, object_key, ExtraArgs=None) -> None:
        self.calls.append(
            {
                "bucket_name": bucket_name,
                "object_key": object_key,
                "extra_args": ExtraArgs,
                "body": fileobj.read(),
            }
        )


@pytest.mark.anyio
async def test_local_document_storage_writes_upload_contents(tmp_path, monkeypatch) -> None:
    storage = storage_module.LocalDocumentStorage()
    company_id = uuid4()
    document_id = uuid4()
    upload = UploadFile(filename="notes.txt", file=BytesIO(b"hello from storage"))

    monkeypatch.setattr(
        storage_module,
        "get_settings",
        lambda: SettingsStub(tmp_path),
    )

    stored_asset = await storage.save_document_upload(
        company_id=company_id,
        document_id=document_id,
        file=upload,
    )

    expected_key = f"companies/{company_id}/documents/{document_id}/source.txt"
    expected_path = tmp_path / expected_key

    assert stored_asset.object_key == expected_key
    assert stored_asset.storage_path == str(expected_path)
    assert expected_path.read_bytes() == b"hello from storage"


@pytest.mark.anyio
async def test_r2_document_storage_uploads_to_bucket(monkeypatch) -> None:
    storage = storage_module.R2DocumentStorage()
    client = FakeR2Client()
    company_id = uuid4()
    document_id = uuid4()
    upload = UploadFile(
        filename="notes.txt",
        file=BytesIO(b"hello from r2"),
        headers={"content-type": "text/plain"},
    )

    monkeypatch.setattr(storage_module, "get_settings", lambda: R2SettingsStub())
    monkeypatch.setattr(storage_module, "get_r2_client", lambda: client)

    stored_asset = await storage.save_document_upload(
        company_id=company_id,
        document_id=document_id,
        file=upload,
    )

    expected_key = f"companies/{company_id}/documents/{document_id}/source.txt"

    assert stored_asset.object_key == expected_key
    assert stored_asset.storage_path == f"r2://archyve-dev/{expected_key}"
    assert stored_asset.bucket_name == "archyve-dev"
    assert client.calls == [
        {
            "bucket_name": "archyve-dev",
            "object_key": expected_key,
            "extra_args": {"ContentType": "text/plain"},
            "body": b"hello from r2",
        }
    ]
