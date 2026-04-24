from __future__ import annotations

from typing import Protocol

from archyve_common.messages import ProcessDocumentJobPayload


class DocumentIndexingMessageSource(Protocol):
    def pull(self) -> ProcessDocumentJobPayload | None: ...
