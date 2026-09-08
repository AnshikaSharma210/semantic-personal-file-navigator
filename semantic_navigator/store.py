from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from semantic_navigator.bm25 import BM25Index
from semantic_navigator.chunking import chunk_document
from semantic_navigator.config import SETTINGS
from semantic_navigator.guardrails import is_allowed_filename, sanitize_filename
from semantic_navigator.ingest import extract_text
from semantic_navigator.models import FileRecord


def _embeddings() -> Embeddings:
    provider = SETTINGS.embedding_provider
    if provider == "openai" and SETTINGS.openai_api_key:
        from langchain_openai import OpenAIEmbeddings  # noqa: PLC0415

        return OpenAIEmbeddings(
            model=SETTINGS.openai_embedding_model,
            api_key=SETTINGS.openai_api_key,
        )
    from langchain_community.embeddings import HuggingFaceEmbeddings  # noqa: PLC0415

    return HuggingFaceEmbeddings(model_name=SETTINGS.local_embedding_model)


class FileLibrary:
    """Per-user FAISS index + file metadata. Isolated by library_id."""

    def __init__(self, library_id: str) -> None:
        safe = "".join(c for c in library_id if c.isalnum() or c in "-_")[:64] or "local"
        self.root = SETTINGS.data_dir / "libraries" / safe
        self.root.mkdir(parents=True, exist_ok=True)
        self._meta_path = self.root / "files.json"
        self._index_dir = self.root / "faiss"
        self._embeddings: Embeddings | None = None
        self._store: FAISS | None = None
        self.bm25 = BM25Index(self.root / "bm25.json")
        self.files: dict[str, FileRecord] = self._load_meta()
        self._load_index()

    def _emb(self) -> Embeddings:
        if self._embeddings is None:
            self._embeddings = _embeddings()
        return self._embeddings

    def _load_meta(self) -> dict[str, FileRecord]:
        if not self._meta_path.exists():
            return {}
        raw = json.loads(self._meta_path.read_text(encoding="utf-8"))
        return {k: FileRecord.model_validate(v) for k, v in raw.items()}

    def _save_meta(self) -> None:
        payload = {k: v.model_dump() for k, v in self.files.items()}
        self._meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_index(self) -> None:
        if (self._index_dir / "index.faiss").exists():
            self._store = FAISS.load_local(
                str(self._index_dir),
                self._emb(),
                allow_dangerous_deserialization=True,
            )

    def _persist_index(self) -> None:
        if self._store:
            self._index_dir.mkdir(parents=True, exist_ok=True)
            self._store.save_local(str(self._index_dir))

    @property
    def is_ready(self) -> bool:
        return self._store is not None and bool(self.files)

    def add_local(self, filename: str, data: bytes, source_path: str = "") -> FileRecord:
        """Index a file from the local filesystem (no size cap, higher file limit)."""
        name = sanitize_filename(filename)
        if not is_allowed_filename(name):
            raise ValueError("Only PDF, TXT, MD, and DOCX files are allowed.")
        # Skip if already indexed by name
        if any(r.filename == name for r in self.files.values()):
            raise ValueError("already indexed")
        text = extract_text(name, data)
        file_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        docs = chunk_document(text, filename=name, file_id=file_id)
        if not docs:
            raise ValueError("Nothing useful could be indexed from this file.")
        if self._store is None:
            self._store = FAISS.from_documents(docs, self._emb())
        else:
            self._store.add_documents(docs)
        rec = FileRecord(
            file_id=file_id,
            filename=name,
            ext=Path(name).suffix.lower(),
            size_bytes=len(data),
            added_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            chunk_count=len(docs),
            source_path=source_path,
        )
        self.files[file_id] = rec
        self._save_meta()
        self._persist_index()
        # populate BM25
        self.bm25.add_chunks([
            {"chunk_id": d.metadata["chunk_id"], "file_id": file_id,
             "filename": name, "text": d.page_content}
            for d in docs
        ])
        return rec

    def add_upload(self, filename: str, data: bytes) -> FileRecord:
        if len(self.files) >= SETTINGS.max_files:
            raise ValueError(f"Library is full (max {SETTINGS.max_files} files). Remove some first.")
        if len(data) > SETTINGS.max_upload_bytes:
            mb = SETTINGS.max_upload_bytes // (1024 * 1024)
            raise ValueError(f"File exceeds the {mb} MB limit.")
        name = sanitize_filename(filename)
        if not is_allowed_filename(name):
            raise ValueError("Only PDF, TXT, MD, and DOCX files are allowed.")
        text = extract_text(name, data)
        file_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        docs = chunk_document(text, filename=name, file_id=file_id)
        if not docs:
            raise ValueError("Nothing useful could be indexed from this file.")
        if self._store is None:
            self._store = FAISS.from_documents(docs, self._emb())
        else:
            self._store.add_documents(docs)
        rec = FileRecord(
            file_id=file_id,
            filename=name,
            ext=Path(name).suffix.lower(),
            size_bytes=len(data),
            added_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            chunk_count=len(docs),
        )
        self.files[file_id] = rec
        self._save_meta()
        self._persist_index()
        # populate BM25
        self.bm25.add_chunks([
            {"chunk_id": d.metadata["chunk_id"], "file_id": file_id,
             "filename": name, "text": d.page_content}
            for d in docs
        ])
        return rec

    def search(self, query: str, k: int) -> list[Document]:
        if not self._store:
            return []
        return self._store.similarity_search_with_score(query, k=k)

    def clear(self) -> None:
        self.files = {}
        self._store = None
        self.bm25.clear()
        self._save_meta()
        for p in self._index_dir.glob("*"):
            p.unlink(missing_ok=True)
