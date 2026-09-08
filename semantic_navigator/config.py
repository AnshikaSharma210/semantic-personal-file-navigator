from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True, encoding="utf-8-sig")


def _env(name: str, default: str = "") -> str:
    val = os.getenv(name, "").strip()
    if val:
        return val
    try:
        import streamlit as st  # noqa: PLC0415

        secret = st.secrets.get(name, "")
        if secret:
            return str(secret).strip()
    except Exception:
        pass
    return default


@dataclass(frozen=True)
class Settings:
    embedding_provider: str
    local_embedding_model: str
    openai_api_key: str | None
    openai_embedding_model: str
    openai_chat_model: str
    max_upload_bytes: int
    max_files: int
    max_chunk_chars: int
    max_results: int
    data_dir: Path


def _build() -> Settings:
    return Settings(
        embedding_provider=(_env("EMBEDDING_PROVIDER", "local") or "local").lower(),
        local_embedding_model=_env("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        openai_api_key=_env("OPENAI_API_KEY") or None,
        openai_embedding_model=_env("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        openai_chat_model=_env("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        max_upload_bytes=int(_env("MAX_UPLOAD_MB", "8")) * 1024 * 1024,
        max_files=int(_env("MAX_FILES_PER_LIBRARY", "200")),
        max_chunk_chars=int(_env("MAX_CHUNK_CHARS", "900")),
        max_results=int(_env("MAX_RESULTS", "8")),
        data_dir=_ROOT / ".data",
    )


SETTINGS = _build()
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
ALLOWED_MIME_HINTS = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
