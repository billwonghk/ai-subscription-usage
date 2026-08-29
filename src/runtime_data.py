"""Platform user-data paths and non-destructive configuration migration."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path


DATA_SCHEMA_VERSION = 2


def app_data_root() -> Path:
    override = os.environ.get("AI_SUBSCRIPTION_USAGE_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AI Subscription Usage"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "AI Subscription Usage"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ai-subscription-usage"


def legacy_data_root() -> Path:
    return Path(os.environ.get("APPDATA", Path.home() / ".config")) / "ai-subscription-usage"


def _backup(path: Path, backup_root: Path) -> None:
    if path.exists():
        backup_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_root / path.name)


def initialize_user_data(resource_root: Path) -> Path:
    root = app_data_root()
    root.mkdir(parents=True, exist_ok=True)
    legacy = legacy_data_root()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = root / "backups" / f"migration-{stamp}"
    for name in ("settings.json", "sources.json", "pricing.json", "pending-diagnostic.json"):
        source, destination = legacy / name, root / name
        if source.exists() and not destination.exists() and source.resolve() != destination.resolve():
            shutil.copy2(source, destination)

    pricing_path = root / "pricing.json"
    subscriptions_path = root / "subscriptions.json"
    if pricing_path.exists() and not subscriptions_path.exists():
        try:
            pricing = json.loads(pricing_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pricing = {}
        subscriptions = pricing.pop("subscriptions", None) if isinstance(pricing, dict) else None
        if isinstance(subscriptions, dict) and subscriptions:
            _backup(pricing_path, backup_root)
            subscriptions_path.write_text(json.dumps({"schema_version": 1, "subscriptions": subscriptions}, ensure_ascii=False, indent=2), encoding="utf-8")
            pricing_path.write_text(json.dumps(pricing, ensure_ascii=False, indent=2), encoding="utf-8")

    bundled_pricing_path = resource_root / "config" / "pricing.json"
    if not pricing_path.exists():
        shutil.copy2(bundled_pricing_path, pricing_path)
    else:
        try:
            runtime_pricing = json.loads(pricing_path.read_text(encoding="utf-8"))
            bundled_pricing = json.loads(bundled_pricing_path.read_text(encoding="utf-8"))
            runtime_updated = str(runtime_pricing.get("updated_at", "")) if isinstance(runtime_pricing, dict) else ""
            bundled_updated = str(bundled_pricing.get("updated_at", "")) if isinstance(bundled_pricing, dict) else ""
        except (OSError, json.JSONDecodeError):
            runtime_updated = bundled_updated = ""
        if bundled_updated and bundled_updated > runtime_updated:
            _backup(pricing_path, root / "backups" / f"pricing-update-{stamp}")
            shutil.copy2(bundled_pricing_path, pricing_path)
    schema_path = root / "data-schema.json"
    if not schema_path.exists():
        schema_path.write_text(json.dumps({"schema_version": DATA_SCHEMA_VERSION}, indent=2), encoding="utf-8")
    return root


def load_subscriptions(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    subscriptions = payload.get("subscriptions") if isinstance(payload, dict) else None
    return subscriptions if isinstance(subscriptions, dict) else {}


def save_subscriptions(path: Path, subscriptions: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.parent / "backups" / f"subscriptions-{dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({"schema_version": 2, "subscriptions": subscriptions}, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
