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
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from favicon import FAVICON_TAG, LOGO_IMG
from report_i18n import localize_html
from source_discovery import load_configured_sources


LOCAL_CODEX_SESSIONS = Path.home() / ".codex" / "sessions"
LOCAL_CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
LOCAL_GEMINI_HOME = Path.home() / ".gemini"
LOCAL_GEMINI_SESSIONS = LOCAL_GEMINI_HOME / "tmp"
LOCAL_GROK_SESSIONS = Path.home() / ".grok" / "sessions"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "ai-usage-report.html"
DEFAULT_PRICING = PROJECT_ROOT / "config" / "pricing.json"
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
                key = (date, current_model)
                usage = usages.setdefault(key, Usage("Codex", current_model, date, cache_is_subset_of_input=True))
                usage.input_tokens += delta["input_tokens"]
                usage.output_tokens += delta["output_tokens"]
                usage.cached_input_tokens += delta["cached_input_tokens"]

    return sorted(usages.values(), key=lambda item: (item.date, item.model)), files_read


def parse_claude_code(root: Path, since: dt.date) -> tuple[list[Usage], int]:
    """Parse Claude Code's per-response usage entries from local JSONL files."""
    usages: dict[tuple[str, str], Usage] = {}
    responses: dict[str, tuple[str, str, dict[str, Any]]] = {}
    files_read = 0
    if not root.exists():
        return [], files_read
    for path in sorted(root.rglob("*.jsonl")):
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
                responses[response_id] = (date, model, usage)
    for date, model, usage in responses.values():
        key = (date, model)
        item = usages.setdefault(key, Usage("Claude Code", model, date))
        item.input_tokens += as_int(usage.get("input_tokens"))
        item.output_tokens += as_int(usage.get("output_tokens"))
        # Claude keeps creation and read cache counters separately.
        item.cached_input_tokens += as_int(usage.get("cache_read_input_tokens"))
        item.cache_write_input_tokens += as_int(usage.get("cache_creation_input_tokens"))
    return sorted(usages.values(), key=lambda item: (item.date, item.model)), files_read


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


def api_equivalent_cost(item: Usage, pricing: dict[str, Any]) -> float | None:
    models = pricing.get("models") if isinstance(pricing.get("models"), dict) else {}
    rate = models.get(item.model)
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
    provider_names = {"Codex": "ChatGPT", "Claude": "Claude", "Gemini": "Gemini", "Grok": "Grok"}
    cleaned = []
    for configured_name, browser_name in provider_names.items():
        config = subscriptions.get(configured_name)
        plans = config.get("plans") if isinstance(config, dict) and isinstance(config.get("plans"), list) else []
        for plan in plans:
            if not isinstance(plan, dict) or not isinstance(plan.get("start_date"), str):
                continue
            if isinstance(plan.get("monthly_usd"), (int, float)):
                cleaned.append({"provider": browser_name, "start_date": plan["start_date"], "amount": float(plan["monthly_usd"]), "cycle": "month"})
            elif isinstance(plan.get("annual_usd"), (int, float)):
                cleaned.append({"provider": browser_name, "start_date": plan["start_date"], "amount": float(plan["annual_usd"]), "cycle": "year"})
    return sorted(cleaned, key=lambda item: (item["provider"], item["start_date"]))



PROVIDER_META = {
    "Codex": {"label": "ChatGPT", "plan": "ChatGPT", "color": "#61a8ff"},
    "Claude Code": {"label": "Claude", "plan": "Claude", "color": "#ff9f43"},
    "Gemini CLI": {"label": "Gemini", "plan": "Gemini", "color": "#23d8aa"},
    "Grok Build": {"label": "Grok", "plan": "Grok", "color": "#b180ff"},
}


def render_dashboard(
    usages: list[Usage],
    days: int,
    source_files: dict[str, int],
    pricing: dict[str, Any],
    app_version: str = "development",
) -> str:
    """Render the overview and provider details from one provider-neutral payload."""
    today = report_today()
    dates = [(today - dt.timedelta(days=index)).isoformat() for index in range(days - 1, -1, -1)]
    by_provider: dict[str, list[Usage]] = {provider: [] for provider in PROVIDER_META}
    for item in usages:
        if item.provider in by_provider:
            by_provider[item.provider].append(item)

    providers = []
    total_input = total_output = total_cached = total_tokens = 0
    for provider, meta in PROVIDER_META.items():
        items = by_provider[provider]
        daily = {date: {"input": 0, "output": 0, "cached": 0, "tokens": 0, "cost": 0.0, "unpriced": 0} for date in dates}
        models: dict[str, Usage] = {}
        model_costs: dict[str, float] = defaultdict(float)
        priced_models: set[str] = set()
        provider_input = provider_output = provider_cached = provider_tokens = provider_unpriced = 0
        provider_cost = 0.0
        estimated = False
        for item in items:
            if item.date not in daily:
                continue
            cost = api_equivalent_cost(item, pricing)
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
                provider_cost += cost
                model_costs[item.model] += cost
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
        model_data = []
        for item in sorted(models.values(), key=lambda value: value.total_tokens, reverse=True):
            model_cost = model_costs[item.model] if item.model in priced_models else None
            model_data.append({
                "model": item.model,
                "input": item.input_tokens,
                "output": item.output_tokens,
                "cached": item.cached_input_tokens + item.cache_write_input_tokens,
                "tokens": item.total_tokens,
                "cost": model_cost,
                "estimated": item.is_estimate,
            })
        providers.append({
            "id": provider,
            "label": meta["label"],
            "plan": meta["plan"],
            "color": meta["color"],
            "has_data": bool(items),
            "estimated": estimated,
            "files": source_files.get(provider, 0),
            "totals": {"input": provider_input, "output": provider_output, "cached": provider_cached, "tokens": provider_tokens, "cost": round(provider_cost, 8), "unpriced": provider_unpriced},
            "daily": [{"date": date, **daily[date], "cost": round(float(daily[date]["cost"]), 8)} for date in dates],
            "models": model_data,
        })

    default_plans = subscription_plan_data(pricing)
    payload = {
        "days": dates,
        "today": today.isoformat(),
        "providers": providers,
        "plans": default_plans,
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "unpriced_models": sorted({item.model for item in usages if api_equivalent_cost(item, pricing) is None}),
    }
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{FAVICON_TAG}<title>订阅 AI 用量报表</title><style>
:root{{--bg:#080d18;--card:#101a2b;--card2:#0c1728;--ink:#ecf5ff;--sub:#91a3bf;--line:#263854;--accent:#61a8ff;--danger:#ff6f86;color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1540px;margin:auto;padding:36px 24px 70px}}h1{{font-size:30px;margin:0;display:flex;align-items:center;gap:12px}}.brand-logo{{width:36px;height:36px;border-radius:8px;flex:none}}h2{{font-size:19px;margin:0 0 8px}}h3{{font-size:15px;margin:0 0 10px}}p{{color:var(--sub);line-height:1.6;margin:6px 0 0}}.head{{display:flex;justify-content:space-between;gap:20px;align-items:end}}.head-actions{{display:flex;align-items:center;gap:10px}}.head-actions button{{height:36px}}.section{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;margin-top:18px;overflow-x:auto}}.summary{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;min-width:1100px}}.plan-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px}}.detail-summary{{display:grid;grid-template-columns:repeat(5,minmax(180px,1fr));gap:12px;min-width:980px}}.metric-card,.plan-card{{border:1px solid var(--line);border-radius:12px;padding:14px;background:var(--card2)}}.metric-card{{display:flex;flex-direction:column;justify-content:space-between;min-height:108px}}.metric{{font-size:20px;font-weight:750;margin:0;padding-top:12px;word-break:break-word;overflow-wrap:anywhere}}.muted{{color:var(--sub)}}.plan-card{{min-height:126px}}.plan-card .price{{font-size:21px;font-weight:750;margin:10px 0}}.editor{{display:grid;grid-template-columns:minmax(210px,1.15fr) minmax(170px,.9fr) minmax(220px,1fr) minmax(280px,1.45fr) 132px;gap:16px;align-items:end;margin-top:24px}}label{{display:grid;gap:9px;color:var(--sub);font-size:13px}}input,select,button{{height:48px;border-radius:10px;border:1px solid var(--line);font:inherit}}input,select{{background:#0a1322;color:var(--ink);padding:0 14px;min-width:0}}input[type=number]{{appearance:textfield;-moz-appearance:textfield}}input[type=number]::-webkit-inner-spin-button,input[type=number]::-webkit-outer-spin-button{{-webkit-appearance:none;margin:0}}button{{background:var(--accent);color:#07101d;border-color:var(--accent);font-weight:750;padding:0 14px;cursor:pointer}}button:hover{{filter:brightness(1.12)}}.chartbox{{border:1px solid var(--line);border-radius:13px;padding:16px;margin-top:16px;background:var(--card2);overflow:hidden}}.legend{{display:flex;gap:17px;flex-wrap:wrap;margin:10px 0 5px;color:var(--sub)}}.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}}svg{{width:100%;height:300px;display:block}}.axis{{stroke:#365173;stroke-width:1}}.gridline{{stroke:#223651;stroke-width:1}}.tick{{fill:#91a3bf;font-size:11px}}.hoverline{{stroke:#d8f2ff;stroke-width:1;stroke-dasharray:4 4}}.tip{{position:fixed;display:none;pointer-events:none;z-index:10;background:#050b14;color:#fff;border:1px solid #405778;border-radius:9px;padding:10px 12px;font-size:12px;line-height:1.6;box-shadow:0 10px 28px #0009}}.tabs{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:20px 0 22px}}.tab{{background:#15243a;color:var(--sub);border-color:var(--line);width:100%;font-size:15px}}.tab.active{{background:var(--accent);color:#07101d}}.detail{{display:none}}.detail.active{{display:block}}table{{width:100%;border-collapse:collapse;margin-top:18px}}th,td{{padding:11px 8px;border-top:1px solid var(--line);text-align:center}}th{{font-size:12px;color:var(--sub);text-align:center}}.empty{{padding:26px;text-align:center;color:var(--sub)}}@media(max-width:900px){{.plan-grid{{grid-template-columns:1fr 1fr}}.editor{{grid-template-columns:1fr 1fr}}}}@media(max-width:560px){{main{{padding:24px 14px}}.plan-grid,.editor{{grid-template-columns:1fr}}svg{{height:260px}}}}
.help-link{{display:inline-flex;align-items:center;height:36px;border:1px solid var(--line);border-radius:9px;padding:0 12px;color:var(--ink);background:#15243a;text-decoration:none}}
</style></head><body><main><div class="head"><div><h1>{LOGO_IMG}订阅 AI 用量报表</h1><p>最近 {days} 天 · 按电脑当前时区分日 · 数据来自本机日志 · Ver {html.escape(app_version)}</p></div><div class="head-actions"><span class="muted" id="refresh-status">生成于本机</span><a class="help-link" href="http://127.0.0.1:17653/help">配置及使用说明</a><button id="refresh-local">更新本机数据</button></div></div>
<section class="section"><div class="summary"><div class="metric-card"><div class="muted">总 Token</div><div class="metric">{number(total_tokens)}</div></div><div class="metric-card"><div class="muted">输入 Token</div><div class="metric">{number(total_input)}</div></div><div class="metric-card"><div class="muted">输出 Token</div><div class="metric">{number(total_output)}</div></div><div class="metric-card"><div class="muted">API 等价价值</div><div class="metric" id="summary-api">—</div></div><div class="metric-card"><div class="muted">有效订阅成本</div><div class="metric" id="summary-sub">—</div></div><div class="metric-card"><div class="muted">价值倍数</div><div class="metric" id="summary-ratio">—</div></div></div></section>
<section class="section"><h2>订阅计划</h2><p>每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。</p><div id="plan-grid" class="plan-grid"></div><div class="editor"><label>平台<select id="provider"></select></label><label>周期<select id="cycle"><option value="month">按月</option><option value="year">按年</option></select></label><label>生效日期<input id="start" type="date"></label><label>订阅金额（USD）<input id="amount" type="number" min="0" step="0.01" placeholder="输入订阅金额"></label><button id="save">保存计划</button></div></section>
<section class="section"><h2>最近 {days} 天 报表</h2><div class="chartbox"><h3>每日 Token</h3><p>各平台当天输入、输出和缓存口径合并后的 Token。</p><div class="legend" id="token-legend"></div><svg id="tokens" viewBox="0 0 1100 300" role="img" aria-label="各平台每日 Token 折线图"></svg></div><div class="chartbox"><h3>每日订阅价值倍数</h3><p>当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。</p><div class="legend" id="ratio-legend"></div><svg id="ratio" viewBox="0 0 1100 300" role="img" aria-label="各平台每日订阅价值倍数折线图"></svg></div></section>
<section class="section"><h2>平台详情</h2><div id="tabs" class="tabs"></div><div id="details"></div></section></main><div id="tip" class="tip"></div>
<script>const DATA={data};const $=id=>document.getElementById(id);let plans=Array.isArray(DATA.plans)?DATA.plans:[];document.addEventListener('DOMContentLoaded',()=>{{document.querySelectorAll('.metric-card').forEach(x=>{{x.style.alignItems='center';x.style.textAlign='center'}});document.querySelectorAll('table th,table td').forEach(x=>x.style.textAlign='center')}});
const cash=v=>'$'+Number(v).toFixed(2),num=v=>Number(v).toLocaleString(),esc=v=>String(v).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function activePlan(provider,date){{return plans.filter(p=>p.provider===provider&&p.start_date<=date).sort((a,b)=>a.start_date.localeCompare(b.start_date)).pop()||null}}function dailyCost(provider,date){{let p=activePlan(provider,date);return p?p.amount/(p.cycle==='year'?360:30):0}}
function renderSummary(){{let api=DATA.providers.reduce((n,p)=>n+p.totals.cost,0),sub=DATA.providers.reduce((n,p)=>n+p.daily.reduce((s,d)=>s+dailyCost(p.plan,d.date),0),0);$('summary-api').textContent=cash(api);$('summary-sub').textContent=cash(sub);$('summary-ratio').textContent=sub?(api/sub).toFixed(2)+'×':'未计算'}}
function renderPlans(){{$('provider').innerHTML=DATA.providers.map(p=>`<option value="${{esc(p.plan)}}">${{esc(p.label)}}</option>`).join('');$('plan-grid').innerHTML=DATA.providers.map(p=>{{let current=activePlan(p.plan,DATA.today);return `<div class="plan-card"><h3>${{esc(p.label)}}</h3>${{current?`<div class="price">${{cash(current.amount)}} / ${{current.cycle==='year'?'年':'月'}}</div><div class="muted">${{current.start_date}} 生效</div><div class="muted">历史计划 ${{plans.filter(x=>x.provider===p.plan).length}} 条</div>`:'<div class="price">未设置</div><div class="muted">不计算订阅成本与倍数</div>'}}</div>`}}).join('')}}
function focusProvider(providerId){{document.querySelectorAll('path.series').forEach(path=>{{let active=path.dataset.provider===providerId;path.style.opacity=active?'1':'.16';path.setAttribute('stroke-width',active?'5':'2')}})}}function clearProviderFocus(){{document.querySelectorAll('path.series').forEach(path=>{{path.style.opacity='1';path.setAttribute('stroke-width','3')}})}}function legend(id){{$(id).innerHTML=DATA.providers.map(p=>`<span class="legend-item" tabindex="0" data-provider="${{esc(p.id)}}" style="cursor:pointer;padding:4px 7px;border-radius:7px"><i class="dot" style="background:${{p.color}}"></i>${{esc(p.label)}}${{p.has_data?'':'（无数据）'}}</span>`).join('');$(id).querySelectorAll('.legend-item').forEach(item=>{{item.onmouseenter=item.onfocus=()=>focusProvider(item.dataset.provider);item.onmouseleave=item.onblur=clearProviderFocus}})}}
function series(type){{return DATA.providers.map(p=>{{let hasPriced=p.totals.tokens>p.totals.unpriced;return {{provider:p,values:p.daily.map(d=>{{if(!p.has_data)return null;if(type==='tokens')return d.tokens;let cost=dailyCost(p.plan,d.date);return hasPriced&&cost?d.cost/cost:null}})}}}})}}
function chart(id,type){{let svg=$(id),w=1100,h=300,l=64,r=20,t=18,b=38,iw=w-l-r,ih=h-t-b,all=series(type),finite=all.flatMap(s=>s.values.filter(v=>v!==null)),max=Math.max(1,...finite),x=i=>l+(DATA.days.length===1?0:i*iw/(DATA.days.length-1)),y=v=>t+ih-v/max*ih;let grid=[0,.25,.5,.75,1].map(k=>`<line class="gridline" x1="${{l}}" y1="${{y(max*k)}}" x2="${{w-r}}" y2="${{y(max*k)}}"/><text class="tick" x="4" y="${{y(max*k)+4}}">${{type==='tokens'?Math.round(max*k).toLocaleString():(max*k).toFixed(1)+'×'}}</text>`).join('');let paths=all.map(s=>{{let parts=[],open=false,points=[];s.values.forEach((v,i)=>{{if(v===null){{open=false;return}}parts.push(`${{open?'L':'M'}}${{x(i).toFixed(1)}} ${{y(v).toFixed(1)}}`);points.push(`<circle cx="${{x(i)}}" cy="${{y(v)}}" r="${{finite.length===1?5:2.6}}" fill="${{s.provider.color}}"/>`);open=true}});return parts.length?`<g data-provider="${{esc(s.provider.id)}}"><path class="series" data-provider="${{esc(s.provider.id)}}" d="${{parts.join(' ')}}" fill="none" stroke="${{s.provider.color}}" stroke-width="3"/>${{points.join('')}}</g>`:''}}).join('');let labels=DATA.days.map((d,i)=>i%3===0?`<text class="tick" x="${{x(i)}}" y="292" text-anchor="middle">${{d.slice(5)}}</text>`:'').join('');svg.innerHTML=grid+paths+`<line class="hoverline" visibility="hidden" x1="0" y1="${{t}}" x2="0" y2="${{t+ih}}"/><rect class="hit-area" x="${{l}}" y="${{t}}" width="${{iw}}" height="${{ih}}" fill="transparent" style="pointer-events:all"/>`+labels;let hit=svg.querySelector('.hit-area');hit.onmousemove=e=>{{let bounds=hit.getBoundingClientRect(),fraction=(e.clientX-bounds.left)/bounds.width,i=Math.max(0,Math.min(DATA.days.length-1,Math.round(fraction*(DATA.days.length-1)))),date=DATA.days[i],line=svg.querySelector('.hoverline');line.setAttribute('x1',x(i));line.setAttribute('x2',x(i));line.setAttribute('visibility','visible');let rows=DATA.providers.map(p=>{{let d=p.daily[i];if(!p.has_data)return `<span style="color:${{p.color}}">${{esc(p.label)}}</span>：无数据`;if(type==='tokens')return `<span style="color:${{p.color}}">${{esc(p.label)}}</span>：${{num(d.tokens)}} Token`;let sub=dailyCost(p.plan,date),priced=p.totals.tokens>p.totals.unpriced,ratio=priced&&sub?d.cost/sub:null,status=!sub?'无生效计划':!priced?'模型未计价':ratio.toFixed(2)+'×';return `<span style="color:${{p.color}}">${{esc(p.label)}}</span>：${{status}}<br>API ${{cash(d.cost)}} · 日成本 ${{cash(sub)}}`}}).join('<br>');$('tip').innerHTML=`${{date}}<br>${{rows}}`;$('tip').style.display='block';$('tip').style.left=Math.min(e.clientX+14,window.innerWidth-260)+'px';$('tip').style.top=(e.clientY+14)+'px'}};hit.onmouseleave=()=>{{svg.querySelector('.hoverline').setAttribute('visibility','hidden');$('tip').style.display='none'}}}}
function renderDetails(){{$('tabs').innerHTML=DATA.providers.map((p,i)=>`<button class="tab ${{i===0?'active':''}}" data-id="${{esc(p.id)}}">${{esc(p.label)}}</button>`).join('');$('details').innerHTML=DATA.providers.map((p,i)=>{{let t=p.totals,subscription=p.daily.reduce((sum,d)=>sum+dailyCost(p.plan,d.date),0),hasPriced=t.tokens>t.unpriced,multiple=subscription&&hasPriced?t.cost/subscription:null,rows=p.models.map(m=>`<tr><td>${{esc(m.model)}}${{m.estimated?'（估算）':''}}</td><td>${{num(m.input)}}</td><td>${{num(m.output)}}</td><td>${{num(m.cached)}}</td><td>${{num(m.tokens)}}</td><td>${{m.cost===null?'未公开价格':cash(m.cost)}}</td></tr>`).join('')||'<tr><td colspan="6" class="empty">本机没有可解析记录</td></tr>';return `<div class="detail ${{i===0?'active':''}}" data-id="${{esc(p.id)}}"><div class="detail-summary"><div class="metric-card"><div class="muted">最近 {days} 天总 Token</div><div class="metric">${{num(t.tokens)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天 API 等价价值</div><div class="metric">${{cash(t.cost)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天有效订阅成本</div><div class="metric">${{cash(subscription)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天同区间价值倍数</div><div class="metric">${{multiple===null?'未计算':multiple.toFixed(2)+'×'}}</div></div><div class="metric-card"><div class="muted">未计价 Token</div><div class="metric">${{num(t.unpriced)}}</div></div></div><table><thead><tr><th>模型</th><th>输入</th><th>输出</th><th>缓存输入</th><th>总 Token</th><th>API 等价价值</th></tr></thead><tbody>${{rows}}</tbody></table></div>`}}).join('');document.querySelectorAll('.tab').forEach(tab=>tab.onclick=()=>{{document.querySelectorAll('.tab,.detail').forEach(x=>x.classList.remove('active'));tab.classList.add('active');document.querySelector(`.detail[data-id="${{CSS.escape(tab.dataset.id)}}"]`).classList.add('active')}})}}
$('save').onclick=async()=>{{let provider=$('provider').value,cycle=$('cycle').value,start=$('start').value,amount=Number($('amount').value);if(!start||!(amount>0))return;let candidate={{provider,start_date:start,cycle,amount}};try{{let response=await fetch('http://127.0.0.1:17653/plans',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(candidate)}});if(!response.ok)throw new Error();let result=await response.json();plans=result.plans;$('start').value='';$('amount').value='';renderPlans();renderSummary();chart('ratio','ratio');renderDetails()}}catch{{alert('本机应用未运行，订阅计划没有保存')}}}};$('refresh-local').onclick=async()=>{{let status=$('refresh-status');status.textContent='正在更新…';try{{let response=await fetch('http://127.0.0.1:17653/refresh',{{method:'POST'}});if(!response.ok)throw new Error();status.textContent='更新完成，正在打开本机报表';setTimeout(()=>location.href='http://127.0.0.1:17653/report',350)}}catch{{status.textContent='本机应用未运行'}}}};let reportVersion=0;async function syncLanguage(){{try{{let response=await fetch('http://127.0.0.1:17653/state?ts='+Date.now(),{{cache:'no-store'}});if(!response.ok)return;let state=await response.json(),current=document.documentElement.lang;if(reportVersion&&state.report_version!==reportVersion&&state.language!==current)location.replace('http://127.0.0.1:17653/report?ts='+Date.now());reportVersion=state.report_version}}catch{{}}}}setInterval(syncLanguage,1000);syncLanguage();renderPlans();renderSummary();legend('token-legend');legend('ratio-legend');chart('tokens','tokens');chart('ratio','ratio');renderDetails();</script></body></html>'''


def collect_usages(
    days: int,
    codex_sessions: Path = LOCAL_CODEX_SESSIONS,
    claude_projects: Path = LOCAL_CLAUDE_PROJECTS,
    gemini_sessions: Path = LOCAL_GEMINI_SESSIONS,
    grok_sessions: Path = LOCAL_GROK_SESSIONS,
) -> tuple[list[Usage], dict[str, int]]:
    configured = {(item["provider"], item["surface"]): Path(item["path"]) for item in load_configured_sources()}
    codex_sessions = configured.get(("chatgpt", "chatgpt-desktop"), codex_sessions)
    claude_projects = configured.get(("claude", "claude-code"), claude_projects)
    gemini_sessions = configured.get(("gemini", "gemini-cli"), gemini_sessions)
    grok_sessions = configured.get(("grok", "grok-local"), grok_sessions)
    since = report_today() - dt.timedelta(days=days - 1)
    codex_usages, codex_files = parse_codex(codex_sessions, since)
    claude_usages, claude_files = parse_claude_code(claude_projects, since)
    gemini_usages, gemini_files = parse_gemini_cli(gemini_sessions, since)
    grok_usages, grok_files = parse_grok_build(grok_sessions, since)
    source_files = {"Codex": codex_files, "Claude Code": claude_files, "Gemini CLI": gemini_files, "Grok Build": grok_files}
    return codex_usages + claude_usages + gemini_usages + grok_usages, source_files


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
