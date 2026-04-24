from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from uuid import UUID

import boto3
from fastapi import UploadFile

from archyve_common.settings import get_settings

UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StoredDocumentAsset:
    object_key: str
    storage_path: str
    bucket_name: str | None = None


class DocumentStorage(Protocol):
    async def save_document_upload(
        self,
        *,
        company_id: UUID,
        document_id: UUID,
        file: UploadFile,
    ) -> StoredDocumentAsset: ...


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

        return StoredDocumentAsset(
            object_key=object_key,
            storage_path=str(target_path),
        )


class R2DocumentStorage:
    async def save_document_upload(
        self,
        *,
        company_id: UUID,
        document_id: UUID,
        file: UploadFile,
    ) -> StoredDocumentAsset:
        settings = get_settings()
        bucket_name = settings.r2_bucket
        if bucket_name is None:
            raise RuntimeError("R2 bucket is not configured.")

        extension = Path(file.filename or "").suffix
        object_key = f"companies/{company_id}/documents/{document_id}/source{extension}"

        await file.seek(0)
        extra_args = {"ContentType": file.content_type} if file.content_type else None
        client = get_r2_client()
        if extra_args is None:
            client.upload_fileobj(file.file, bucket_name, object_key)
        else:
            client.upload_fileobj(
                file.file,
                bucket_name,
                object_key,
                ExtraArgs=extra_args,
            )

        return StoredDocumentAsset(
            object_key=object_key,
            storage_path=f"r2://{bucket_name}/{object_key}",
            bucket_name=bucket_name,
        )


@lru_cache(maxsize=1)
def get_r2_client():
    settings = get_settings()
    if not settings.r2_configured:
        raise RuntimeError("R2 storage is not fully configured.")

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def get_document_storage() -> DocumentStorage:
    settings = get_settings()
    if settings.r2_configured:
        return R2DocumentStorage()

    return LocalDocumentStorage()
