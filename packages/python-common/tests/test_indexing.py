import pytest

from archyve_common.indexing import chunk_text, estimate_token_count, extract_docx_text


def test_chunk_text_creates_overlapping_chunks() -> None:
    sample = " ".join(["archived"] * 600)
    chunks = chunk_text(sample, chunk_size=120, overlap=20)

    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)


def test_estimate_token_count_uses_word_boundaries() -> None:
    assert estimate_token_count("one two three") == 3


def test_extract_docx_text_requires_a_valid_file(tmp_path) -> None:
    sample = tmp_path / "sample.docx"
    sample.write_bytes(b"not-a-real-docx")

    with pytest.raises(Exception):
        extract_docx_text(sample)
