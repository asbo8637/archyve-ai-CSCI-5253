from __future__ import annotations

from functools import lru_cache
from typing import Protocol, Sequence

import google.generativeai as genai

from archyve_common.settings import get_settings


class EmbeddingsClient(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


class GeminiEmbeddingsClient:
    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            genai.embed_content(model="models/text-embedding-004", content=text)["embedding"]
            for text in texts
        ]


@lru_cache(maxsize=1)
def get_embeddings_client() -> GeminiEmbeddingsClient:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return GeminiEmbeddingsClient(settings.gemini_api_key)
