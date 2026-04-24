from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from archyve_common.settings import get_settings

UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StoredDocumentAsset:
    object_key: str
    storage_path: str


class LocalDocumentStorage:
    async def save_document_upload(
        self,
        *,
        company_id: UUID,
        document_id: UUID,
        file: UploadFile,
    ) -> StoredDocumentAsset:
        settings = get_settings()
        settings.storage_root_path.mkdir(parents=True, exist_ok=True)

        extension = Path(file.filename or "").suffix
        object_key = f"companies/{company_id}/documents/{document_id}/source{extension}"
        target_path = settings.storage_root_path / object_key
        target_path.parent.mkdir(parents=True, exist_ok=True)

        await file.seek(0)
        with target_path.open("wb") as buffer:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE_BYTES):
                buffer.write(chunk)

        return StoredDocumentAsset(object_key=object_key, storage_path=str(target_path))


def get_document_storage() -> LocalDocumentStorage:
    return LocalDocumentStorage()
