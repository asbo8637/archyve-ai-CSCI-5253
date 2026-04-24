from __future__ import annotations

from typing import Protocol

from archyve_common.messages import ProcessDocumentJobPayload


class DocumentIndexingDispatcher(Protocol):
    def dispatch(self, message: ProcessDocumentJobPayload) -> None: ...


class DatabasePollingDispatcher:
    def dispatch(self, message: ProcessDocumentJobPayload) -> None:
        # The bootstrap worker polls the jobs table directly.
        # This hook exists so Pub/Sub can replace the no-op dispatcher later.
        return None


def get_document_indexing_dispatcher() -> DocumentIndexingDispatcher:
    return DatabasePollingDispatcher()
