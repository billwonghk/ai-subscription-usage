#!/usr/bin/env python3
"""Refresh config/pricing.json from OpenRouter's public pricing API.

Only models listed in config/model_id_map.json are touched. A model whose
current entry already uses a "periods" schedule is left alone (treated as
hand-curated). A genuine price change on a flat-rate model is recorded as a
new period so past report dates keep using the rate that was actually in
effect back then.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MODEL_MAP_PATH = ROOT / "config" / "model_id_map.json"
PRICING_PATH = ROOT / "config" / "pricing.json"
MANIFEST_PATH = ROOT / "config" / "pricing-manifest.json"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
PRICING_RAW_URL = "https://raw.githubusercontent.com/billwonghk/ai-subscription-usage/main/config/pricing.json"

PRIMARY_FIELDS = ("input_per_million", "cached_input_per_million", "output_per_million")


def fetch_openrouter_models() -> dict[str, dict[str, Any]]:
    request = urllib.request.Request(OPENROUTER_MODELS_URL, headers={"User-Agent": "AI-Subscription-Usage"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {model["id"]: model for model in payload.get("data", []) if isinstance(model, dict) and "id" in model}


def rate_from_openrouter(model: dict[str, Any]) -> dict[str, float] | None:
    pricing = model.get("pricing") or {}
    try:
        input_rate = round(float(pricing["prompt"]) * 1_000_000, 6)
        output_rate = round(float(pricing["completion"]) * 1_000_000, 6)
    except (KeyError, TypeError, ValueError):
        return None
    cached_rate = input_rate
    if pricing.get("input_cache_read") not in (None, ""):
        try:
            cached_rate = round(float(pricing["input_cache_read"]) * 1_000_000, 6)
        except (TypeError, ValueError):
            pass
    rate = {"input_per_million": input_rate, "cached_input_per_million": cached_rate, "output_per_million": output_rate}
    write_price = pricing.get("input_cache_write")
    if write_price not in (None, ""):
        try:
            rate["cache_write_input_per_million"] = round(float(write_price) * 1_000_000, 6)
        except (TypeError, ValueError):
            pass
    return rate


def primary_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    try:
        return all(round(float(a.get(key, -1)), 6) == round(float(b.get(key, -1)), 6) for key in PRIMARY_FIELDS)
    except (TypeError, ValueError):
        return False


def update_model(models: dict[str, Any], local_name: str, new_rate: dict[str, float], today: str) -> bool:
    existing = models.get(local_name)
    if isinstance(existing, dict) and isinstance(existing.get("periods"), list):
        return False  # hand-curated schedule; leave it to manual maintenance
    if not isinstance(existing, dict):
        models[local_name] = {**new_rate, "source": "openrouter", "updated_at": today}
        return True
    if primary_equal(existing, new_rate):
        old_write = existing.get("cache_write_input_per_million")
        new_write = new_rate.get("cache_write_input_per_million")
        if new_write is not None and (old_write is None or round(float(old_write), 6) != new_write):
            existing["cache_write_input_per_million"] = new_write
            existing["source"] = "openrouter"
            existing["updated_at"] = today
            return True
        return False
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
    old_period = {k: v for k, v in existing.items() if k not in ("source", "updated_at", "effective_from")}
    old_period["start_date"] = existing.get("effective_from", "2000-01-01")
    old_period["end_date"] = yesterday
    new_period = {**new_rate, "start_date": today}
    models[local_name] = {"periods": [old_period, new_period], "source": "openrouter", "updated_at": today}
    return True


def main() -> int:
    model_map = json.loads(MODEL_MAP_PATH.read_text(encoding="utf-8"))
    pricing = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    models = pricing.setdefault("models", {})
    today = date.today().isoformat()

    try:
        upstream = fetch_openrouter_models()
    except Exception as error:
        print(f"Could not reach OpenRouter: {error}", file=sys.stderr)
        return 1

    changed = False
    for local_name, target_id in model_map.items():
        if local_name.startswith("_"):
            continue
        match = upstream.get(target_id)
        if not match:
            print(f"No OpenRouter match for {local_name} ({target_id})")
            continue
        rate = rate_from_openrouter(match)
        if not rate:
            print(f"Incomplete pricing for {local_name} ({target_id})")
            continue
        if update_model(models, local_name, rate, today):
            print(f"Updated {local_name} from {target_id}")
            changed = True

    if not changed:
        print("No pricing changes.")
        return 0

    pricing["price_version"] = f"{today}.openrouter"
    pricing["updated_at"] = f"{today}T00:00:00Z"
    PRICING_PATH.write_text(json.dumps(pricing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    checksum = hashlib.sha256(PRICING_PATH.read_bytes()).hexdigest()
    manifest = {"price_version": pricing["price_version"], "pricing_url": PRICING_RAW_URL, "sha256": checksum}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {PRICING_PATH} and {MANIFEST_PATH} (version {pricing['price_version']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
