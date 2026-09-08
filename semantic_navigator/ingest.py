from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _pdf(data)
    if ext == ".docx":
        return _docx(data)
    if ext in {".txt", ".md"}:
        return data.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {ext}")


def _pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"[page {i}]\n{text}")
    if not pages:
        raise ValueError("No readable text in this PDF (it may be a scan).")
    return "\n\n".join(pages)


def _docx(data: bytes) -> str:
    from docx import Document  # noqa: PLC0415

    doc = Document(io.BytesIO(data))
    parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    if not parts:
        raise ValueError("No readable text in this Word file.")
    return "\n".join(parts)
