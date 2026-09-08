"""
Background folder watcher + indexer for the Semantic File Navigator.

Runs as a daemon thread inside the Streamlit process (via @st.cache_resource).
Watches configured folders, auto-indexes supported file types, and exposes
live status that the UI can poll.
"""
from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

SCAN_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

# Skip hidden files, temp Word files, and system dirs
_SKIP_PREFIXES = (".", "~$", "_")
_SKIP_DIRS = {"node_modules", ".git", "__pycache__", "$RECYCLE.BIN", "System Volume Information"}


def _should_index(path: Path) -> bool:
    if path.suffix.lower() not in SCAN_EXTENSIONS:
        return False
    if any(part.startswith(".") or part in _SKIP_DIRS for part in path.parts):
        return False
    if path.name.startswith(_SKIP_PREFIXES):
        return False
    return True


# ── Thread-safe status ────────────────────────────────────────────────────────

@dataclass
class IndexStatus:
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    total_indexed: int = 0
    failed: int = 0
    scanning: bool = False
    current_file: str = ""
    log: list[tuple[str, str]] = field(default_factory=list)  # [(filename, ok|fail)]

    def record(self, filename: str, ok: bool, *, set_scanning: bool | None = None):
        with self._lock:
            if ok:
                self.total_indexed += 1
                self.log = [(filename, "ok")] + self.log[:99]
            else:
                self.failed += 1
                self.log = [(filename, "fail")] + self.log[:99]
            if set_scanning is not None:
                self.scanning = set_scanning
            self.current_file = filename if set_scanning else ""

    def set_scanning(self, v: bool, current: str = ""):
        with self._lock:
            self.scanning = v
            self.current_file = current

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "total_indexed": self.total_indexed,
                "failed": self.failed,
                "scanning": self.scanning,
                "current_file": self.current_file,
                "log": list(self.log[:20]),
            }


# ── Watchdog event handler ────────────────────────────────────────────────────

class _Handler(FileSystemEventHandler):
    def __init__(self, q: queue.Queue):
        self._q = q

    def _enqueue(self, event: FileSystemEvent):
        if not event.is_directory:
            p = Path(str(event.src_path))
            if _should_index(p):
                self._q.put(p)

    def on_created(self, event: FileSystemEvent):
        self._enqueue(event)

    def on_moved(self, event):
        # File renamed — index the new path
        p = Path(str(getattr(event, "dest_path", "")))
        if _should_index(p):
            self._q.put(p)


# ── Main watcher / indexer ────────────────────────────────────────────────────

class FolderWatcher:
    """
    Singleton owned by @st.cache_resource.
    Manages watchdog observers + background indexer thread.
    """

    CONFIG_FILE = Path(__file__).resolve().parent.parent / ".data" / "watched_folders.json"

    def __init__(self, library) -> None:
        self._lib = library
        self._q: queue.Queue[Path] = queue.Queue()
        self._stop = threading.Event()
        self.status = IndexStatus()

        self._observer = Observer()
        self._watched_paths: set[str] = set()

        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._load_config()

        # Start background indexer thread
        self._thread = threading.Thread(target=self._run, daemon=True, name="file-indexer")
        self._thread.start()

    # ── Config persistence ────────────────────────────────────────────────────

    def _load_config(self):
        if self.CONFIG_FILE.exists():
            try:
                data = json.loads(self.CONFIG_FILE.read_text(encoding="utf-8"))
                for p in data.get("folders", []):
                    self._register(Path(p))
            except Exception:
                pass

    def _save_config(self):
        self.CONFIG_FILE.write_text(
            json.dumps({"folders": list(self._watched_paths)}, indent=2),
            encoding="utf-8",
        )

    # ── Folder management ────────────────────────────────────────────────────

    @property
    def folders(self) -> list[Path]:
        return sorted(Path(p) for p in self._watched_paths)

    def add_folder(self, path: Path) -> str:
        """Add a folder to watch. Returns '' on success or an error message."""
        path = path.expanduser().resolve()
        if not path.exists() or not path.is_dir():
            return f"Folder not found: {path}"
        key = str(path)
        if key in self._watched_paths:
            return "Already watching this folder."
        self._register(path)
        self._save_config()
        # Enqueue initial scan
        self._q.put(("SCAN", path))
        return ""

    def remove_folder(self, path: Path):
        key = str(path.expanduser().resolve())
        self._watched_paths.discard(key)
        self._save_config()
        # We can't un-schedule watchdog cleanly without restarting;
        # the observer will still fire events but we'll ignore them.

    def _register(self, path: Path):
        key = str(path)
        if key not in self._watched_paths and path.exists():
            self._watched_paths.add(key)
            try:
                if not self._observer.is_alive():
                    self._observer.start()
                self._observer.schedule(_Handler(self._q), str(path), recursive=True)
            except Exception:
                pass

    # ── Background indexer ────────────────────────────────────────────────────

    def _run(self):
        # Start observer
        if not self._observer.is_alive():
            try:
                self._observer.start()
            except Exception:
                pass

        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=1.0)
            except queue.Empty:
                continue

            # Initial folder scan command
            if isinstance(item, tuple) and item[0] == "SCAN":
                self._initial_scan(item[1])
                self._q.task_done()
                continue

            # Single file
            path: Path = item
            self._index_file(path)
            self._q.task_done()

    def _initial_scan(self, folder: Path):
        already = {rec.filepath for rec in self._lib.files.values() if hasattr(rec, "filepath")}
        already_names = {rec.filename for rec in self._lib.files.values()}
        candidates = [p for p in folder.rglob("*") if _should_index(p) and p.name not in already_names]
        self.status.set_scanning(True, f"Scanning {folder.name}…")
        for p in candidates:
            self._index_file(p)
        self.status.set_scanning(False)

    def _index_file(self, path: Path):
        # Skip if already indexed by filename
        already_names = {rec.filename for rec in self._lib.files.values()}
        if path.name in already_names:
            return
        try:
            self.status.set_scanning(True, path.name)
            data = path.read_bytes()
            self._lib.add_local(path.name, data, source_path=str(path))
            self.status.record(path.name, ok=True)
        except Exception as exc:
            if "already indexed" not in str(exc).lower():
                self.status.record(path.name, ok=False)
        finally:
            self.status.set_scanning(False)

    def stop(self):
        self._stop.set()
        try:
            self._observer.stop()
        except Exception:
            pass
