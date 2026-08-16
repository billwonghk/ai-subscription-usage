"""Cross-platform "launch at login" toggle using OS-native mechanisms only.

macOS uses a per-user LaunchAgent; Windows uses the per-user Run registry
key. Both are the standard, no-extra-privilege way to do this and require
no third-party dependency.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BUNDLE_ID = "online.apeai.ai-subscription-usage"


def is_supported() -> bool:
    return sys.platform in ("darwin", "win32")


def _launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def is_enabled() -> bool:
    if sys.platform == "darwin":
        return _launch_agent_path().exists()
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                winreg.QueryValueEx(key, BUNDLE_ID)
            return True
        except OSError:
            return False
    return False


def _app_bundle(executable: Path) -> Path:
    """Walk up from the .app's inner Mach-O binary to the .app bundle itself.

    Pointing a LaunchAgent at the raw executable makes macOS treat it as a
    bare process with no bundle identity, so Login Items shows a generic
    terminal icon instead of the app's real name and icon.
    """
    for parent in executable.parents:
        if parent.suffix == ".app":
            return parent
    return executable


def set_enabled(enabled: bool, executable: Path) -> None:
    if sys.platform == "darwin":
        path = _launch_agent_path()
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            app_bundle = _app_bundle(executable)
            plist = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0"><dict>\n'
                f"<key>Label</key><string>{BUNDLE_ID}</string>\n"
                f"<key>ProgramArguments</key><array><string>/usr/bin/open</string><string>-a</string><string>{app_bundle}</string></array>\n"
                "<key>RunAtLoad</key><true/>\n"
                "</dict></plist>\n"
            )
            path.write_text(plist, encoding="utf-8")
            gui_domain = f"gui/{os.getuid()}"
            subprocess.run(["launchctl", "bootout", gui_domain, str(path)], check=False, capture_output=True)
            subprocess.run(["launchctl", "bootstrap", gui_domain, str(path)], check=False)
        elif path.exists():
            subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(path)], check=False)
            path.unlink()
    elif sys.platform == "win32":
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, BUNDLE_ID, 0, winreg.REG_SZ, f'"{executable}"')
            else:
                try:
                    winreg.DeleteValue(key, BUNDLE_ID)
                except FileNotFoundError:
                    pass
