"""Consent-gated, content-free diagnostic reporting."""

from __future__ import annotations

import json
import platform
import traceback
import urllib.request
from pathlib import Path
from typing import Any


ALLOWED_FIELDS = {"app_version", "os", "os_version", "language", "module", "error_type", "stack", "adapter_status"}


def diagnostic_payload(error: BaseException, *, app_version: str, language: str, module: str) -> dict[str, Any]:
    stack = traceback.format_exception(type(error), error, error.__traceback__)
    return {
        "app_version": app_version,
        "os": platform.system(),
        "os_version": platform.release(),
        "language": language,
        "module": module,
        "error_type": type(error).__name__,
        "stack": "".join(stack)[-6000:],
    }


def send_diagnostic(payload: dict[str, Any], endpoint: str, consent: bool) -> bool:
    if not consent or not endpoint:
        return False
    safe = {key: payload[key] for key in ALLOWED_FIELDS if key in payload}
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(safe).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "AI-Subscription-Usage"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return 200 <= response.status < 300


def save_pending(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({key: payload[key] for key in ALLOWED_FIELDS if key in payload}, ensure_ascii=False, indent=2), encoding="utf-8")

