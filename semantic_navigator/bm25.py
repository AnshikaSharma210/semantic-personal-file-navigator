"""
BM25 keyword index — exact-match counterpart to FAISS semantic search.

Persisted alongside the FAISS index so it survives restarts.
Merged with FAISS scores in retrieve.py (hybrid RRF fusion).
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens, keep hyphens inside words (e.g. IIA-24)."""
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())


class BM25Index:
    """
    Lightweight BM25 over document chunks.
    k1=1.5, b=0.75 (standard defaults).
    """

    K1 = 1.5
    B  = 0.75

    def __init__(self, store_path: Path) -> None:
        self._path = store_path
        # chunk_id → {"file_id", "filename", "text", "tokens": Counter}
        self._docs:   dict[str, dict] = {}
        self._idf:    dict[str, float] = {}
        self._avgdl:  float = 0.0
        if store_path.exists():
            self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        # Store only what's needed to reconstruct (not the full token counters)
        payload = {
            "docs": {
                cid: {
                    "file_id":  d["file_id"],
                    "filename": d["filename"],
                    "tokens":   dict(d["tokens"]),
                    "length":   d["length"],
                }
                for cid, d in self._docs.items()
            }
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload), encoding="utf-8")

    def _load(self) -> None:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._docs = {
                cid: {**d, "tokens": Counter(d["tokens"])}
                for cid, d in raw.get("docs", {}).items()
            }
            self._recompute()
        except Exception:
            self._docs = {}

    # ── Indexing ──────────────────────────────────────────────────────────────

    def add_chunks(self, chunks: list[dict]) -> None:
        """
        chunks: list of {"chunk_id", "file_id", "filename", "text"}
        """
        for c in chunks:
            toks = _tokenize(c["text"])
            self._docs[c["chunk_id"]] = {
                "file_id":  c["file_id"],
                "filename": c["filename"],
                "tokens":   Counter(toks),
                "length":   len(toks),
            }
        self._recompute()
        self._save()

    def remove_by_file(self, file_id: str) -> None:
        self._docs = {cid: d for cid, d in self._docs.items() if d["file_id"] != file_id}
        self._recompute()
        self._save()

    def clear(self) -> None:
        self._docs = {}
        self._idf = {}
        self._avgdl = 0.0
        self._save()

    def _recompute(self) -> None:
        N = len(self._docs)
        if N == 0:
            self._idf = {}
            self._avgdl = 0.0
            return
        self._avgdl = sum(d["length"] for d in self._docs.values()) / N
        # DF: how many docs contain each term
        df: dict[str, int] = defaultdict(int)
        for d in self._docs.values():
            for t in d["tokens"]:
                df[t] += 1
        self._idf = {
            t: math.log((N - n + 0.5) / (n + 0.5) + 1.0)
            for t, n in df.items()
        }

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, k: int = 20) -> list[tuple[str, str, str, float]]:
        """
        Returns list of (chunk_id, file_id, filename, bm25_score), sorted desc.
        """
        q_tokens = _tokenize(query)
        if not q_tokens or not self._docs:
            return []

        scores: dict[str, float] = {}
        for cid, d in self._docs.items():
            dl   = d["length"]
            toks = d["tokens"]
            sc   = 0.0
            for t in q_tokens:
                if t not in toks:
                    continue
                idf = self._idf.get(t, 0.0)
                tf  = toks[t]
                sc += idf * (tf * (self.K1 + 1)) / (
                    tf + self.K1 * (1 - self.B + self.B * dl / max(self._avgdl, 1))
                )
            if sc > 0:
                scores[cid] = sc

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return [
            (cid, self._docs[cid]["file_id"], self._docs[cid]["filename"], sc)
            for cid, sc in ranked
        ]
