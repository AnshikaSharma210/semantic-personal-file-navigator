"""
install_startup.py — Register File Navigator to start silently on Windows login.

Run ONCE:
    python install_startup.py          # install
    python install_startup.py remove   # uninstall

After install, the app starts automatically on every login.
Open http://localhost:8501 in any browser to use it.
"""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

APP_NAME = "SemanticFileNavigator"
RUN_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _vbs_path() -> Path:
    return Path(__file__).resolve().parent / "start_silent.vbs"


def _write_vbs() -> Path:
    """VBScript wrapper so the app starts without a visible terminal window."""
    python  = Path(sys.executable).resolve()
    run_py  = Path(__file__).resolve().parent / "run.py"
    vbs = _vbs_path()
    vbs.write_text(
        f'Set ws = CreateObject("WScript.Shell")\n'
        f'ws.Run "{python} {run_py}", 0, False\n',
        encoding="utf-8",
    )
    return vbs


def install() -> None:
    vbs = _write_vbs()
    cmd = f'wscript.exe "{vbs}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                        winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
    print(f"✓ Installed.  File Navigator will start silently on every login.")
    print(f"  Open http://localhost:8501 in your browser to use it.")
    print(f"  VBScript: {vbs}")
    print(f"\nTo remove:  python install_startup.py remove")


def remove() -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        print("✓ Removed from startup.")
    except FileNotFoundError:
        print("Not installed — nothing to remove.")
    vbs = _vbs_path()
    if vbs.exists():
        vbs.unlink()
        print(f"  Deleted {vbs}")


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This script is Windows-only.")
        sys.exit(1)
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove()
    else:
        install()
