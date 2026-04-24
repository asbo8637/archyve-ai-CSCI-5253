from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator, Protocol

import boto3

from archyve_common.models import Document
from archyve_common.settings import get_settings


class DocumentStorageResolver(Protocol):
    def materialize(self, document: Document) -> Iterator[Path]: ...


class LocalDocumentStorageResolver:
    @contextmanager
    def materialize(self, document: Document) -> Iterator[Path]:
        yield Path(document.storage_path)


class R2DocumentStorageResolver:
    @contextmanager
    def materialize(self, document: Document) -> Iterator[Path]:
        settings = get_settings()
        bucket_name = document.r2_bucket or settings.r2_bucket
        if bucket_name is None or document.r2_key is None:
            raise RuntimeError("Document is missing R2 metadata.")

        suffix = Path(document.filename).suffix
        with NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            temp_path = Path(handle.name)
            get_r2_client().download_fileobj(bucket_name, document.r2_key, handle)

        try:
            yield temp_path
        finally:
            temp_path.unlink(missing_ok=True)


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


def get_document_storage_resolver(document: Document) -> DocumentStorageResolver:
    if (
        document.r2_key is not None
        or document.r2_bucket is not None
        or document.storage_path.startswith("r2://")
    ):
        return R2DocumentStorageResolver()

    return LocalDocumentStorageResolver()
