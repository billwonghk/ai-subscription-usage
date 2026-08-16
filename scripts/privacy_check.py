#!/usr/bin/env python3
"""Fail a public release when bundled inputs contain personal runtime data."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "config", ROOT / "locales", ROOT / "SETUP_WITH_AI.md", ROOT / "src"]
BANNED = ("/Users/bill", "\\Users\\bill", '"start_date": "2026-07-12"', '"start_date": "2026-08-15"', '"start_date": "2026-03-13"')


def main() -> int:
    violations = []
    for target in TARGETS:
        files = [target] if target.is_file() else [p for p in target.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        for path in files:
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for marker in BANNED:
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
