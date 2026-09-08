"""
local_scan.py — Desktop companion for Semantic Personal File Navigator.

Run this on your laptop to auto-index files from any folder.
It walks the paths you configure below, skips files that are already
indexed, and stores the FAISS library in the same .data/ folder that
the Streamlit app reads from.

Usage:
    python local_scan.py                  # interactive: scans WATCH_DIRS
    python local_scan.py --search "q3"    # search without opening the UI

Requirements: pip install -r requirements.txt
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

# ── Folders to scan ───────────────────────────────────────────────────────────
# Add or remove paths. Environment variables and ~ are expanded.
WATCH_DIRS: list[Path] = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "OneDrive",          # if you use OneDrive
    Path.home() / "OneDrive - AMDOCS", # AMDOCS OneDrive
]

# File types to index (must be a subset of ALLOWED_EXTENSIONS)
SCAN_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

# Your private library key — same one you type in the app sidebar
LIBRARY_KEY = "local-laptop"

# ─────────────────────────────────────────────────────────────────────────────

from semantic_navigator.store import FileLibrary


def _library() -> FileLibrary:
    import hashlib
    key_hash = hashlib.sha256(LIBRARY_KEY.lower().encode()).hexdigest()[:24]
    return FileLibrary(key_hash)


def scan(lib: FileLibrary, dry_run: bool = False) -> None:
    already = {rec.filename for rec in lib.files.values()}
    found: list[Path] = []
    for base in WATCH_DIRS:
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.suffix.lower() in SCAN_EXTENSIONS and f.is_file():
                # Skip hidden / system dirs
                if any(part.startswith(".") for part in f.parts):
                    continue
                found.append(f)

    print(f"\n{len(found)} indexable file(s) found across {len(WATCH_DIRS)} folder(s).")
    new_files = [f for f in found if f.name not in already]
    print(f"{len(new_files)} are new / not yet indexed.")

    if dry_run:
        for f in new_files:
            print(f"  → {f}")
        return

    if not new_files:
        print("Nothing to do.")
        return

    ok, fail = 0, []
    for i, path in enumerate(new_files, 1):
        try:
            data = path.read_bytes()
            lib.add_upload(path.name, data)
            print(f"[{i}/{len(new_files)}] ✓ {path.name}")
            ok += 1
        except Exception as exc:
            fail.append((path.name, str(exc)))
            print(f"[{i}/{len(new_files)}] ✗ {path.name}  ({exc})")

    print(f"\nDone — {ok} indexed, {len(fail)} skipped.")
    if fail:
        print("Skipped files:")
        for name, reason in fail:
            print(f"  {name}: {reason}")

    print(f"\nLibrary now holds {len(lib.files)} document(s).")
    print("Open the app to search:  streamlit run streamlit_app.py")
    print(f"Use library key in the sidebar:  {LIBRARY_KEY}")


def search(lib: FileLibrary, query: str) -> None:
    from semantic_navigator.agent import search_library  # noqa: PLC0415

    if not lib.is_ready:
        print("Library is empty. Run without --search first to index your files.")
        return

    result = search_library(lib, query)
    if result.blocked:
        print(f"Blocked: {result.block_reason}")
        return

    print(f"\nQuery: {query}")
    print(f"Intent: {result.intent}")
    print(f"\n{result.answer}\n")
    for hit in result.hits:
        print(f"  [{hit.relevance}%] {hit.filename}  —  {hit.why}")
        if hit.excerpts:
            excerpt = hit.excerpts[0][:200].replace("\n", " ")
            print(f"         …{excerpt}…")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index your laptop files for semantic search.")
    parser.add_argument("--search", metavar="QUERY", help="Run a search instead of indexing.")
    parser.add_argument("--dry-run", action="store_true", help="List files that would be indexed, without indexing.")
    parser.add_argument("--key", metavar="LIBRARY_KEY", default=LIBRARY_KEY, help="Override the library key.")
    args = parser.parse_args()

    if args.key != LIBRARY_KEY:
        LIBRARY_KEY = args.key  # type: ignore[assignment]

    print("Semantic Personal File Navigator — Local Scanner")
    print(f"Library key : {LIBRARY_KEY}")
    print(f"Folders     : {', '.join(str(d) for d in WATCH_DIRS if d.exists())}\n")

    lib = _library()
    print(f"Already indexed: {len(lib.files)} file(s).")

    if args.search:
        search(lib, args.search)
    else:
        scan(lib, dry_run=args.dry_run)
