"""
run.py — One command to start the Semantic File Navigator.

    python run.py

Opens http://localhost:8501 in your browser automatically.
Press Ctrl+C to stop.
"""
from __future__ import annotations

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 8501
APP = Path(__file__).resolve().parent / "streamlit_app.py"


def main() -> None:
    print("=" * 54)
    print("  Semantic Personal File Navigator")
    print("  Local-first · Private · No cloud required")
    print("=" * 54)
    print(f"\nStarting on  http://localhost:{PORT}")
    print("Press Ctrl+C to stop.\n")

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m", "streamlit",
            "run", str(APP),
            f"--server.port={PORT}",
            "--server.headless=true",         # don't auto-open from Streamlit
            "--browser.gatherUsageStats=false",
            "--server.fileWatcherType=none",   # we handle watching ourselves
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Wait until Streamlit is ready, then open browser
    opened = False
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            print(line, end="")
            if not opened and ("You can now view" in line or "Local URL" in line or "localhost" in line):
                time.sleep(0.5)
                webbrowser.open(f"http://localhost:{PORT}")
                opened = True
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("\nStopped.")


if __name__ == "__main__":
    main()
