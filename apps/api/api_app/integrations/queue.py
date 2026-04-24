from archyve_common.messages import ProcessDocumentJobPayload


class NoopDispatcher:
    def dispatch(self, message: ProcessDocumentJobPayload) -> None:
        pass


def get_document_indexing_dispatcher() -> NoopDispatcher:
    return NoopDispatcher()
