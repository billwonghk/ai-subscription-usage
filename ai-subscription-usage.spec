# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "src" / "desktop_app.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "config"), "config"), (str(root / "locales"), "locales"), (str(root / "SETUP_WITH_AI.md"), "."), (str(root / "assets" / "tray-icon-64.png"), "assets"), (str(root / "assets" / "tray-icon.ico"), "assets")],
    hiddenimports=["pystray._darwin"] if sys.platform == "darwin" else ["pystray._win32"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="AI Subscription Usage",
        console=False,
    )
    collected = COLLECT(exe, a.binaries, a.datas, name="AI Subscription Usage")
    app = BUNDLE(
        collected,
        name="AI Subscription Usage.app",
        icon=str(root / "assets" / "app-icon.icns"),
        bundle_identifier="online.apeai.ai-subscription-usage",
        info_plist={"LSUIElement": True, "NSHighResolutionCapable": True, "CFBundleShortVersionString": "0.4.0", "CFBundleVersion": "0.4.0"},
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name="AI Subscription Usage",
        icon=str(root / "assets" / "app-icon.ico"),
        console=False,
    )
