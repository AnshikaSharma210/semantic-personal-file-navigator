# Semantic Personal File Navigator

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-green)](https://python.langchain.com/)
[![FAISS](https://img.shields.io/badge/Vector%20Store-FAISS-orange)](https://faiss.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

AI-powered semantic search over your own files — find any document by describing what's in it, not by remembering its name.

> **Runs entirely on your laptop. Your files never leave your machine.**

---

## Quickstart (Windows)

1. [Download or clone this repo](https://github.com/AnshikaSharma210/semantic-personal-file-navigator)
2. Double-click **`setup.bat`**
3. Browser opens automatically at `localhost:8501`
4. Add a folder (Desktop, Documents, Downloads) — files are indexed in the background
5. Search in plain English: *"find my offer letter"*, *"HLD for project Muse"*, *"Q3 report"*

> First run installs dependencies (~2 min). Every run after that opens instantly.

---

## What it does

Point it at any folder on your machine. It reads every PDF, Word doc, text file, and Markdown file, splits them into chunks, embeds them using a local AI model, and stores the index on disk. When you search, it finds files by *meaning* — not just filename or keyword.

**Built for situations like:**
- You remember writing something about a topic but not what the file was called
- You have hundreds of downloads and need one specific document fast
- You want instant search across work docs, notes, contracts, and reports — all in one place

---

## Tech stack

| Layer | Choice |
|---|---|
| UI | Streamlit — dark aurora theme, runs in browser |
| Search | Hybrid: FAISS semantic (MiniLM) + BM25 keyword — fused via RRF |
| Embeddings | `all-MiniLM-L6-v2` — runs locally, no API key needed |
| Vector store | FAISS, persisted to disk per session |
| File watching | `watchdog` — auto-indexes new files dropped into watched folders |
| Guardrails | Query scope check, document injection strip, file-type/size caps |
| Optional LLM | OpenAI GPT — only for summarising retrieved excerpts (not required) |

---

## How search works

```
folder watch → extract text → chunk + metadata tag
             → embed (local MiniLM) → FAISS + BM25 index on disk

query → validate → embed query
      → FAISS semantic search + BM25 keyword search
      → RRF fusion → rank by relevance → show files + excerpts
```

Two engines run in parallel for every search:
- **FAISS** handles natural language — *"salary negotiation email"*
- **BM25** handles exact codes and names — *"CR-24471"*, *"Muse HLD"*

Results only show when the top match exceeds a confidence threshold — no guessing.

---

## Guardrails

- Files stay on your disk. Nothing is uploaded anywhere.
- Queries that look like jailbreaks or code execution are refused.
- Text injected inside documents (*"ignore previous instructions…"*) is stripped before indexing.
- Supported types: PDF, DOCX, TXT, MD.
- Index survives restarts — no re-indexing needed.

---

## Auto-start on Windows login

Run once to make it start silently in the background on every login:

```bash
python install_startup.py
# To remove:
python install_startup.py remove
```

After that, just open `http://localhost:8501` whenever you need to search.

---

## Manual setup (Mac / Linux / advanced)

```bash
git clone https://github.com/AnshikaSharma210/semantic-personal-file-navigator
cd semantic-personal-file-navigator
pip install -r requirements.txt
python run.py
```

---

See **[PROJECT.md](./PROJECT.md)** for architecture decisions and what was deliberately left out.

---

## License

MIT
