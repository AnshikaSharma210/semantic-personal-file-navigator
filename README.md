# Semantic Personal File Navigator

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-green)](https://python.langchain.com/)
[![FAISS](https://img.shields.io/badge/Vector%20Store-FAISS-orange)](https://faiss.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

AI-powered file search for people who remember *what* a document was about, not *where* they saved it. Ask “find my Q3 report” and the agent ranks the most relevant files from **your** library — phones and laptops included, without ever scanning the whole device.

---

## What it does

You add the documents you care about (from Files on iOS, Downloads on Android, or a folder on a laptop). The agent chunks them, tags metadata, embeds them, and stores vectors in FAISS. A natural-language query is context-engineered against that index so the first results are the files that match *intent*, not keyword coincidence.

**Useful when**
- Reports, contracts, and notes live across WhatsApp, email, and Desktop.
- You need the right PDF in seconds, not a filename guess.
- Several people should each keep a **private** library on the same hosted app.

---

## Tech stack

| Layer | Choice |
|---|---|
| UI | Streamlit (dark theme, mobile-usable uploader + search) |
| Orchestration | LangChain documents + text splitters |
| Embeddings | `all-MiniLM-L6-v2` locally (default) or OpenAI `text-embedding-3-small` |
| Vector store | FAISS, persisted per library |
| Optional phrasing | OpenAI chat — *only* over retrieved excerpts |
| Guardrails | Query allowlist, document injection strip, library isolation, file-type / size caps |

---

## How search works

```
upload → extract text → chunk + metadata
      → embed → FAISS
query → scope check → embed query
      → ranked passages → group by file → answer
```

Context engineering: each chunk carries `filename`, `section`, `page`, and `file_id`. Retrieval is passage-level; the UI presents **documents** with why they matched.

---

## Guardrails (cannot be talked out of scope)

- Answers only from the signed-in library. No web browse, no shell, no general chat.
- Queries that look like jailbreaks or code execution are refused.
- Instruction-like lines inside uploaded files are stripped before indexing and before the LLM sees them.
- Allowed types: PDF, DOCX, TXT, MD. Size and file-count caps are enforced.
- Libraries are keyed by a private phrase (hashed). Different keys never share an index.

A website **cannot** index an entire phone or laptop disk. That is an OS/browser rule, not a missing feature. Users pick files; the agent makes them findable.

---

## Run locally (laptop with full-disk search)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
```

**Step 1 — index your laptop files (one command)**
```bash
python local_scan.py
```
Walks Desktop, Documents, Downloads, and OneDrive. Skips files already indexed. Re-run any time to pick up new files.

**Step 2 — search**
```bash
# In the UI:
streamlit run streamlit_app.py
# Or directly from terminal:
python local_scan.py --search "find my Q3 report"
```

Use library key `local-laptop` in the sidebar (matches what `local_scan.py` uses by default).

**Dry run to preview what would be indexed:**
```bash
python local_scan.py --dry-run
```

---

## Host and share

Deploy `streamlit_app.py` on Streamlit Community Cloud (or any Python host). Each person uses their own library key. Put optional secrets in the host dashboard, never in git.

See **[PROJECT.md](./PROJECT.md)** for what was built, file-by-file, and the product constraints.

---

## License

MIT
