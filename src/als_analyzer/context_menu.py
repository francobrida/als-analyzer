"""Windows right-click entry for .als files: ``python -m als_analyzer.context_menu install|uninstall``.

Per-user (HKCU), no admin needed. On Windows 11 it shows under "Show more options".
"""

from __future__ import annotations

import sys
from pathlib import Path

KEY = r"Software\Classes\SystemFileAssociations\.als\shell\als-analyzer"
LABEL = "Analyze with als-analyzer"


def _command() -> str:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")  # no console window
    return f'"{pythonw if pythonw.exists() else exe}" -m als_analyzer "%1" --open'


def install() -> None:
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, LABEL)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY + r"\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, _command())


def uninstall() -> None:
    import winreg

    for sub in (KEY + r"\command", KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if sys.platform != "win32" or args not in (["install"], ["uninstall"]):
        print("usage (Windows only): python -m als_analyzer.context_menu install|uninstall", file=sys.stderr)
        return 2
    (install if args == ["install"] else uninstall)()
    print("Right-click entry " + ("installed." if args == ["install"] else "removed."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
