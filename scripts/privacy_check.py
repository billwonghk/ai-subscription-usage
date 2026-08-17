#!/usr/bin/env python3
"""Fail a public release when bundled inputs contain personal runtime data."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
# Absolute-path markers: checked across every tracked file, since a personal
# path has no legitimate reason to appear anywhere in the public repo.
PATH_MARKERS = ("/Users/bill", "\\Users\\bill")
# Known historical subscription dates: only meaningful within the files that
# actually ship in the app/release, not in test fixtures that legitimately
# use plausible-looking example dates.
SUBSCRIPTION_DATE_MARKERS = ('"start_date": "2026-07-12"', '"start_date": "2026-08-15"', '"start_date": "2026-03-13"')
NARROW_TARGETS = (ROOT / "config", ROOT / "locales", ROOT / "SETUP_WITH_AI.md", ROOT / "src")
EXCLUDED_DIR_NAMES = {
    ".git", "dist", "build", "outputs", "output", ".venv-desktop", ".pyinstaller-cache",
    "__pycache__", "deploy", "node_modules", ".pytest_cache",
}


def tracked_files() -> list[Path]:
    """Prefer the exact set of git-tracked files (mirrors what a public checkout contains)."""
    try:
        result = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
        return [ROOT / line for line in result.stdout.splitlines() if line]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in ROOT.rglob("*") if p.is_file() and not EXCLUDED_DIR_NAMES.intersection(p.parts)]


def in_narrow_scope(path: Path) -> bool:
    return any(path == target or target in path.parents for target in NARROW_TARGETS)


def main() -> int:
    violations = []
    for path in tracked_files():
        if path == SELF:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for marker in PATH_MARKERS:
            if marker in content:
                violations.append(f"{path.relative_to(ROOT)}: {marker}")
        if in_narrow_scope(path):
            for marker in SUBSCRIPTION_DATE_MARKERS:
                if marker in content:
                    violations.append(f"{path.relative_to(ROOT)}: {marker}")
    pricing = json.loads((ROOT / "config" / "pricing.json").read_text(encoding="utf-8"))
    if pricing.get("subscriptions"):
        violations.append("config/pricing.json: populated subscriptions")
    if violations:
        print("Privacy check failed:\n" + "\n".join(violations))
        return 1
    print("Privacy check passed: public release inputs contain no runtime user data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
