from __future__ import annotations

from semantic_navigator.config import SETTINGS
from semantic_navigator.guardrails import SYSTEM_SCOPE, infer_intent
from semantic_navigator.models import SearchAnswer
from semantic_navigator.retrieve import empty_answer, group_hits, retrieve
from semantic_navigator.store import FileLibrary


def search_library(library: FileLibrary, query: str) -> SearchAnswer:
    if not library.is_ready:
        return empty_answer(query, "Upload at least one document before searching.")

    chunks, blocked = retrieve(library, query)
    if blocked:
        return empty_answer(query, blocked, blocked=True)
    if not chunks:
        return empty_answer(query, "Nothing in your library matched that request.")

    hits = group_hits(chunks)
    if not hits:
        return empty_answer(query, "Nothing in your library matched that request.")

    answer = _compose_answer(query, hits)
    used_llm = False
    if SETTINGS.openai_api_key:
        try:
            answer = _llm_answer(query, chunks[:8])
            used_llm = True
        except Exception:
            used_llm = False

    return SearchAnswer(
        query=query,
        intent=infer_intent(query),
        hits=hits,
        answer=answer,
        used_llm=used_llm,
    )


def _compose_answer(query: str, hits) -> str:
    top = hits[0]
    extras = ", ".join(h.filename for h in hits[1:3])
    line = f"Best match for “{query}” is **{top.filename}** ({top.relevance}% relevance — {top.why})."
    if extras:
        line += f" Also consider: {extras}."
    return line


def _llm_answer(query: str, chunks) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage  # noqa: PLC0415
    from langchain_openai import ChatOpenAI  # noqa: PLC0415

    context = "\n\n---\n\n".join(
        f"FILE: {c.filename} | SECTION: {c.section}\n{c.text[:700]}" for c in chunks
    )
    llm = ChatOpenAI(
        model=SETTINGS.openai_chat_model,
        api_key=SETTINGS.openai_api_key,
        temperature=0,
        max_tokens=280,
    )
    resp = llm.invoke(
        [
            SystemMessage(content=SYSTEM_SCOPE),
            HumanMessage(
                content=(
                    f"User request: {query}\n\n"
                    f"Retrieved excerpts (only source of truth):\n{context}\n\n"
                    "Reply in 2–4 sentences: which file(s) to open and why. "
                    "Quote a short phrase from an excerpt if useful. "
                    "If excerpts are unrelated, say you cannot find it."
                )
            ),
        ]
    )
    return str(resp.content).strip()
