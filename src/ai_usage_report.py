#!/usr/bin/env python3
"""Generate an offline AI subscription usage report from local session logs.

This module intentionally uses only the Python standard library. It never reads
credentials, opens a network connection, or starts a web server.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import fx_rates
from favicon import FAVICON_TAG, LOGO_IMG
from report_i18n import localize_html
from source_discovery import load_configured_sources


LOCAL_CODEX_SESSIONS = Path.home() / ".codex" / "sessions"
LOCAL_CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
LOCAL_GEMINI_HOME = Path.home() / ".gemini"
LOCAL_GEMINI_SESSIONS = LOCAL_GEMINI_HOME / "tmp"
LOCAL_GROK_SESSIONS = Path.home() / ".grok" / "sessions"
LOCAL_MINIMAX_DB = Path.home() / ".minimax" / "sqlite.db"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "ai-usage-report.html"
DEFAULT_PRICING = PROJECT_ROOT / "config" / "pricing.json"
DEFAULT_DEEPSEEK_TIER_MAP = PROJECT_ROOT / "config" / "deepseek_tier_map.json"
def report_today() -> dt.date:
    return dt.date.today()


@dataclass
class Usage:
    provider: str
    model: str
    date: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cache_is_subset_of_input: bool = False
    is_estimate: bool = False
    cache_write_input_tokens: int = 0
    deepseek_rate_band: str = "off_peak"

    @property
    def total_tokens(self) -> int:
        cached = 0 if self.cache_is_subset_of_input else self.cached_input_tokens
        return self.input_tokens + self.output_tokens + cached + self.cache_write_input_tokens


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_timestamp(value: Any) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def explicit_record_moment(record: dict[str, Any]) -> dt.datetime | None:
    """Return only a real timestamp from the record, never a file-time fallback."""
    for key in ("timestamp", "created_at", "time"):
        parsed = parse_timestamp(record.get(key))
        if parsed:
            return parsed
    return None


def deepseek_rate_band(moment: dt.datetime | None) -> str:
    """Classify DeepSeek's published peak windows in Beijing time; unknown means off-peak."""
    if moment is None:
        return "off_peak"
    if moment.tzinfo is None:
        moment = moment.astimezone()
    beijing_time = moment.astimezone(ZoneInfo("Asia/Shanghai")).time()
    if dt.time(9, 0) <= beijing_time < dt.time(12, 0) or dt.time(14, 0) <= beijing_time < dt.time(18, 0):
        return "peak"
    return "off_peak"


def iter_json_records(root: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    if not root.exists():
        return
    for path in sorted(root.rglob("*.jsonl")):
        try:
            with path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(record, dict):
                        yield path, record
        except OSError:
            continue


def walk_values(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child)


def record_date(record: dict[str, Any], fallback: Path) -> str:
    for key in ("timestamp", "created_at", "time"):
        parsed = parse_timestamp(record.get(key))
        if parsed:
            return parsed.astimezone().date().isoformat()
    try:
        return dt.datetime.fromtimestamp(fallback.stat().st_mtime).date().isoformat()
    except OSError:
        return report_today().isoformat()


def find_model(record: dict[str, Any], current_model: str) -> str:
    for node in walk_values(record):
        value = node.get("model")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return current_model


def token_count(record: dict[str, Any]) -> dict[str, Any] | None:
    """Return the cumulative total emitted by a Codex token_count event."""
    payload = record.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "token_count":
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    total = info.get("total_token_usage")
    if not isinstance(total, dict):
        return None
    if not any(key in total for key in ("input_tokens", "output_tokens", "cached_input_tokens")):
        return None
    return total


def parse_codex(root: Path, since: dt.date) -> tuple[list[Usage], int]:
    usages: dict[tuple[str, str], Usage] = {}
    files_read = 0
    if not root.exists():
        return [], files_read

    for path in sorted(root.rglob("*.jsonl")):
        files_read += 1
        current_model = "未记录模型"
        previous = {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
        try:
            stream = path.open("r", encoding="utf-8")
        except OSError:
            continue
        with stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                current_model = find_model(record, current_model)
                node = token_count(record)
                if node is None:
                    continue
                current = {key: as_int(node.get(key)) for key in previous}
                delta = {key: current[key] - previous[key] for key in previous}
                # A lower counter indicates a new accounting segment; use its
                # absolute counter rather than discarding its usage.
                if any(value < 0 for value in delta.values()):
                    delta = current
                previous = current
                date = record_date(record, path)
                try:
                    record_day = dt.date.fromisoformat(date)
                except ValueError:
                    continue
                if record_day < since:
                    continue
                rate_band = deepseek_rate_band(explicit_record_moment(record))
                key = (date, current_model, rate_band)
                usage = usages.setdefault(key, Usage("Codex", current_model, date, cache_is_subset_of_input=True, deepseek_rate_band=rate_band))
                usage.input_tokens += delta["input_tokens"]
                usage.output_tokens += delta["output_tokens"]
                usage.cached_input_tokens += delta["cached_input_tokens"]

    return sorted(usages.values(), key=lambda item: (item.date, item.model)), files_read


def parse_claude_code(root: Path, since: dt.date, *, provider: str = "Claude Code", excluded_roots: tuple[Path, ...] = ()) -> tuple[list[Usage], int]:
    """Parse Claude Code's per-response usage entries from local JSONL files."""
    usages: dict[tuple[str, str], Usage] = {}
    responses: dict[str, tuple[str, str, dict[str, Any], str]] = {}
    files_read = 0
    if not root.exists():
        return [], files_read
    for path in sorted(root.rglob("*.jsonl")):
        if any(path.resolve().is_relative_to(excluded.resolve()) for excluded in excluded_roots):
            continue
        files_read += 1
        try:
            stream = path.open("r", encoding="utf-8")
        except OSError:
            continue
        with stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if not isinstance(message, dict):
                    continue
                usage = message.get("usage")
                if not isinstance(usage, dict):
                    continue
                if not any(key in usage for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")):
                    continue
                date = record_date(record, path)
                try:
                    if dt.date.fromisoformat(date) < since:
                        continue
                except ValueError:
                    continue
                model = message.get("model") if isinstance(message.get("model"), str) else "未记录模型"
                if model == "<synthetic>":
                    continue
                response_id = message.get("id") or record.get("uuid")
                if not isinstance(response_id, str) or not response_id:
                    response_id = f"{path}:{record.get('timestamp', '')}:{len(responses)}"
                responses[response_id] = (date, model, usage, deepseek_rate_band(explicit_record_moment(record)))
    for date, model, usage, rate_band in responses.values():
        key = (date, model, rate_band)
        item = usages.setdefault(key, Usage(provider, model, date, deepseek_rate_band=rate_band))
        item.input_tokens += as_int(usage.get("input_tokens"))
        item.output_tokens += as_int(usage.get("output_tokens"))
        # Claude keeps creation and read cache counters separately.
        item.cached_input_tokens += as_int(usage.get("cache_read_input_tokens"))
        item.cache_write_input_tokens += as_int(usage.get("cache_creation_input_tokens"))
    return sorted(usages.values(), key=lambda item: (item.date, item.model)), files_read


def parse_kimi_wire(root: Path, since: dt.date) -> tuple[list[Usage], int]:
    """Read persisted StatusUpdate records, not JSON-RPC transport messages.

    Official sources: MoonshotAI/kimi-cli wire/file.py, wire/types.py and
    packages/kosong/src/kosong/chat_provider/__init__.py. StatusUpdate has no
    model ID: preserve unknown model rather than relabel historical usage.
    """
    responses = {}
    files_read = 0
    for path in sorted(root.rglob("wire.jsonl")) if root.exists() else ():
        try:
            stream = path.open(encoding="utf-8")
        except OSError:
            continue
        files_read += 1
        with stream:
            for line_number, line in enumerate(stream):
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        continue
                    message = record.get("message")
                    if not isinstance(message, dict) or message.get("type") != "StatusUpdate":
                        continue
                    payload = message.get("payload")
                    if not isinstance(payload, dict):
                        continue
                    counters = payload.get("token_usage")
                    if not isinstance(counters, dict):
                        continue
                    timestamp = record.get("timestamp")
                    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
                        continue
                    moment = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc)
                    day = moment.astimezone().date()
                    if day < since:
                        continue
                    values = [counters.get(k, 0) for k in
                              ("input_other", "output", "input_cache_read", "input_cache_creation")]
                    if any(type(v) is not int or v < 0 for v in values):
                        continue
                    identifier = payload.get("message_id")
                    key = (path.parent.name, identifier) if isinstance(identifier, str) and identifier else (str(path), line_number)
                    responses[key] = Usage("Kimi", "未记录模型", day.isoformat(),
                                           input_tokens=values[0], output_tokens=values[1],
                                           cached_input_tokens=values[2], cache_write_input_tokens=values[3],
                                           deepseek_rate_band=deepseek_rate_band(moment))
                except (ValueError, OverflowError, OSError):
                    continue
    return list(responses.values()), files_read


def parse_minimax(database: Path, since: dt.date) -> tuple[list[Usage], int]:
    """Read MiniMax Agent's local per-turn token accounting table.

    Only the accounting columns are selected. The ``raw`` field and session
    message tables are deliberately not read.
    """
    if not database.is_file():
        return [], 0
    usages: dict[tuple[str, str], Usage] = {}
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        rows = connection.execute(
            "SELECT model, ts, input_tokens, output_tokens, reasoning_tokens, "
            "cache_read_tokens, cache_write_tokens FROM token_usage ORDER BY ts"
        ).fetchall()
    except (sqlite3.Error, OSError):
        return [], 0
    finally:
        if "connection" in locals():
            connection.close()
    for model, timestamp, input_tokens, output_tokens, reasoning_tokens, cache_read, cache_write in rows:
        try:
            moment = dt.datetime.fromtimestamp(int(timestamp) / 1000).astimezone()
        except (TypeError, ValueError, OSError):
            continue
        if moment.date() < since:
            continue
        date = moment.date().isoformat()
        model = model.strip() if isinstance(model, str) and model.strip() else "未记录模型"
        rate_band = deepseek_rate_band(moment)
        key = (date, model, rate_band)
        item = usages.setdefault(key, Usage("MiniMax", model, date, deepseek_rate_band=rate_band))
        item.input_tokens += as_int(input_tokens)
        item.output_tokens += as_int(output_tokens) + as_int(reasoning_tokens)
        item.cached_input_tokens += as_int(cache_read)
        item.cache_write_input_tokens += as_int(cache_write)
    return sorted(usages.values(), key=lambda item: (item.date, item.model)), 1


def iter_json_documents(root: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    """Read JSON/JSONL session documents; unreadable documents are skipped."""
    if not root.exists():
        return
    for path in sorted(root.rglob("*.json")):
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(loaded, dict):
            yield path, loaded
        elif isinstance(loaded, list):
            for item in loaded:
                if isinstance(item, dict):
                    yield path, item
    yield from iter_json_records(root)


def parse_gemini_cli(root: Path, since: dt.date) -> tuple[list[Usage], int]:
    """Parse Gemini CLI chat files under ~/.gemini/tmp/*/chats/.

    Gemini's local format records per-message token metadata. The parser accepts
    both the documented {type, model, tokens} form and API usageMetadata names.
    """
    usages: dict[tuple[str, str], Usage] = {}
    files_read = 0
    if not root.exists():
        return [], files_read
    paths = [path for path in root.rglob("*") if path.is_file() and "chats" in path.parts and path.suffix in {".json", ".jsonl"}]
    for path in paths:
        files_read += 1
    for path, document in iter_json_documents(root):
        if "chats" not in path.parts:
            continue
        for node in walk_values(document):
            tokens = node.get("tokens") if isinstance(node.get("tokens"), dict) else node.get("usageMetadata")
            if not isinstance(tokens, dict):
                continue
            token_keys = {"input", "output", "cached", "promptTokenCount", "candidatesTokenCount", "cachedContentTokenCount"}
            if not token_keys.intersection(tokens):
                continue
            model = node.get("model") or node.get("modelVersion") or document.get("model") or "未记录模型"
            if not isinstance(model, str):
                model = "未记录模型"
            date = record_date(node, path)
            try:
                if dt.date.fromisoformat(date) < since:
                    continue
            except ValueError:
                continue
            key = (date, model)
            item = usages.setdefault(key, Usage("Gemini CLI", model, date, cache_is_subset_of_input=True))
            item.input_tokens += as_int(tokens.get("input", tokens.get("promptTokenCount")))
            item.output_tokens += as_int(tokens.get("output", tokens.get("candidatesTokenCount"))) + as_int(tokens.get("thoughts", tokens.get("thoughtsTokenCount")))
            item.cached_input_tokens += as_int(tokens.get("cached", tokens.get("cachedContentTokenCount")))
    return sorted(usages.values(), key=lambda item: (item.date, item.model)), files_read


def parse_grok_build(root: Path, since: dt.date) -> tuple[list[Usage], int]:
    """Read Grok Build local session usage records.

    Three local sources exist, tried in order of preference, and each is used
    on its own (no summing across sources) to avoid double-counting the same
    underlying usage: per-turn updates.jsonl (includes a model breakdown),
    then the global unified.jsonl operation log, then signals.json context
    snapshots as an estimate-only last resort.
    """
    usages: dict[tuple[str, str], Usage] = {}
    files_read = 0
    if not root.exists():
        return [], files_read

    update_paths = sorted(set(root.rglob("updates.jsonl")))
    for path in update_paths:
        files_read += 1
        try:
            stream = path.open("r", encoding="utf-8")
        except OSError:
            continue
        with stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or record.get("sessionUpdate") != "turn_completed":
                    continue
                usage = record.get("usage")
                if not isinstance(usage, dict):
                    continue
                date = record_date(record, path)
                try:
                    if dt.date.fromisoformat(date) < since:
                        continue
                except ValueError:
                    continue
                model_usage = usage.get("modelUsage")
                if isinstance(model_usage, dict) and len(model_usage) == 1:
                    model = next(iter(model_usage))
                else:
                    model = find_model(record, "未记录模型")
                key = (date, model)
                item = usages.setdefault(key, Usage("Grok Build", model, date, cache_is_subset_of_input=True))
                item.input_tokens += as_int(usage.get("inputTokens"))
                item.output_tokens += as_int(usage.get("outputTokens"))
                item.cached_input_tokens += as_int(usage.get("cachedReadTokens"))
    if update_paths:
        return sorted(usages.values(), key=lambda item: (item.date, item.model)), files_read

    unified_paths = sorted(set(root.rglob("unified.jsonl")))
    logs_path = root.parent / "logs" / "unified.jsonl"
    if logs_path.exists():
        unified_paths.append(logs_path)
    for path in unified_paths:
        files_read += 1
        current_model = "未记录模型"
        try:
            stream = path.open("r", encoding="utf-8")
        except OSError:
            continue
        with stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                current_model = find_model(record, current_model)
                usage = next((node for node in walk_values(record) if any(key in node for key in (
                    "prompt_tokens", "promptTokens", "input_tokens", "completion_tokens",
                    "completionTokens", "output_tokens", "cached_prompt_tokens", "cache_read_input_tokens"
                ))), None)
                if not usage:
                    continue
                date = record_date(record, path)
                try:
                    if dt.date.fromisoformat(date) < since:
                        continue
                except ValueError:
                    continue
                model = find_model(record, current_model)
                key = (date, model)
                item = usages.setdefault(key, Usage("Grok Build", model, date, cache_is_subset_of_input=True))
                item.input_tokens += as_int(usage.get("prompt_tokens", usage.get("promptTokens", usage.get("input_tokens"))))
                # reasoning_tokens is a subset of completion_tokens, not additional output.
                item.output_tokens += as_int(usage.get("completion_tokens", usage.get("completionTokens", usage.get("output_tokens"))))
                item.cached_input_tokens += as_int(usage.get("cached_prompt_tokens", usage.get("cache_read_input_tokens")))
    if unified_paths:
        return sorted(usages.values(), key=lambda item: (item.date, item.model)), files_read

    for signal_path in sorted(root.rglob("signals.json")):
        files_read += 1
        try:
            signal = json.loads(signal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(signal, dict):
            continue
        summary_path = signal_path.with_name("summary.json")
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            summary = {}
        if not isinstance(summary, dict):
            summary = {}
        date = record_date(summary or signal, signal_path)
        try:
            if dt.date.fromisoformat(date) < since:
                continue
        except ValueError:
            continue
        model = signal.get("primaryModelId") or summary.get("current_model_id") or summary.get("model") or "未记录模型"
        if not isinstance(model, str):
            model = "未记录模型"
        tokens = as_int(signal.get("contextTokensUsed"))
        if not tokens:
            tokens = as_int(signal.get("totalTokensBeforeCompaction"))
        if not tokens:
            continue
        key = (date, model)
        item = usages.setdefault(key, Usage("Grok Build", model, date, is_estimate=True))
        item.input_tokens += tokens
    return sorted(usages.values(), key=lambda item: (item.date, item.model)), files_read


def number(value: int | float) -> str:
    return f"{value:,.0f}"


def load_pricing(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"models": {}, "subscriptions": {}}
    if not isinstance(data, dict):
        return {"models": {}, "subscriptions": {}}
    return data


def pricing_model_for_usage(item: Usage, pricing: dict[str, Any]) -> tuple[str, bool]:
    """Resolve configured aliases and the explicit Auto-model fallback."""
    aliases = pricing.get("model_aliases") if isinstance(pricing.get("model_aliases"), dict) else {}
    resolved = aliases.get(item.model, item.model)
    normalized = item.model.strip().lower().replace("_", "-")
    is_auto = normalized == "automatic" or re.search(r"(^|[-/:])auto($|[-/:])", normalized) is not None
    if not is_auto:
        return str(resolved), False
    fallbacks = pricing.get("auto_fallbacks") if isinstance(pricing.get("auto_fallbacks"), dict) else {}
    fallback = fallbacks.get(item.provider)
    if isinstance(fallback, str) and fallback:
        return str(fallback), True
    if isinstance(fallback, dict) and isinstance(fallback.get("periods"), list):
        candidates = [period for period in fallback["periods"] if isinstance(period, dict) and (
            not item.date or (str(period.get("start_date", "")) <= item.date and (not period.get("end_date") or item.date <= str(period["end_date"])))
        ) and isinstance(period.get("model"), str) and period["model"]]
        if candidates:
            selected = sorted(candidates, key=lambda period: str(period.get("start_date", "")))[-1]
            return str(selected["model"]), True
    return item.model, False


def api_equivalent_cost(item: Usage, pricing: dict[str, Any]) -> float | None:
    models = pricing.get("models") if isinstance(pricing.get("models"), dict) else {}
    pricing_model, _ = pricing_model_for_usage(item, pricing)
    rate = models.get(pricing_model)
    if not isinstance(rate, dict):
        return None
    periods = rate.get("periods")
    if isinstance(periods, list):
        candidates = [period for period in periods if isinstance(period, dict) and (
            not item.date or (str(period.get("start_date", "")) <= item.date and (not period.get("end_date") or item.date <= str(period["end_date"])))
        )]
        if not candidates:
            return None
        rate = sorted(candidates, key=lambda period: str(period.get("start_date", "")))[-1]
    try:
        input_rate = float(rate["input_per_million"])
        cached_rate = float(rate["cached_input_per_million"])
        output_rate = float(rate["output_per_million"])
    except (KeyError, TypeError, ValueError):
        return None
    fresh_input = max(0, item.input_tokens - item.cached_input_tokens) if item.cache_is_subset_of_input else item.input_tokens
    try:
        cache_write_rate = float(rate.get("cache_write_input_per_million", input_rate))
    except (TypeError, ValueError):
        return None
    return (
        fresh_input * input_rate
        + item.cached_input_tokens * cached_rate
        + item.cache_write_input_tokens * cache_write_rate
        + item.output_tokens * output_rate
    ) / 1_000_000


def load_deepseek_tier_map(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: value for key, value in data.items() if not key.startswith("_") and value in ("flash", "pro")}


def cache_hit_stats(items: Iterable[Usage]) -> tuple[int, int]:
    """Return (cache-hit input tokens, total input tokens) across items; output tokens are not counted."""
    hit = total = 0
    for item in items:
        fresh = max(0, item.input_tokens - item.cached_input_tokens) if item.cache_is_subset_of_input else item.input_tokens
        hit += item.cached_input_tokens
        total += fresh + item.cached_input_tokens + item.cache_write_input_tokens
    return hit, total


def deepseek_equivalent_cost(item: Usage, pricing: dict[str, Any], tiers: dict[str, str]) -> float | None:
    """Estimate what this usage would cost on DeepSeek: the tier ('flash' or 'pro') is matched to
    this model's capability class (config/deepseek_tier_map.json), and DeepSeek's own real cache-hit
    vs cache-miss rates are applied to this item's own actual cache-hit/miss token split - not a
    guessed or borrowed ratio."""
    pricing_model, is_auto = pricing_model_for_usage(item, pricing)
    tier = "flash" if is_auto else tiers.get(pricing_model)
    if tier is None:
        return None
    models = pricing.get("models") if isinstance(pricing.get("models"), dict) else {}
    rate = models.get(f"deepseek-v4-{tier}")
    if not isinstance(rate, dict):
        return None
    periods = rate.get("periods")
    if isinstance(periods, list):
        candidates = [period for period in periods if isinstance(period, dict) and (
            not item.date or (str(period.get("start_date", "")) <= item.date and (not period.get("end_date") or item.date <= str(period["end_date"])))
        )]
        if not candidates:
            return None
        rate = sorted(candidates, key=lambda period: str(period.get("start_date", "")))[-1]
    try:
        input_rate = float(rate["input_per_million"])
        cached_rate = float(rate["cached_input_per_million"])
        output_rate = float(rate["output_per_million"])
    except (KeyError, TypeError, ValueError):
        return None
    fresh_input = max(0, item.input_tokens - item.cached_input_tokens) if item.cache_is_subset_of_input else item.input_tokens
    # DeepSeek has no separate cache-write price; cache-write tokens are billed as fresh (cache-miss) input.
    base_cost = (
        (fresh_input + item.cache_write_input_tokens) * input_rate
        + item.cached_input_tokens * cached_rate
        + item.output_tokens * output_rate
    ) / 1_000_000
    return base_cost * (2.0 if item.deepseek_rate_band == "peak" else 1.0)


def deepseek_tier_for_usage(item: Usage, pricing: dict[str, Any], tiers: dict[str, str]) -> str | None:
    pricing_model, is_auto = pricing_model_for_usage(item, pricing)
    return "flash" if is_auto else tiers.get(pricing_model)


def money(value: float | None) -> str:
    return "未公开价格" if value is None else f"${value:,.2f}"


def plan_data(pricing: dict[str, Any]) -> list[dict[str, Any]]:
    subscriptions = pricing.get("subscriptions") if isinstance(pricing.get("subscriptions"), dict) else {}
    codex = subscriptions.get("Codex") if isinstance(subscriptions.get("Codex"), dict) else {}
    plans = codex.get("plans") if isinstance(codex.get("plans"), list) else []
    cleaned = []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        start = plan.get("start_date")
        amount = plan.get("monthly_usd")
        if isinstance(start, str) and isinstance(amount, (int, float)):
            cleaned.append({"start_date": start, "monthly_usd": float(amount)})
    return sorted(cleaned, key=lambda item: item["start_date"])


def subscription_plan_data(pricing: dict[str, Any]) -> list[dict[str, Any]]:
    """Return browser-ready plans for every configured subscription provider."""
    subscriptions = pricing.get("subscriptions") if isinstance(pricing.get("subscriptions"), dict) else {}
    provider_names = {
        "Codex": "ChatGPT", "Claude": "Claude", "Gemini": "Gemini", "Grok": "Grok",
        "MiniMax": "MiniMax", "Kimi": "Kimi", "GLM": "GLM", "Bailian": "阿里百炼",
    }
    cleaned = []
    for configured_name, browser_name in provider_names.items():
        config = subscriptions.get(configured_name)
        plans = config.get("plans") if isinstance(config, dict) and isinstance(config.get("plans"), list) else []
        for plan in plans:
            if not isinstance(plan, dict) or not isinstance(plan.get("start_date"), str):
                continue
            if isinstance(plan.get("amount"), (int, float)) and plan.get("currency") in {"USD", "CNY"} and plan.get("cycle") in {"month", "year"}:
                cleaned.append({"provider": browser_name, "start_date": plan["start_date"], "amount": float(plan["amount"]), "currency": plan["currency"], "cycle": plan["cycle"]})
            elif isinstance(plan.get("monthly_usd"), (int, float)):
                cleaned.append({"provider": browser_name, "start_date": plan["start_date"], "amount": float(plan["monthly_usd"]), "currency": "USD", "cycle": "month"})
            elif isinstance(plan.get("annual_usd"), (int, float)):
                cleaned.append({"provider": browser_name, "start_date": plan["start_date"], "amount": float(plan["annual_usd"]), "currency": "USD", "cycle": "year"})
    return sorted(cleaned, key=lambda item: (item["provider"], item["start_date"]))



PROVIDER_META = {
    "Codex": {"label": "ChatGPT", "plan": "ChatGPT", "color": "#61a8ff"},
    "Claude Code": {"label": "Claude", "plan": "Claude", "color": "#ff9f43"},
    "Gemini CLI": {"label": "Gemini", "plan": "Gemini", "color": "#23d8aa"},
    "Grok Build": {"label": "Grok", "plan": "Grok", "color": "#b180ff"},
    "MiniMax": {"label": "MiniMax", "plan": "MiniMax", "color": "#ff5b8d"},
    "Kimi": {"label": "Kimi", "plan": "Kimi", "color": "#ffd166"},
    "GLM": {"label": "GLM", "plan": "GLM", "color": "#41c7ff"},
    "Bailian": {"label": "阿里百炼", "plan": "阿里百炼", "color": "#7ddc72"},
}
DEFAULT_ENABLED_PROVIDERS = tuple(PROVIDER_META)


def render_dashboard(
    usages: list[Usage],
    days: int,
    source_files: dict[str, int],
    pricing: dict[str, Any],
    app_version: str = "development",
    deepseek_tiers: dict[str, str] | None = None,
    enabled_providers: list[str] | tuple[str, ...] | None = None,
    display_currency: str = "USD",
    fx_cache: dict | None = None,
) -> str:
    """Render the overview and provider details from one provider-neutral payload."""
    if deepseek_tiers is None:
        deepseek_tiers = load_deepseek_tier_map(DEFAULT_DEEPSEEK_TIER_MAP)
    today = report_today()
    display_currency = display_currency if display_currency in {"USD", "CNY"} else "USD"
    dates = [(today - dt.timedelta(days=index)).isoformat() for index in range(days - 1, -1, -1)]
    fx_payload = fx_rates.browser_payload(fx_cache or {}, dates)
    usd_cny_by_date = fx_payload["usd_cny_by_date"]
    requested = DEFAULT_ENABLED_PROVIDERS if enabled_providers is None else enabled_providers
    enabled = tuple(provider for provider in requested if provider in PROVIDER_META)
    usages = [item for item in usages if item.provider in enabled]
    by_provider: dict[str, list[Usage]] = {provider: [] for provider in enabled}
    for item in usages:
        if item.provider in by_provider:
            by_provider[item.provider].append(item)

    providers = []
    total_input = total_output = total_cached = total_tokens = 0
    for provider in enabled:
        meta = PROVIDER_META[provider]
        items = by_provider[provider]
        daily = {date: {"input": 0, "output": 0, "cached": 0, "tokens": 0, "cost": 0.0, "cost_cny": 0.0, "unpriced": 0} for date in dates}
        models: dict[str, Usage] = {}
        model_costs: dict[str, float] = defaultdict(float)
        model_costs_cny: dict[str, float] = defaultdict(float)
        model_deepseek_costs: dict[str, float] = defaultdict(float)
        model_deepseek_costs_cny: dict[str, float] = defaultdict(float)
        priced_models: set[str] = set()
        deepseek_priced_models: set[str] = set()
        estimated_pricing_models: set[str] = set()
        estimated_pricing_targets: dict[str, set[str]] = defaultdict(set)
        provider_input = provider_output = provider_cached = provider_tokens = provider_unpriced = 0
        provider_cost = 0.0
        provider_deepseek_cost = 0.0
        provider_deepseek_matched = 0
        estimated = False
        for item in items:
            if item.date not in daily:
                continue
            resolved_pricing_model, pricing_estimated = pricing_model_for_usage(item, pricing)
            if pricing_estimated:
                estimated_pricing_models.add(item.model)
                estimated_pricing_targets[item.model].add(resolved_pricing_model)
            cost = api_equivalent_cost(item, pricing)
            deepseek_cost = deepseek_equivalent_cost(item, pricing, deepseek_tiers)
            if deepseek_cost is not None:
                provider_deepseek_cost += deepseek_cost
                provider_deepseek_matched += item.total_tokens
                model_deepseek_costs[item.model] += deepseek_cost
                rate = usd_cny_by_date.get(item.date)
                if rate is not None:
                    model_deepseek_costs_cny[item.model] += deepseek_cost * rate
                deepseek_priced_models.add(item.model)
            row = daily[item.date]
            row["input"] += item.input_tokens
            row["output"] += item.output_tokens
            row["cached"] += item.cached_input_tokens + item.cache_write_input_tokens
            row["tokens"] += item.total_tokens
            if cost is None:
                row["unpriced"] += item.total_tokens
                provider_unpriced += item.total_tokens
            else:
                row["cost"] += cost
                rate = usd_cny_by_date.get(item.date)
                if rate is not None:
                    row["cost_cny"] += cost * rate
                provider_cost += cost
                model_costs[item.model] += cost
                if rate is not None:
                    model_costs_cny[item.model] += cost * rate
                priced_models.add(item.model)
            provider_input += item.input_tokens
            provider_output += item.output_tokens
            provider_cached += item.cached_input_tokens + item.cache_write_input_tokens
            provider_tokens += item.total_tokens
            estimated = estimated or item.is_estimate
            aggregate = models.setdefault(item.model, Usage(provider, item.model, "", cache_is_subset_of_input=item.cache_is_subset_of_input, is_estimate=item.is_estimate))
            aggregate.input_tokens += item.input_tokens
            aggregate.output_tokens += item.output_tokens
            aggregate.cached_input_tokens += item.cached_input_tokens
            aggregate.cache_write_input_tokens += item.cache_write_input_tokens
        total_input += provider_input
        total_output += provider_output
        total_cached += provider_cached
        total_tokens += provider_tokens
        hit_tokens, hit_total = cache_hit_stats(items)
        cache_hit_rate = round(hit_tokens / hit_total, 4) if hit_total else None
        model_data = []
        for item in sorted(models.values(), key=lambda value: value.total_tokens, reverse=True):
            model_cost = model_costs[item.model] if item.model in priced_models else None
            deepseek_tier = deepseek_tier_for_usage(item, pricing, deepseek_tiers) if item.model in deepseek_priced_models else None
            pricing_targets = sorted(estimated_pricing_targets[item.model])
            model_data.append({
                "model": item.model,
                "input": item.input_tokens,
                "output": item.output_tokens,
                "cached": item.cached_input_tokens + item.cache_write_input_tokens,
                "tokens": item.total_tokens,
                "cost": model_cost,
                "cost_cny": round(model_costs_cny[item.model], 8) if item.model in priced_models else None,
                "estimated": item.is_estimate or item.model in estimated_pricing_models,
                "pricing_model": " / ".join(pricing_targets) if pricing_targets else None,
                "deepseek_cost": round(model_deepseek_costs[item.model], 8) if deepseek_tier else None,
                "deepseek_cost_cny": round(model_deepseek_costs_cny[item.model], 8) if deepseek_tier else None,
                "deepseek_tier": deepseek_tier,
            })
        providers.append({
            "id": provider,
            "label": meta["label"],
            "plan": meta["plan"],
            "color": meta["color"],
            "has_data": bool(items),
            "estimated": estimated,
            "files": source_files.get(provider, 0),
            "totals": {"input": provider_input, "output": provider_output, "cached": provider_cached, "tokens": provider_tokens, "cost": round(provider_cost, 8), "cost_cny": round(sum(float(daily[date]["cost_cny"]) for date in dates), 8), "unpriced": provider_unpriced},
            "daily": [{"date": date, **daily[date], "cost": round(float(daily[date]["cost"]), 8), "cost_cny": round(float(daily[date]["cost_cny"]), 8)} for date in dates],
            "models": model_data,
            "cache_hit_rate": cache_hit_rate,
            "deepseek_cost": round(provider_deepseek_cost, 8) if provider_deepseek_matched else None,
            "deepseek_cost_cny": round(sum(model_deepseek_costs_cny.values()), 8) if provider_deepseek_matched else None,
            "deepseek_matched": provider_deepseek_matched,
        })

    default_plans = subscription_plan_data(pricing)
    generated_now = dt.datetime.now().astimezone()
    payload = {
        "days": dates,
        "today": today.isoformat(),
        "providers": providers,
        "plans": default_plans,
        "generated_at": generated_now.isoformat(timespec="seconds"),
        "unpriced_models": sorted({item.model for item in usages if api_equivalent_cost(item, pricing) is None}),
        "display_currency": display_currency,
        "fx": fx_payload,
    }
    generated_display = generated_now.strftime("%Y-%m-%d %H:%M")
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{FAVICON_TAG}<title>订阅 AI 用量报表</title><style>
:root{{--bg:#080d18;--card:#101a2b;--card2:#0c1728;--ink:#ecf5ff;--sub:#91a3bf;--line:#263854;--accent:#61a8ff;--danger:#ff6f86;color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1540px;margin:auto;padding:36px 24px 70px}}h1{{font-size:30px;margin:0;display:flex;align-items:center;gap:12px}}.brand-logo{{width:36px;height:36px;border-radius:8px;flex:none}}h2{{font-size:19px;margin:0 0 8px}}h3{{font-size:15px;margin:0 0 10px}}p{{color:var(--sub);line-height:1.6;margin:6px 0 0}}.head{{display:flex;justify-content:space-between;gap:20px;align-items:end}}.head-actions{{display:flex;align-items:center;gap:10px}}.head-actions button{{height:36px}}.section{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;margin-top:18px;overflow-x:auto}}.summary{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:12px;min-width:1280px}}.plan-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px}}.detail-summary{{display:grid;grid-template-columns:repeat(6,minmax(160px,1fr));gap:12px;min-width:1150px}}.metric-card,.plan-card{{border:1px solid var(--line);border-radius:12px;padding:14px;background:var(--card2)}}.metric-card{{display:flex;flex-direction:column;justify-content:space-between;min-height:108px}}.metric{{font-size:20px;font-weight:750;margin:0;padding-top:12px;word-break:break-word;overflow-wrap:anywhere}}.muted{{color:var(--sub)}}.hint{{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#263854;color:#91a3bf;font-size:11px;margin-left:5px;cursor:help;vertical-align:middle}}.plan-card{{min-height:126px}}.plan-card .price{{font-size:21px;font-weight:750;margin:10px 0}}.editor{{display:grid;grid-template-columns:minmax(210px,1.15fr) minmax(170px,.9fr) minmax(220px,1fr) minmax(280px,1.45fr) 132px;gap:16px;align-items:end;margin-top:24px}}label{{display:grid;gap:9px;color:var(--sub);font-size:13px}}input,select,button{{height:48px;border-radius:10px;border:1px solid var(--line);font:inherit}}input,select{{background:#0a1322;color:var(--ink);padding:0 14px;min-width:0}}input[type=number]{{appearance:textfield;-moz-appearance:textfield}}input[type=number]::-webkit-inner-spin-button,input[type=number]::-webkit-outer-spin-button{{-webkit-appearance:none;margin:0}}button{{background:var(--accent);color:#07101d;border-color:var(--accent);font-weight:750;padding:0 14px;cursor:pointer}}button:hover{{filter:brightness(1.12)}}.chartbox{{border:1px solid var(--line);border-radius:13px;padding:16px;margin-top:16px;background:var(--card2);overflow:hidden}}.legend{{display:flex;gap:17px;flex-wrap:wrap;margin:10px 0 5px;color:var(--sub)}}.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}}svg{{width:100%;height:300px;display:block}}.axis{{stroke:#365173;stroke-width:1}}.gridline{{stroke:#223651;stroke-width:1}}.tick{{fill:#91a3bf;font-size:11px}}.hoverline{{stroke:#d8f2ff;stroke-width:1;stroke-dasharray:4 4}}.tip{{position:fixed;display:none;pointer-events:none;z-index:10;background:#050b14;color:#fff;border:1px solid #405778;border-radius:9px;padding:10px 12px;font-size:12px;line-height:1.6;box-shadow:0 10px 28px #0009}}.tabs{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:20px 0 22px}}.tab{{background:#15243a;color:var(--sub);border-color:var(--line);width:100%;font-size:15px}}.tab.active{{background:var(--accent);color:#07101d}}.detail{{display:none}}.detail.active{{display:block}}table{{width:100%;border-collapse:collapse;margin-top:18px}}th,td{{padding:11px 8px;border-top:1px solid var(--line);text-align:center}}th{{font-size:12px;color:var(--sub);text-align:center}}.empty{{padding:26px;text-align:center;color:var(--sub)}}@media(max-width:900px){{.plan-grid{{grid-template-columns:1fr 1fr}}.editor{{grid-template-columns:1fr 1fr}}}}@media(max-width:560px){{main{{padding:24px 14px}}.plan-grid,.editor{{grid-template-columns:1fr}}svg{{height:260px}}}}
.help-link{{display:inline-flex;align-items:center;height:36px;border:1px solid var(--line);border-radius:9px;padding:0 12px;color:var(--ink);background:#15243a;text-decoration:none}}.currency-switch{{display:flex;height:36px;border:1px solid var(--line);border-radius:9px;overflow:hidden;background:#0a1322}}.currency-switch button{{height:34px;border:0;border-radius:0;background:transparent;color:var(--sub);padding:0 11px}}.currency-switch button.active{{background:var(--accent);color:#07101d}}.fx-note{{font-size:12px;color:var(--sub);margin-top:8px}}
</style></head><body><main><div class="head"><div><h1>{LOGO_IMG}订阅 AI 用量报表</h1><p>最近 {days} 天 · 按电脑当前时区分日 · 数据来自本机日志 · API 价格数据来自 OpenRouter · Ver {html.escape(app_version)}</p></div><div class="head-actions"><span class="muted" id="refresh-status">生成于本机 · {generated_display}</span><div class="currency-switch" aria-label="显示货币"><button id="currency-usd" data-currency="USD">USD</button><button id="currency-cny" data-currency="CNY">CNY</button></div><a class="help-link" href="http://127.0.0.1:17653/help">配置及使用说明</a><button id="refresh-local">更新本机数据</button></div></div>
<section class="section"><div class="summary"><div class="metric-card"><div class="muted">总 Token</div><div class="metric">{number(total_tokens)}</div></div><div class="metric-card"><div class="muted">输入 Token</div><div class="metric">{number(total_input)}</div></div><div class="metric-card"><div class="muted">输出 Token</div><div class="metric">{number(total_output)}</div></div><div class="metric-card"><div class="muted">API 等价价值</div><div class="metric" id="summary-api">—</div></div><div class="metric-card"><div class="muted">有效订阅成本<span class="hint" data-tip="按这段时间里每天实际生效的订阅价格计算；订阅价格中途变动过的话，这里会是新旧价格混合后的结果。">?</span></div><div class="metric" id="summary-sub">—</div></div><div class="metric-card"><div class="muted">价值倍数</div><div class="metric" id="summary-ratio">—</div></div><div class="metric-card"><div class="muted">对应 DeepSeek 成本<span class="hint" data-tip="各平台已计价模型的 DeepSeek 参考成本合计。">?</span></div><div class="metric" id="summary-deepseek">—</div></div></div><p class="muted" style="margin-top:14px">无法确认具体模型的记录保留 Token，但不参与价格计算；所示金额为已确认模型的保守估算。</p></section>
<section class="section"><h2>订阅计划</h2><p>每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。</p><div id="plan-grid" class="plan-grid"></div><div class="editor"><label>平台<select id="provider"></select></label><label>周期<select id="cycle"><option value="month">按月</option><option value="year">按年</option></select></label><label>生效日期<input id="start" type="date"></label><label><span id="amount-label">订阅金额（USD）</span><input id="amount" type="number" min="0" step="0.01" placeholder="输入订阅金额"></label><button id="save">保存计划</button></div><div class="fx-note" id="fx-note"></div></section>
<section class="section"><h2>最近 {days} 天 报表</h2><div class="chartbox"><h3>每日 Token</h3><p>各平台当天输入、输出和缓存口径合并后的 Token。</p><div class="legend" id="token-legend"></div><svg id="tokens" viewBox="0 0 1100 300" role="img" aria-label="各平台每日 Token 折线图"></svg></div><div class="chartbox"><h3>每日订阅价值倍数</h3><p>当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。</p><div class="legend" id="ratio-legend"></div><svg id="ratio" viewBox="0 0 1100 300" role="img" aria-label="各平台每日订阅价值倍数折线图"></svg></div></section>
<section class="section"><h2>平台详情</h2><div id="tabs" class="tabs"></div><div id="details"></div></section></main><div id="tip" class="tip"></div>
<script>const DATA={data};const $=id=>document.getElementById(id);let plans=Array.isArray(DATA.plans)?DATA.plans:[],displayCurrency=DATA.display_currency==='CNY'&&DATA.fx.latest_rate_date?'CNY':'USD';document.addEventListener('DOMContentLoaded',()=>{{document.querySelectorAll('.metric-card').forEach(x=>{{x.style.alignItems='center';x.style.textAlign='center'}});document.querySelectorAll('table th,table td').forEach(x=>x.style.textAlign='center')}});
const num=v=>Number(v).toLocaleString(),esc=v=>String(v).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])),rate=date=>DATA.fx.usd_cny_by_date[date]||null,convert=(value,from,to,date)=>{{if(from===to)return Number(value);let r=rate(date);if(!r)return null;return from==='USD'?Number(value)*r:Number(value)/r}},cash=(v,currency=displayCurrency)=>v===null?'—':new Intl.NumberFormat(document.documentElement.lang||'zh-CN',{{style:'currency',currency,minimumFractionDigits:2,maximumFractionDigits:2}}).format(Number(v)),multipleText=v=>v===null?'未计算':(Number(v)<.01?Number(v).toFixed(4):Number(v).toFixed(2))+'×',apiValue=(row,date)=>displayCurrency==='CNY'?(rate(date)?row.cost_cny:null):row.cost,aggregateValue=(item,key)=>displayCurrency==='CNY'?item[key+'_cny']:item[key];
function activePlan(provider,date){{return plans.filter(p=>p.provider===provider&&p.start_date<=date).sort((a,b)=>a.start_date.localeCompare(b.start_date)).pop()||null}}function dailyCost(provider,date){{let p=activePlan(provider,date);if(!p)return 0;let converted=convert(p.amount,p.currency||'USD',displayCurrency,date);return converted===null?null:converted/(p.cycle==='year'?360:30)}}
function renderSummary(){{let api=DATA.providers.reduce((n,p)=>n+(aggregateValue(p.totals,'cost')||0),0),sub=DATA.providers.reduce((n,p)=>n+p.daily.reduce((s,d)=>{{let cost=dailyCost(p.plan,d.date);return s+(cost||0)}},0),0),ds=DATA.providers.reduce((n,p)=>n+(aggregateValue(p,'deepseek_cost')||0),0);$('summary-api').textContent=cash(api);$('summary-sub').textContent=cash(sub);$('summary-ratio').textContent=multipleText(sub?api/sub:null);$('summary-deepseek').textContent=cash(ds)}}
function renderPlans(){{$('provider').innerHTML=DATA.providers.map(p=>`<option value="${{esc(p.plan)}}">${{esc(p.label)}}</option>`).join('');$('plan-grid').style.gridTemplateColumns=`repeat(${{Math.max(1,DATA.providers.length)}},minmax(0,1fr))`;let windowStart=DATA.days[0];$('plan-grid').innerHTML=DATA.providers.map(p=>{{let current=activePlan(p.plan,DATA.today);if(!current)return `<div class="plan-card"><h3>${{esc(p.label)}}</h3><div class="price">未设置</div><div class="muted">不计算订阅成本与倍数</div></div>`;let startingPlan=activePlan(p.plan,windowStart),history=plans.filter(x=>x.provider===p.plan&&(x.start_date>windowStart||(startingPlan&&x.start_date===startingPlan.start_date))).sort((a,b)=>a.start_date.localeCompare(b.start_date)),shown=h=>convert(h.amount,h.currency||'USD',displayCurrency,DATA.today),rows=history.length>1?history.map(h=>`<div class="muted">${{h.start_date}} 生效 · ${{cash(shown(h))}} / ${{h.cycle==='year'?'年':'月'}} <span>(${{h.currency||'USD'}})</span></div>`).join(''):`<div class="muted">${{current.start_date}} 生效 · 原币种 ${{current.currency||'USD'}}</div>`;return `<div class="plan-card"><h3>${{esc(p.label)}}</h3><div class="price">${{cash(shown(current))}} / ${{current.cycle==='year'?'年':'月'}}</div>${{rows}}<div class="muted">历史计划 ${{history.length}} 条</div></div>`}}).join('')}}
function chartProviders(){{return DATA.providers.filter(p=>p.has_data)}}function focusProvider(providerId){{document.querySelectorAll('path.series').forEach(path=>{{let active=path.dataset.provider===providerId;path.style.opacity=active?'1':'.16';path.setAttribute('stroke-width',active?'5':'2')}})}}function clearProviderFocus(){{document.querySelectorAll('path.series').forEach(path=>{{path.style.opacity='1';path.setAttribute('stroke-width','3')}})}}function legend(id){{$(id).innerHTML=chartProviders().map(p=>`<span class="legend-item" tabindex="0" data-provider="${{esc(p.id)}}" style="cursor:pointer;padding:4px 7px;border-radius:7px"><i class="dot" style="background:${{p.color}}"></i>${{esc(p.label)}}</span>`).join('');$(id).querySelectorAll('.legend-item').forEach(item=>{{item.onmouseenter=item.onfocus=()=>focusProvider(item.dataset.provider);item.onmouseleave=item.onblur=clearProviderFocus}})}}
function series(type){{return chartProviders().map(p=>{{return {{provider:p,values:p.daily.map(d=>{{if(type==='tokens')return d.tokens;let cost=dailyCost(p.plan,d.date),api=apiValue(d,d.date),priced=d.tokens>d.unpriced;return priced&&cost&&api!==null?api/cost:null}})}}}})}}
function chart(id,type){{let svg=$(id),w=1100,h=300,l=64,r=20,t=18,b=38,iw=w-l-r,ih=h-t-b,all=series(type),finite=all.flatMap(s=>s.values.filter(v=>v!==null)),max=Math.max(1,...finite),x=i=>l+(DATA.days.length===1?0:i*iw/(DATA.days.length-1)),y=v=>t+ih-v/max*ih;let grid=[0,.25,.5,.75,1].map(k=>`<line class="gridline" x1="${{l}}" y1="${{y(max*k)}}" x2="${{w-r}}" y2="${{y(max*k)}}"/><text class="tick" x="4" y="${{y(max*k)+4}}">${{type==='tokens'?Math.round(max*k).toLocaleString():(max*k).toFixed(1)+'×'}}</text>`).join('');let paths=all.map(s=>{{let parts=[],open=false,points=[];s.values.forEach((v,i)=>{{if(v===null){{open=false;return}}parts.push(`${{open?'L':'M'}}${{x(i).toFixed(1)}} ${{y(v).toFixed(1)}}`);points.push(`<circle cx="${{x(i)}}" cy="${{y(v)}}" r="${{finite.length===1?5:2.6}}" fill="${{s.provider.color}}"/>`);open=true}});return parts.length?`<g data-provider="${{esc(s.provider.id)}}"><path class="series" data-provider="${{esc(s.provider.id)}}" d="${{parts.join(' ')}}" fill="none" stroke="${{s.provider.color}}" stroke-width="3"/>${{points.join('')}}</g>`:''}}).join('');let labels=DATA.days.map((d,i)=>i===0||(DATA.days.length-1-i)%3===0?`<text class="tick" x="${{x(i)}}" y="292" text-anchor="middle">${{d.slice(5)}}${{i===DATA.days.length-1?'（今日）':''}}</text>`:'').join('');svg.innerHTML=grid+paths+`<line class="hoverline" visibility="hidden" x1="0" y1="${{t}}" x2="0" y2="${{t+ih}}"/><rect class="hit-area" x="${{l}}" y="${{t}}" width="${{iw}}" height="${{ih}}" fill="transparent" style="pointer-events:all"/>`+labels;let hit=svg.querySelector('.hit-area');hit.onmousemove=e=>{{let bounds=hit.getBoundingClientRect(),fraction=(e.clientX-bounds.left)/bounds.width,i=Math.max(0,Math.min(DATA.days.length-1,Math.round(fraction*(DATA.days.length-1)))),date=DATA.days[i],line=svg.querySelector('.hoverline');line.setAttribute('x1',x(i));line.setAttribute('x2',x(i));line.setAttribute('visibility','visible');let rows=chartProviders().map(p=>{{let d=p.daily[i];if(type==='tokens')return `<span style="color:${{p.color}}">${{esc(p.label)}}</span>：${{num(d.tokens)}} Token`;let sub=dailyCost(p.plan,date),api=apiValue(d,date),priced=d.tokens>d.unpriced,ratio=priced&&sub&&api!==null?api/sub:null,status=sub===null?'汇率不可用':!sub?'无生效计划':!d.tokens?'无用量记录':!priced?'模型未计价':ratio===null?'汇率不可用':ratio.toFixed(2)+'×'+(d.unpriced?'（仅已计价部分）':'');return `<span style="color:${{p.color}}">${{esc(p.label)}}</span>：${{status}}<br>API ${{cash(api)}} · 日成本 ${{cash(sub)}}`}}).join('<br>');$('tip').innerHTML=`${{date}}<br>${{rows}}`;$('tip').style.display='block';$('tip').style.left=Math.min(e.clientX+14,window.innerWidth-260)+'px';$('tip').style.top=(e.clientY+14)+'px'}};hit.onmouseleave=()=>{{svg.querySelector('.hoverline').setAttribute('visibility','hidden');$('tip').style.display='none'}}}}
function renderDetails(){{$('tabs').style.gridTemplateColumns=`repeat(${{Math.max(1,DATA.providers.length)}},minmax(0,1fr))`;$('tabs').innerHTML=DATA.providers.map((p,i)=>`<button class="tab ${{i===0?'active':''}}" data-id="${{esc(p.id)}}">${{esc(p.label)}}</button>`).join('');$('details').innerHTML=DATA.providers.map((p,i)=>{{let t=p.totals,subscription=p.daily.reduce((sum,d)=>sum+(dailyCost(p.plan,d.date)||0),0),api=aggregateValue(t,'cost'),hasPriced=t.tokens>t.unpriced,multiple=subscription&&hasPriced&&api!==null?api/subscription:null,rows=p.models.map(m=>{{let modelCost=aggregateValue(m,'cost'),deepseekCost=aggregateValue(m,'deepseek_cost'),estimate=m.pricing_model?`<span class="hint" data-tip="Auto 无法确认实际路由，按当前订阅最低价模型 ${{esc(m.pricing_model)}} 估算">?</span>`:(m.estimated?'（估算）':'');return `<tr><td>${{esc(m.model)}}${{estimate}}</td><td>${{num(m.input)}}</td><td>${{num(m.output)}}</td><td>${{num(m.cached)}}</td><td>${{num(m.tokens)}}</td><td>${{m.cost===null?'未公开价格':cash(modelCost)}}</td><td>${{m.deepseek_tier?`${{cash(deepseekCost)}}<span class="hint" data-tip="${{m.deepseek_tier==='pro'?'对应 DeepSeek V4 Pro':'对应 DeepSeek V4 Flash'}}">?</span>`:'—'}}</td></tr>`}}).join('')||'<tr><td colspan="7" class="empty">本机没有可解析记录</td></tr>';return `<div class="detail ${{i===0?'active':''}}" data-id="${{esc(p.id)}}"><div class="detail-summary"><div class="metric-card"><div class="muted">最近 {days} 天总 Token</div><div class="metric">${{num(t.tokens)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天 API 等价价值</div><div class="metric">${{cash(api)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天有效订阅成本<span class="hint" data-tip="按这段时间里每天实际生效的订阅价格计算；订阅价格中途变动过的话，这里会是新旧价格混合后的结果。">?</span></div><div class="metric">${{cash(subscription)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天同区间价值倍数</div><div class="metric">
${{multipleText(multiple)}}
</div></div><div class="metric-card"><div class="muted">缓存命中率</div><div class="metric">${{p.cache_hit_rate===null?'—':(p.cache_hit_rate*100).toFixed(1)+'%'}}</div></div><div class="metric-card"><div class="muted">对应 DeepSeek 成本<span class="hint" data-tip="以 DeepSeek 定价核算的成本，缓存命中率已计入">?</span></div><div class="metric">${{p.deepseek_cost===null?'—':cash(aggregateValue(p,'deepseek_cost'))}}</div></div></div><table><thead><tr><th>模型</th><th>输入</th><th>输出</th><th>缓存输入</th><th>总 Token</th><th>API 等价价值</th><th>对应 DeepSeek</th></tr></thead><tbody>${{rows}}</tbody></table></div>`}}).join('');document.querySelectorAll('.tab').forEach(tab=>tab.onclick=()=>{{document.querySelectorAll('.tab,.detail').forEach(x=>x.classList.remove('active'));tab.classList.add('active');document.querySelector(`.detail[data-id="${{CSS.escape(tab.dataset.id)}}"]`).classList.add('active')}})}}
$('save').onclick=async()=>{{let provider=$('provider').value,cycle=$('cycle').value,start=$('start').value,amount=Number($('amount').value);if(!start||!(amount>0))return;let candidate={{provider,start_date:start,cycle,amount,currency:displayCurrency}};try{{let response=await fetch('http://127.0.0.1:17653/plans',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(candidate)}});if(!response.ok)throw new Error();let result=await response.json();plans=result.plans;$('start').value='';$('amount').value='';renderPlans();renderSummary();chart('ratio','ratio');renderDetails()}}catch{{alert('本机应用未运行，订阅计划没有保存')}}}};
async function setCurrency(currency){{if(currency==='CNY'&&!DATA.fx.latest_rate_date)return;displayCurrency=currency;document.querySelectorAll('.currency-switch button').forEach(button=>button.classList.toggle('active',button.dataset.currency===currency));$('amount-label').textContent=`订阅金额（${{currency}}）`;$('fx-note').textContent=DATA.fx.latest_rate_date?`汇率来源：ECB · 最新参考日期 ${{DATA.fx.latest_rate_date}} · 历史金额按每日参考汇率换算`:'汇率尚未取得，当前只能显示 USD';renderPlans();renderSummary();chart('ratio','ratio');renderDetails();try{{await fetch('http://127.0.0.1:17653/settings',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{action:'set_display_currency',value:currency}})}})}}catch{{}}}}
document.querySelectorAll('.currency-switch button').forEach(button=>button.onclick=()=>setCurrency(button.dataset.currency));if(!DATA.fx.latest_rate_date)$('currency-cny').disabled=true;
$('refresh-local').onclick=async()=>{{let status=$('refresh-status');status.textContent='正在更新…';try{{let response=await fetch('http://127.0.0.1:17653/refresh',{{method:'POST'}});if(!response.ok)throw new Error();status.textContent='更新完成，正在打开本机报表';setTimeout(()=>location.href='http://127.0.0.1:17653/report',350)}}catch{{status.textContent='本机应用未运行'}}}};let reportVersion=0;async function syncReport(){{try{{let response=await fetch('http://127.0.0.1:17653/state?page=report&ts='+Date.now(),{{cache:'no-store'}});if(!response.ok)return;let state=await response.json();if(reportVersion&&state.report_version!==reportVersion)location.replace('http://127.0.0.1:17653/report?ts='+Date.now());reportVersion=state.report_version}}catch{{}}}}setInterval(syncReport,1000);syncReport();legend('token-legend');legend('ratio-legend');chart('tokens','tokens');setCurrency(displayCurrency);document.body.addEventListener('mouseover',e=>{{let h=e.target.closest('.hint');if(!h)return;let r=h.getBoundingClientRect(),box=$('tip');box.textContent=h.dataset.tip;box.style.display='block';box.style.left=Math.min(r.left,window.innerWidth-260)+'px';box.style.top=(r.bottom+8)+'px'}});document.body.addEventListener('mouseout',e=>{{if(e.target.closest('.hint'))$('tip').style.display='none'}});</script></body></html>'''


def collect_usages(
    days: int,
    codex_sessions: Path = LOCAL_CODEX_SESSIONS,
    claude_projects: Path = LOCAL_CLAUDE_PROJECTS,
    gemini_sessions: Path = LOCAL_GEMINI_SESSIONS,
    grok_sessions: Path = LOCAL_GROK_SESSIONS,
    minimax_database: Path = LOCAL_MINIMAX_DB,
    enabled_providers: list[str] | tuple[str, ...] | None = None,
) -> tuple[list[Usage], dict[str, int]]:
    configured = {(item["provider"], item["surface"]): Path(item["path"]) for item in load_configured_sources()}
    codex_sessions = configured.get(("chatgpt", "chatgpt-desktop"), codex_sessions)
    claude_projects = configured.get(("claude", "claude-code"), claude_projects)
    gemini_sessions = configured.get(("gemini", "gemini-cli"), gemini_sessions)
    grok_sessions = configured.get(("grok", "grok-local"), grok_sessions)
    minimax_root = configured.get(("minimax", "minimax-agent"))
    if minimax_root is not None:
        minimax_database = minimax_root / "sqlite.db"
    since = report_today() - dt.timedelta(days=days - 1)
    enabled = set(DEFAULT_ENABLED_PROVIDERS if enabled_providers is None else enabled_providers)
    codex_usages, codex_files = parse_codex(codex_sessions, since) if "Codex" in enabled else ([], 0)
    bound_sources = [(provider, configured[(key, "claude-code")])
                     for key, provider in (("kimi", "Kimi"), ("glm", "GLM"), ("bailian", "Bailian"))
                     if (key, "claude-code") in configured]
    bound_roots = tuple(root for _, root in bound_sources)
    for index, root in enumerate(bound_roots):
        for other in bound_roots[index + 1:]:
            if root.resolve().is_relative_to(other.resolve()) or other.resolve().is_relative_to(root.resolve()):
                raise ValueError("subscription source directories must not overlap")
    claude_usages, claude_files = parse_claude_code(claude_projects, since, excluded_roots=bound_roots) if "Claude Code" in enabled else ([], 0)
    gemini_usages, gemini_files = parse_gemini_cli(gemini_sessions, since) if "Gemini CLI" in enabled else ([], 0)
    grok_usages, grok_files = parse_grok_build(grok_sessions, since) if "Grok Build" in enabled else ([], 0)
    minimax_usages, minimax_files = parse_minimax(minimax_database, since) if "MiniMax" in enabled else ([], 0)
    source_files = {
        "Codex": codex_files, "Claude Code": claude_files, "Gemini CLI": gemini_files,
        "Grok Build": grok_files, "MiniMax": minimax_files, "Kimi": 0, "GLM": 0, "Bailian": 0,
    }
    extra_usages = []
    for provider, root in bound_sources:
        if provider in enabled:
            items, count = parse_claude_code(root, since, provider=provider)
            extra_usages.extend(items)
            source_files[provider] += count
    if "Kimi" in enabled:
        kimi_root = configured.get(("kimi", "kimi-code"), Path.home() / ".kimi" / "sessions")
        items, count = parse_kimi_wire(kimi_root, since)
        extra_usages.extend(items)
        source_files["Kimi"] += count
    return codex_usages + claude_usages + gemini_usages + grok_usages + minimax_usages + extra_usages, source_files


def generate_report(days: int = 30, output: Path = DEFAULT_OUTPUT, pricing_path: Path = DEFAULT_PRICING, language: str = "zh-CN") -> Path:
    usages, source_files = collect_usages(days)
    pricing = load_pricing(pricing_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(localize_html(render_dashboard(usages, days, source_files, pricing), language), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local AI subscription usage report.")
    parser.add_argument("--days", type=int, default=30, help="Number of trailing calendar days to include.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Static HTML output path.")
    parser.add_argument("--codex-sessions", type=Path, default=LOCAL_CODEX_SESSIONS, help="Codex sessions directory.")
    parser.add_argument("--claude-projects", type=Path, default=LOCAL_CLAUDE_PROJECTS, help="Claude Code projects directory.")
    parser.add_argument("--gemini-sessions", type=Path, default=LOCAL_GEMINI_SESSIONS, help="Gemini CLI session directory.")
    parser.add_argument("--grok-sessions", type=Path, default=LOCAL_GROK_SESSIONS, help="Grok Build session directory.")
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING, help="Verified API price table JSON.")
    parser.add_argument("--language", choices=["zh-CN", "en", "ja", "ko", "fr", "de", "es"], default="zh-CN", help="Report language.")
    args = parser.parse_args()
    if args.days < 1:
        raise SystemExit("--days 必须大于 0")
    since = dt.date.today() - dt.timedelta(days=args.days - 1)
    codex_usages, codex_files = parse_codex(args.codex_sessions, since)
    claude_usages, claude_files = parse_claude_code(args.claude_projects, since)
    gemini_usages, gemini_files = parse_gemini_cli(args.gemini_sessions, since)
    grok_usages, grok_files = parse_grok_build(args.grok_sessions, since)
    pricing = load_pricing(args.pricing)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    all_usages = codex_usages + claude_usages + gemini_usages + grok_usages
    source_files = {"Codex": codex_files, "Claude Code": claude_files, "Gemini CLI": gemini_files, "Grok Build": grok_files}
    page = localize_html(render_dashboard(all_usages, args.days, source_files, pricing), args.language)
    args.output.write_text(page, encoding="utf-8")
    print(f"已生成：{args.output}")


if __name__ == "__main__":
    main()
