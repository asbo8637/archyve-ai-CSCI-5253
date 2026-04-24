from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text_from_path(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return extract_pdf_text(file_path)

    if suffix == ".docx":
        return extract_docx_text(file_path)

    return file_path.read_text(encoding="utf-8", errors="ignore")


def extract_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page.strip() for page in pages if page.strip())


def extract_docx_text(file_path: Path) -> str:
    document = DocxDocument(str(file_path))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
    return "\n".join(text for text in paragraphs if text)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(end - overlap, 0)

    return [chunk for chunk in chunks if chunk]


def estimate_token_count(text: str) -> int:
    return max(1, len(text.split()))

