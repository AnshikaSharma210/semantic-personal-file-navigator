from __future__ import annotations

from collections import defaultdict

from semantic_navigator.config import SETTINGS
from semantic_navigator.guardrails import infer_intent, strip_document_injections, validate_query
from semantic_navigator.models import RetrievedChunk, SearchAnswer, SearchHit
from semantic_navigator.store import FileLibrary

_RRF_K = 60  # standard RRF constant


def retrieve(library: FileLibrary, query: str) -> tuple[list[RetrievedChunk], str]:
    blocked = validate_query(query)
    if blocked:
        return [], blocked

    k_fetch = min(24, SETTINGS.max_results * 4)

    # ── FAISS semantic search ─────────────────────────────────────────────────
    faiss_raw = library.search(query, k=k_fetch)
    # Map chunk_id → (doc, semantic_rel_score)
    faiss_by_id: dict[str, tuple] = {}
    for item in faiss_raw:
        doc, score = item if isinstance(item, tuple) else (item, 0.0)
        chunk_id = str(doc.metadata.get("chunk_id", doc.metadata.get("file_id", "")))
        rel = max(0.0, 1.0 - float(score) / 2.0)
        faiss_by_id[chunk_id] = (doc, rel)

    # ── BM25 keyword search ───────────────────────────────────────────────────
    bm25_results = library.bm25.search(query, k=k_fetch)
    # Normalise BM25 scores to 0–1
    max_bm25 = bm25_results[0][3] if bm25_results else 1.0
    bm25_by_id: dict[str, float] = {
        cid: score / max(max_bm25, 1e-9)
        for cid, _fid, _fn, score in bm25_results
    }

    # ── Reciprocal Rank Fusion ────────────────────────────────────────────────
    # Rank positions (1-based)
    faiss_rank = {cid: i + 1 for i, (cid, _) in enumerate(faiss_by_id.items())}
    bm25_rank  = {r[0]: i + 1 for i, r in enumerate(bm25_results)}

    all_ids = set(faiss_by_id) | set(bm25_by_id)
    rrf: dict[str, float] = {}
    for cid in all_ids:
        r_f = faiss_rank.get(cid, k_fetch + 1)
        r_b = bm25_rank.get(cid, k_fetch + 1)
        rrf[cid] = 1.0 / (_RRF_K + r_f) + 1.0 / (_RRF_K + r_b)

    # ── Build RetrievedChunk list ─────────────────────────────────────────────
    chunks: list[RetrievedChunk] = []
    for cid, rrf_score in sorted(rrf.items(), key=lambda x: x[1], reverse=True):
        # Prefer semantic score for display; fall back to BM25 normalised score
        if cid in faiss_by_id:
            doc, sem_rel = faiss_by_id[cid]
            # Blend: 60 % semantic + 40 % BM25 when both exist
            bm25_rel = bm25_by_id.get(cid, 0.0)
            blend = 0.6 * sem_rel + 0.4 * bm25_rel if bm25_rel else sem_rel
            chunks.append(RetrievedChunk(
                file_id=str(doc.metadata.get("file_id", "")),
                filename=str(doc.metadata.get("filename", "unknown")),
                section=str(doc.metadata.get("section", "body")),
                page_hint=str(doc.metadata.get("page_hint", "")),
                score=blend,
                text=strip_document_injections(doc.page_content),
            ))
        else:
            # BM25-only hit — look up metadata from bm25 index
            entry = next((r for r in bm25_results if r[0] == cid), None)
            if not entry:
                continue
            _, file_id, filename, _ = entry
            bm25_rel = bm25_by_id[cid]
            chunks.append(RetrievedChunk(
                file_id=file_id,
                filename=filename,
                section="body",
                page_hint="",
                score=bm25_rel * 0.7,   # BM25-only: slight discount
                text="",
            ))

    # Hard cut: drop chunks below 0.30
    chunks = [c for c in chunks if c.score >= 0.30]
    return chunks, ""


def group_hits(chunks: list[RetrievedChunk]) -> list[SearchHit]:
    by_file: dict[str, list[RetrievedChunk]] = defaultdict(list)
    for c in chunks:
        by_file[c.file_id].append(c)

    hits: list[SearchHit] = []
    for file_id, group in by_file.items():
        group.sort(key=lambda c: c.score, reverse=True)
        top = group[0]
        excerpts = [g.text.strip()[:320] for g in group[:3] if g.text.strip()]
        sections = list(dict.fromkeys(g.section for g in group if g.section))
        why_bits = []
        if top.section and top.section != "body":
            why_bits.append(f"matched section \"{top.section}\"")
        if top.page_hint:
            why_bits.append(f"page {top.page_hint}")
        why_bits.append(f"{len(group)} relevant passage(s)")
        hits.append(SearchHit(
            filename=top.filename,
            file_id=file_id,
            relevance=min(99, max(0, int(top.score * 100))),
            why=" · ".join(why_bits),
            excerpts=excerpts,
            sections=sections[:4],
        ))

    hits.sort(key=lambda h: h.relevance, reverse=True)
    # Drop file-level hits below 35 %
    hits = [h for h in hits if h.relevance >= 35]
    # If even the top hit isn't confident, return nothing
    if hits and hits[0].relevance < 45:
        return []
    return hits[: SETTINGS.max_results]


def empty_answer(query: str, reason: str, *, blocked: bool = False) -> SearchAnswer:
    return SearchAnswer(
        query=query,
        intent=infer_intent(query) if query else "",
        hits=[],
        answer=reason,
        blocked=blocked,
        block_reason=reason if blocked else "",
    )
