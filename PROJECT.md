# Project record — Semantic Personal File Navigator

This document is the source of truth for what exists in the repo, why it was built this way, and what a new reader should not expect.

## Problem

People do not lose files because search is slow. They lose them because they search by *name* while they remember *meaning* (“the Q3 deck for finance”). Keyword search fails across PDFs, Word notes, and exports sitting on a phone.

## Product decision

A **hosted** navigator that works on phones and laptops must use **explicit file add**, not full-disk crawl.

| Device | What the user does | What the agent does |
|---|---|---|
| Phone | Pick files from Files / Drive / Downloads | Index + semantic retrieve |
| Laptop | Multi-select from a folder | Same pipeline, same library key |
| Shared URL | Each person types a private library key | Isolated FAISS + metadata on disk |

Full-disk indexing would require a native desktop/mobile installer with OS permissions. That is a different product. This repo is the shareable web agent.

## What was implemented

### Ingest and context engineering
- `semantic_navigator/ingest.py` — PDF (page-tagged), DOCX, TXT/MD extraction.
- `semantic_navigator/chunking.py` — recursive split, overlap, section/page metadata, injection strip.
- `semantic_navigator/store.py` — per-library FAISS persist under `.data/libraries/<hash>/`.

### Retrieval
- `semantic_navigator/retrieve.py` — query validation, similarity search, score → %, group by file, excerpts.
- `semantic_navigator/agent.py` — intent label, heuristic answer, optional OpenAI phrasing locked to `SYSTEM_SCOPE`.

### Guardrails
- `semantic_navigator/guardrails.py` — filename sanitisation, extension allowlist, out-of-scope / jailbreak regex, document-injection strip, fixed system prompt.

### UI
- `streamlit_app.py` — Library (upload + list), Search (ranked hits), How it works (honest limits).
- `.streamlit/config.toml` — 8 MB upload cap, dark theme, no Streamlit footer.

### Config
- `config.py` reads `.env` then `st.secrets`.
- Defaults stay free (`EMBEDDING_PROVIDER=local`).

## What was deliberately not built

- Silent scanning of Photos, WhatsApp, or `C:\`.
- Auto-apply / file delete / file move.
- Cross-user “admin view” of libraries.
- Unrestricted chat.

## How to extend later (same guardrails)

1. **Native companion is already built** — `local_scan.py` walks Desktop / Documents / Downloads / OneDrive and indexes everything into the same FAISS library. Run it once; new files are added incrementally on re-runs.
2. Optional account (Supabase) instead of a library key — still one index per user.
3. OCR for scanned PDFs — still text-only after extract; same chunk pipeline.

## File map

```
streamlit_app.py
semantic_navigator/
  config.py
  models.py
  guardrails.py
  ingest.py
  chunking.py
  store.py
  retrieve.py
  agent.py
PROJECT.md          ← this file
README.md
```

## Stack claimed on a resume (accurate)

Python · LangChain · FAISS · OpenAI embeddings (optional) · local MiniLM embeddings · RAG · context engineering (chunk + metadata + intent-scoped retrieval) · Streamlit.
