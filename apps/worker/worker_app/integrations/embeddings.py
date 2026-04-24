from __future__ import annotations

from typing import Protocol, Sequence


class EmbeddingsClient(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...
