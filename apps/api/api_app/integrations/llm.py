from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol, Sequence

import google.generativeai as genai

from archyve_common.settings import get_settings


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


class GeminiEmbeddingsClient:
    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            genai.embed_content(model="models/text-embedding-004", content=text)["embedding"]
            for text in texts
        ]


class GeminiAnswerGenerationClient:
    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel("gemini-2.0-flash")

    def answer_question(self, request: AnswerRequest) -> AnswerResult:
        context = "\n\n".join(
            f"[{chunk.source_label}]\n{chunk.content}"
            for chunk in request.context_chunks
        )
        prompt = (
            "You are a helpful assistant. Answer the question using only the provided context. "
            "If the context does not contain enough information, say so.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {request.question}\n\n"
            "Answer:"
        )
        response = self._model.generate_content(prompt)
        sources = tuple(dict.fromkeys(c.source_label for c in request.context_chunks))
        return AnswerResult(answer=response.text, cited_sources=sources)


@lru_cache(maxsize=1)
def get_embeddings_client() -> GeminiEmbeddingsClient:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return GeminiEmbeddingsClient(settings.gemini_api_key)


@lru_cache(maxsize=1)
def get_answer_client() -> GeminiAnswerGenerationClient:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return GeminiAnswerGenerationClient(settings.gemini_api_key)
