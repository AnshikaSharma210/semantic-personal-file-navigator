from __future__ import annotations

from pydantic import BaseModel, Field


class FileRecord(BaseModel):
    file_id: str
    filename: str
    ext: str
    size_bytes: int
    added_at: str
    chunk_count: int = 0
    source_path: str = ""  # full disk path, only set for locally-scanned files


class RetrievedChunk(BaseModel):
    file_id: str
    filename: str
    section: str
    page_hint: str
    score: float
    text: str


class SearchHit(BaseModel):
    filename: str
    file_id: str
    relevance: int = Field(ge=0, le=100)
    why: str
    excerpts: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)


class SearchAnswer(BaseModel):
    query: str
    intent: str
    hits: list[SearchHit]
    answer: str
    used_llm: bool = False
    blocked: bool = False
    block_reason: str = ""
