"""User-triggered, validated pricing database updates."""

from __future__ import annotations

import hashlib
import json
import re
import math
import datetime as dt
import urllib.request
from pathlib import Path
from typing import Any


REQUIRED_RATE_FIELDS = {"input_per_million", "cached_input_per_million", "output_per_million"}


def download_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "AI-Subscription-Usage"})
    with urllib.request.urlopen(request, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("downloaded JSON must be an object")
    return data


def validate_pricing(data: dict[str, Any]) -> None:
    models = data.get("models")
    if not isinstance(models, dict) or not isinstance(data.get("price_version"), str):
        raise ValueError("pricing database is missing models or price_version")
    for model, rate in models.items():
        if not isinstance(model, str) or not isinstance(rate, dict):
            raise ValueError(f"invalid price entry: {model}")
        if "periods" in rate and not isinstance(rate["periods"], list):
            raise ValueError(f"invalid price periods: {model}")
        entries = rate.get("periods", [rate])
        if not entries:
            raise ValueError(f"empty price periods: {model}")
        intervals = []
        for entry in entries:
            if not isinstance(entry, dict) or not REQUIRED_RATE_FIELDS.issubset(entry):
                raise ValueError(f"invalid price entry: {model}")
            for field in REQUIRED_RATE_FIELDS | ({"cache_write_input_per_million"} & entry.keys()):
                if isinstance(entry[field], bool) or not isinstance(entry[field], (int, float)) or not math.isfinite(entry[field]) or entry[field] < 0:
                    raise ValueError(f"invalid {field}: {model}")
            if "periods" in rate:
                try:
                    start = dt.date.fromisoformat(entry["start_date"])
                    end = dt.date.fromisoformat(entry["end_date"]) if entry.get("end_date") else dt.date.max
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(f"invalid price dates: {model}") from error
                if end < start:
                    raise ValueError(f"reversed price dates: {model}")
                intervals.append((start, end))
        intervals.sort()
        if any(right[0] <= left[1] for left, right in zip(intervals, intervals[1:])):
            raise ValueError(f"overlapping price periods: {model}")


def update_pricing(manifest_url: str, destination: Path) -> str:
    if not manifest_url:
        raise ValueError("price manifest URL is not configured")
    manifest = download_json(manifest_url)
    price_url = manifest.get("pricing_url")
    expected_hash = manifest.get("sha256")
    if not isinstance(price_url, str) or not isinstance(expected_hash, str):
        raise ValueError("invalid price manifest")
    request = urllib.request.Request(price_url, headers={"User-Agent": "AI-Subscription-Usage"})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read()
    if hashlib.sha256(raw).hexdigest() != expected_hash.lower():
        raise ValueError("pricing checksum mismatch")
    data = json.loads(raw.decode("utf-8"))
    validate_pricing(data)
    temporary = destination.with_suffix(".json.new")
    temporary.write_bytes(raw)
    temporary.replace(destination)
    return data["price_version"]


def latest_release(releases_url: str, current_version: str) -> dict[str, str] | None:
    if not releases_url:
        return None
    release = download_json(releases_url)
    tag = str(release.get("tag_name", "")).lstrip("v")
    page = release.get("html_url")
    def stable_version(value: str) -> tuple[int, int, int] | None:
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value)
        return tuple(map(int, match.groups())) if match else None

    remote = stable_version(tag)
    current = stable_version(current_version)
    if (remote is not None and current is not None and remote > current
            and not release.get("draft") and not release.get("prerelease")
            and isinstance(page, str)):
        return {"version": tag, "url": page}
    return None
