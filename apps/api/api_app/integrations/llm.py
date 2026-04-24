from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    source_label: str


@dataclass(frozen=True)
class AnswerRequest:
    question: str
    context_chunks: tuple[RetrievedChunk, ...]


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    cited_sources: tuple[str, ...]


class EmbeddingsClient(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


class AnswerGenerationClient(Protocol):
    def answer_question(self, request: AnswerRequest) -> AnswerResult: ...
