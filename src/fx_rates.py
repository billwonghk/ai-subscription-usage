"""Daily USD/CNY reference-rate cache backed by the ECB reference feed."""

from __future__ import annotations

import datetime as dt
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ECB_90_DAY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"


def load_cache(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"source": "ECB", "fetched_at": None, "rates": {}}
    rates = payload.get("rates") if isinstance(payload, dict) else None
    if not isinstance(rates, dict):
        rates = {}
    cleaned = {}
    for date, value in rates.items():
        try:
            cleaned[str(date)] = float(value)
        except (TypeError, ValueError):
            continue
    return {"source": "ECB", "fetched_at": payload.get("fetched_at"), "rates": cleaned}


def parse_ecb_xml(content: bytes) -> dict[str, float]:
    """Return USD-to-CNY cross rates keyed by ECB reference-rate date."""
    root = ET.fromstring(content)
    result: dict[str, float] = {}
    for node in root.iter():
        date = node.attrib.get("time")
        if not date:
            continue
        currencies = {
            child.attrib.get("currency"): child.attrib.get("rate")
            for child in node
            if child.attrib.get("currency") in {"USD", "CNY"}
        }
        try:
            usd_per_eur = float(currencies["USD"])
            cny_per_eur = float(currencies["CNY"])
        except (KeyError, TypeError, ValueError):
            continue
        if usd_per_eur > 0 and cny_per_eur > 0:
            result[date] = cny_per_eur / usd_per_eur
    return result


def refresh_if_due(path: Path, today: dt.date | None = None, timeout: float = 8.0) -> dict:
    """Fetch once per local calendar day; keep the last good cache on any failure."""
    today = today or dt.datetime.now().astimezone().date()
    cached = load_cache(path)
    fetched_at = cached.get("fetched_at")
    if isinstance(fetched_at, str) and fetched_at[:10] == today.isoformat():
        return cached
    try:
        request = urllib.request.Request(ECB_90_DAY_URL, headers={"User-Agent": "AI-Subscription-Usage/0.4"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            rates = parse_ecb_xml(response.read())
    except (OSError, TimeoutError, ET.ParseError):
        return cached
    if not rates:
        return cached
    payload = {
        "source": "ECB",
        "fetched_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "rates": rates,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return payload


def browser_payload(cache: dict, dates: list[str]) -> dict:
    """Carry the latest published rate forward across weekends and holidays."""
    raw = cache.get("rates") if isinstance(cache, dict) else {}
    if not isinstance(raw, dict):
        raw = {}
    valid = sorted((str(date), float(value)) for date, value in raw.items() if isinstance(value, (int, float)))
    mapped: dict[str, float | None] = {}
    for date in dates:
        prior = [item for item in valid if item[0] <= date]
        mapped[date] = prior[-1][1] if prior else None
    latest_date = valid[-1][0] if valid else None
    return {
        "source": "ECB",
        "fetched_at": cache.get("fetched_at") if isinstance(cache, dict) else None,
        "latest_rate_date": latest_date,
        "usd_cny_by_date": mapped,
    }
