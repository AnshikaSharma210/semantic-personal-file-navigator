from __future__ import annotations

import hashlib
import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from semantic_navigator.config import SETTINGS
from semantic_navigator.guardrails import strip_document_injections

_HEADING = re.compile(
    r"(?im)^(?:#{1,3}\s+|[A-Z][A-Z0-9 /&-]{3,40}$|"
    r"(?:summary|experience|education|skills|projects|introduction|"
    r"abstract|conclusion|appendix|q[1-4]|quarter|financials|notes)\b.*)"
)


def _section_hint(chunk: str) -> str:
    first = chunk.strip().splitlines()[0][:80] if chunk.strip() else ""
    m = _HEADING.match(first)
    if m:
        return first.strip("# ").strip()[:60]
    if first.lower().startswith("[page "):
        return first.strip("[]")
    return "body"


def chunk_document(text: str, *, filename: str, file_id: str) -> list[Document]:
    cleaned = strip_document_injections(text)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SETTINGS.max_chunk_chars,
        chunk_overlap=140,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    docs: list[Document] = []
    for i, piece in enumerate(splitter.split_text(cleaned)):
        page = ""
        pm = re.search(r"\[page (\d+)\]", piece)
        if pm:
            page = pm.group(1)
        sid = hashlib.sha256(f"{file_id}:{i}:{piece[:80]}".encode()).hexdigest()[:16]
        docs.append(
            Document(
                page_content=piece,
                metadata={
                    "chunk_id": sid,
                    "file_id": file_id,
                    "filename": filename,
                    "section": _section_hint(piece),
                    "page_hint": page,
                    "source": filename,
                },
            )
        )
    return docs
