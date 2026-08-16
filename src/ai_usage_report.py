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

from report_i18n import localize_html
from claude_code_quota import load_snapshot as load_claude_quota_snapshot
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


@dataclass
class RateLimitWindow:
    window_minutes: int
    used_percent: float | None = None
    resets_at: str | None = None


@dataclass
class RateLimitSnapshot:
    windows: list[RateLimitWindow]
    source_file: str | None = None


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


def extract_rate_limit(record: dict[str, Any], source: Path) -> RateLimitSnapshot | None:
    snapshots: list[RateLimitSnapshot] = []
    for node in walk_values(record):
        if not isinstance(node.get("primary"), dict) and not isinstance(node.get("secondary"), dict):
            continue
        windows = []
        for key in ("primary", "secondary"):
            limit = node.get(key)
            if not isinstance(limit, dict):
                continue
            minutes = as_int(limit.get("window_minutes"))
            used = limit.get("used_percent")
            reset = limit.get("resets_at")
            if minutes and (isinstance(used, (int, float)) or isinstance(reset, (int, float, str))):
                windows.append(RateLimitWindow(minutes, float(used) if isinstance(used, (int, float)) else None,
                                               str(reset) if reset is not None else None))
        if windows:
            snapshots.append(RateLimitSnapshot(windows, str(source)))
    return snapshots[-1] if snapshots else None


def parse_codex(root: Path, since: dt.date) -> tuple[list[Usage], RateLimitSnapshot | None, int]:
    usages: dict[tuple[str, str], Usage] = {}
    latest_snapshot: RateLimitSnapshot | None = None
    files_read = 0
    if not root.exists():
        return [], None, files_read

    for path in sorted(root.rglob("*.jsonl")):
        files_read += 1
        current_model = "未记录模型"
        previous = {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
        latest_record_time: dt.datetime | None = None
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
                record_time = parse_timestamp(record.get("timestamp"))
                if record_time and (latest_record_time is None or record_time > latest_record_time):
                    latest_record_time = record_time
                snapshot = extract_rate_limit(record, path)
                if snapshot and latest_record_time:
                    # Files are processed in chronological path order and
                    # records in file order, so the last observed snapshot is
                    # the newest local snapshot.
                    latest_snapshot = snapshot
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

    return sorted(usages.values(), key=lambda item: (item.date, item.model)), latest_snapshot, files_read


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
    """Read Grok Build local session context snapshots.

    Grok Build does not write a billable input/output ledger. Its signals file
    records current context tokens, which is shown as an estimate only.
    """
    usages: dict[tuple[str, str], Usage] = {}
    files_read = 0
    if not root.exists():
        return [], files_read
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
                item.output_tokens += as_int(usage.get("completion_tokens", usage.get("completionTokens", usage.get("output_tokens"))))
                item.output_tokens += as_int(usage.get("reasoning_tokens", usage.get("reasoningTokens")))
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


def local_reset_time(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = dt.datetime.fromtimestamp(float(value)).astimezone()
        return parsed.strftime("%Y-%m-%d %H:%M %Z")
    except (TypeError, ValueError, OSError):
        return html.escape(value)


def quota_window(snapshot: RateLimitSnapshot | None, minutes: int) -> RateLimitWindow | None:
    if not snapshot:
        return None
    return next((item for item in snapshot.windows if item.window_minutes == minutes), None)


def render_report(usages: list[Usage], snapshot: RateLimitSnapshot | None, days: int, source_files: dict[str, int], pricing: dict[str, Any]) -> str:
    """Render one independent Codex report; provider pages remain separate."""
    today = report_today()
    dates = [(today - dt.timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]
    daily_tokens: dict[str, int] = defaultdict(int)
    daily_costs: dict[str, float] = defaultdict(float)
    models: dict[str, Usage] = {}
    totals = Usage("Codex", "全部模型", "", cache_is_subset_of_input=True)
    for item in usages:
        daily_tokens[item.date] += item.total_tokens
        cost = api_equivalent_cost(item, pricing)
        if cost is not None:
            daily_costs[item.date] += cost
        aggregate = models.setdefault(item.model, Usage("Codex", item.model, "", cache_is_subset_of_input=True))
        for target in (totals, aggregate):
            target.input_tokens += item.input_tokens
            target.output_tokens += item.output_tokens
            target.cached_input_tokens += item.cached_input_tokens
            target.cache_write_input_tokens += item.cache_write_input_tokens
    payload = {
        "days": [{"date": date, "tokens": daily_tokens[date], "api_cost": round(daily_costs[date], 8)} for date in dates],
        "plans": plan_data(pricing),
    }
    model_rows = "".join(
        f"<tr><td>{html.escape(item.model)}</td><td>{number(item.input_tokens)}</td><td>{number(item.output_tokens)}</td><td>{number(item.cached_input_tokens)}</td><td>{number(item.total_tokens)}</td><td>{money(api_equivalent_cost(item, pricing))}</td></tr>"
        for item in sorted(models.values(), key=lambda value: value.total_tokens, reverse=True)
    ) or '<tr><td colspan="6">没有可解析的 Codex Token 记录</td></tr>'
    five_hour = quota_window(snapshot, 300)
    weekly = quota_window(snapshot, 10080)
    def quota_card(label: str, window: RateLimitWindow | None) -> str:
        if not window:
            return f'<div class="card"><div class="label">{label}</div><div class="metric">N/A</div><p class="quota-note">本机日志未提供</p></div>'
        remaining = max(0.0, 100.0 - window.used_percent) if window.used_percent is not None else None
        reset_note = local_reset_time(window.resets_at)
        warning = "quota-zero" if remaining == 0 else ""
        return f'<div class="card {warning}"><div class="label">{label}</div><div class="metric">{remaining:.0f}%</div><p class="quota-note">已用 {window.used_percent:.0f}% · 重置 {reset_note}</p></div>'
    def quota_line(label: str, window: RateLimitWindow | None) -> str:
        if not window:
            return f"{label}：N/A（本机日志未提供）"
        remaining = max(0.0, 100.0 - window.used_percent) if window.used_percent is not None else None
        reset = local_reset_time(window.resets_at)
        if remaining == 0:
            return f"{label}：剩余 0% · 已用 {window.used_percent:.0f}% · 重置 {reset}"
        return f"{label}：剩余 {remaining:.0f}% · 已用 {window.used_percent:.0f}% · 重置 {reset}"
    quota = quota_line("五小时", five_hour) + "<br>" + quota_line("周", weekly)
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Codex 用量报表</title><style>
:root{{color-scheme:dark;--bg:#101217;--card:#1a1f28;--line:#343b49;--blue:#76a9ff;--green:#55d6a5;--text:#f4f6fb;--muted:#9ba5b6}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1120px;margin:auto;padding:38px 22px 72px}}h1{{margin:0 0 8px;font-size:30px}}h2{{margin:0 0 12px;font-size:18px}}p{{color:var(--muted);line-height:1.6}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin:22px 0}}.card,section{{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:19px}}section{{margin-top:16px}}.label{{font-size:13px;color:var(--muted)}}.metric{{font-size:27px;font-weight:700;margin-top:7px}}.quota-note{{font-size:12px;margin:8px 0 0}}.quota-zero{{border-color:#d96270}}.chart{{height:250px;overflow:auto;position:relative}}svg{{min-width:760px;width:100%;height:230px;display:block}}.axis{{stroke:#394150;stroke-width:1}}.line-token{{fill:none;stroke:var(--blue);stroke-width:3}}.line-ratio{{fill:none;stroke:var(--green);stroke-width:3}}.tick{{fill:var(--muted);font-size:11px}}.legend{{display:flex;gap:18px;color:var(--muted);font-size:13px}}.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}}.tooltip{{position:fixed;z-index:5;display:none;pointer-events:none;background:#080b10;border:1px solid #566178;border-radius:9px;padding:9px 11px;font-size:12px;line-height:1.5;box-shadow:0 8px 24px #0008}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px 8px;border-top:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}}td:first-child,th:first-child{{text-align:left}}th{{color:var(--muted);font-size:12px}}.plans{{display:grid;grid-template-columns:1fr 150px auto;gap:9px;align-items:center}}input,button{{font:inherit;border-radius:9px;padding:9px 10px;border:1px solid var(--line)}}input{{background:#11151c;color:var(--text)}}button{{background:var(--blue);color:#091322;border:0;font-weight:700;cursor:pointer}}button.ghost{{background:#303846;color:var(--text)}}.plan-row{{display:grid;grid-template-columns:1fr 130px auto;gap:9px;margin-top:9px}}.note{{font-size:12px}}@media(max-width:760px){{main{{padding:22px 14px}}.grid{{grid-template-columns:repeat(2,1fr)}}.plans,.plan-row{{grid-template-columns:1fr 110px auto}}}}
</style></head><body><main><h1>Codex 用量报表</h1><p>独立报表 · 滚动最近 {days} 天 · 生成于 {today.isoformat()} · 本页不包含 Claude、Gemini 或 Grok 数据。</p><div class="grid"><div class="card"><div class="label">总 Token</div><div class="metric">{number(totals.total_tokens)}</div></div><div class="card"><div class="label">输入 Token</div><div class="metric">{number(totals.input_tokens)}</div></div><div class="card"><div class="label">输出 Token</div><div class="metric">{number(totals.output_tokens)}</div></div><div class="card"><div class="label">本机额度快照</div><div class="metric" style="font-size:19px">{quota}</div></div></div><section><h2>订阅计划</h2><p>填写每次订阅价格生效的日期和月金额。一个计划从生效日开始，到下一条计划生效日前一天结束；该周期金额按周期天数平均分摊。浏览器会将你的输入保存在此文件的本机页面存储中，重新生成报表后仍会保留。</p><div class="plans"><input id="start" type="date" aria-label="订阅生效日期"><input id="amount" type="number" min="0" step="0.01" placeholder="USD / 月" aria-label="月订阅金额"><button id="add">添加计划</button></div><div id="plans"></div><p class="note">页面中的计划只用于当前浏览器本机计算。以后插件的“更新统计”按钮会把同一计划写入本地配置文件。</p></section><section><h2>每日 Token 曲线</h2><div class="legend"><span><i class="dot" style="background:var(--blue)"></i>每日总 Token</span></div><div class="chart"><svg id="token-chart" viewBox="0 0 900 230" role="img" aria-label="每日 Token 折线图"></svg></div></section><section><h2>每日 API 等价价值 / 订阅日成本倍数曲线</h2><div class="grid" style="margin:0 0 15px"><div class="card"><div class="label">过去 {days} 天 API 等价价值</div><div class="metric" id="api-total">—</div></div><div class="card"><div class="label">过去 {days} 天订阅成本</div><div class="metric" id="subscription-total">—</div></div><div class="card"><div class="label">过去 {days} 天总倍数</div><div class="metric" id="overall-ratio">—</div></div></div><div class="legend"><span><i class="dot" style="background:var(--green)"></i>当天 API 等价价值 ÷ 当天订阅日成本</span></div><div class="chart"><svg id="ratio-chart" viewBox="0 0 900 230" role="img" aria-label="每日订阅倍数折线图"></svg></div><p class="note">只按本地 Codex 日志里模型名与价格表精确匹配的文本 Token 计算；工具调用、区域价格、长上下文加价不计入。</p></section><section><h2>模型汇总</h2><table><thead><tr><th>模型</th><th>输入</th><th>输出</th><th>缓存输入</th><th>总 Token</th><th>API 等价价值</th></tr></thead><tbody>{model_rows}</tbody></table></section><section><h2>数据来源与扩展</h2><p>此次读取了 {source_files.get("Codex", 0)} 个 Codex 本机会话文件。Claude、Gemini、Grok 将各自生成独立页面，不与 Codex 合并；新增平台使用同一套“本机采集器、订阅计划、Token 曲线、倍数曲线、模型汇总”接口。</p></section></main><script>const DATA={data_json};const KEY='ai-subscription-usage:codex:plans:v1';const $=id=>document.getElementById(id);let plans=[];try{{plans=JSON.parse(localStorage.getItem(KEY)||'null')||DATA.plans}}catch{{plans=DATA.plans}}function money(v){{return '$'+v.toFixed(2)}}function esc(v){{return String(v).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}function save(){{localStorage.setItem(KEY,JSON.stringify(plans));render()}}function allocation(date){{let active=plans.filter(p=>p.start_date<=date).sort((a,b)=>a.start_date.localeCompare(b.start_date)).pop();if(!active)return 0;let next=plans.filter(p=>p.start_date>active.start_date).sort((a,b)=>a.start_date.localeCompare(b.start_date))[0];let start=new Date(active.start_date+'T00:00:00');let end=next?new Date(next.start_date+'T00:00:00'):new Date(start);if(!next)end.setMonth(end.getMonth()+1);let span=Math.max(1,Math.round((end-start)/86400000));return active.monthly_usd/span}}function chart(id,values,color,unit){{let svg=$(id),w=900,h=230,l=45,r=15,t=18,b=31,max=Math.max(1,...values),innerW=w-l-r,innerH=h-t-b;let pts=values.map((v,i)=>{{let x=l+(values.length===1?0:i*innerW/(values.length-1));let y=t+innerH-(v/max*innerH);return [x,y]}});let line=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');let labels=DATA.days.map((d,i)=>i===0||i===DATA.days.length-1||i%7===0?`<text x="${{pts[i][0]}}" y="218" text-anchor="middle" class="tick">${{d.date.slice(5)}}</text>`:'').join('');svg.innerHTML=`<line x1="${{l}}" y1="${{t+innerH}}" x2="${{w-r}}" y2="${{t+innerH}}" class="axis"/><text x="3" y="${{t+8}}" class="tick">${{max.toLocaleString(undefined,{{maximumFractionDigits:unit==='×'?2:0}})}}${{unit}}</text><path d="${{line}}" class="${{id==='token-chart'?'line-token':'line-ratio'}}"/>${{pts.map(p=>`<circle cx="${{p[0]}}" cy="${{p[1]}}" r="3.5" fill="${{color}}"/>`).join('')}}${{labels}}`}}function render(){{plans.sort((a,b)=>a.start_date.localeCompare(b.start_date));$('plans').innerHTML=plans.map((p,i)=>`<div class="plan-row"><input type="date" value="${{esc(p.start_date)}}" onchange="plans[${{i}}].start_date=this.value;save()"><input type="number" min="0" step="0.01" value="${{p.monthly_usd}}" onchange="plans[${{i}}].monthly_usd=Number(this.value);save()"><button class="ghost" onclick="plans.splice(${{i}},1);save()">删除</button></div>`).join('')||'<p>尚未设置订阅计划。</p>';let costs=DATA.days.map(d=>d.api_cost),subs=DATA.days.map(d=>allocation(d.date)),ratios=costs.map((c,i)=>subs[i]?c/subs[i]:0),api=costs.reduce((a,b)=>a+b,0),sub=subs.reduce((a,b)=>a+b,0);$('api-total').textContent=money(api);$('subscription-total').textContent=money(sub);$('overall-ratio').textContent=sub?(api/sub).toFixed(2)+'×':'未设置';chart('token-chart',DATA.days.map(d=>d.tokens),'#76a9ff','');chart('ratio-chart',ratios,'#55d6a5','×')}}$('add').onclick=()=>{{let start=$('start').value,amount=Number($('amount').value);if(!start||!(amount>0))return;plans.push({{start_date:start,monthly_usd:amount}});$('start').value='';$('amount').value='';save()}};render();</script></body></html>"""


def render_codex_dashboard(usages: list[Usage], snapshot: RateLimitSnapshot | None, days: int, pricing: dict[str, Any]) -> str:
    """Clean Codex dashboard; other providers get separate data pages later."""
    today = report_today()
    dates = [(today - dt.timedelta(days=index)).isoformat() for index in range(days - 1, -1, -1)]
    daily_tokens: dict[str, int] = defaultdict(int)
    daily_cost: dict[str, float] = defaultdict(float)
    models: dict[str, Usage] = {}
    for item in usages:
        daily_tokens[item.date] += item.total_tokens
        cost = api_equivalent_cost(item, pricing)
        if cost is not None:
            daily_cost[item.date] += cost
        aggregate = models.setdefault(item.model, Usage("Codex", item.model, "", cache_is_subset_of_input=True))
        aggregate.input_tokens += item.input_tokens
        aggregate.output_tokens += item.output_tokens
        aggregate.cached_input_tokens += item.cached_input_tokens
        aggregate.cache_write_input_tokens += item.cache_write_input_tokens
    total_input = sum(item.input_tokens for item in usages)
    total_output = sum(item.output_tokens for item in usages)
    total_tokens = sum(item.total_tokens for item in usages)
    default_plans = subscription_plan_data(pricing)
    payload = {"days": [{"date": day, "tokens": daily_tokens[day], "cost": round(daily_cost[day], 8)} for day in dates], "plans": default_plans}
    def quota_data(minutes: int) -> dict[str, Any]:
        item = quota_window(snapshot, minutes)
        if not item:
            return {"available": False}
        return {"available": True, "used": item.used_percent, "remaining": max(0, 100 - (item.used_percent or 0)), "reset": local_reset_time(item.resets_at)}
    payload["quota"] = {"five_hour": quota_data(300), "weekly": quota_data(10080)}
    model_rows = "".join(f"<tr><td>{html.escape(item.model)}</td><td>{number(item.input_tokens)}</td><td>{number(item.output_tokens)}</td><td>{number(item.cached_input_tokens)}</td><td>{number(item.total_tokens)}</td><td>{money(api_equivalent_cost(item, pricing))}</td></tr>" for item in sorted(models.values(), key=lambda value: value.total_tokens, reverse=True)) or '<tr><td colspan="6">没有可解析记录</td></tr>'
    summary_html = (
        '<section class="section"><div class="plans">'
        f'<div class="plan"><div class="muted">总 Token</div><div class="amount">{number(total_tokens)}</div></div>'
        f'<div class="plan"><div class="muted">输入 Token</div><div class="amount">{number(total_input)}</div></div>'
        f'<div class="plan"><div class="muted">输出 Token</div><div class="amount">{number(total_output)}</div></div>'
        f'<div class="plan"><div class="muted">统计范围</div><div class="amount">{days} 天</div></div>'
        '</div></section>'
    )
    rates = pricing.get("models") if isinstance(pricing.get("models"), dict) else {}
    price_rows = "".join(
        f"<tr><td>{html.escape(model)}</td><td>${float(rate.get('input_per_million', 0)):.2f}</td>"
        f"<td>${float(rate.get('cached_input_per_million', 0)):.2f}</td><td>${float(rate.get('output_per_million', 0)):.2f}</td></tr>"
        for model, rate in sorted(rates.items()) if isinstance(rate, dict)
    ) or "<tr><td colspan=\"4\">尚未设置公开模型价格</td></tr>"
    info_html = (
        '<section class="section" id="calculation-guide"><h2>计算说明与模型价格</h2>'
        '<p>月订阅固定按 30 天分摊；年订阅固定按 360 天分摊。每日 API 等价价值按模型的输入、缓存输入和输出 Token 分别乘以每百万 Token 单价计算。30 天总倍数等于 30 天 API 等价价值除以 30 天订阅成本。未公开模型暂按 $0 计价，并在模型汇总中标注。</p>'
        '<table><thead><tr><th>模型</th><th>输入 / 百万 Token</th><th>缓存输入 / 百万 Token</th><th>输出 / 百万 Token</th></tr></thead><tbody>'
        + price_rows + '</tbody></table><p class="muted">价格表来自本机 `config/pricing.json`。扫描到价格表没有的新模型时，应补充官方单价和生效日期后再计价。</p></section>'
    )
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    data += ";document.addEventListener('DOMContentLoaded',()=>{document.querySelector('.head').insertAdjacentHTML('afterend'," + json.dumps(summary_html, ensure_ascii=False) + ");document.querySelector('main').insertAdjacentHTML('beforeend'," + json.dumps(info_html, ensure_ascii=False) + ")})"
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex 用量</title><style>
:root{{--bg:#f6f7fb;--card:#fff;--ink:#162033;--sub:#68748a;--line:#e5e9f1;--blue:#396af6;--green:#0d9f74;--red:#d84252}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1200px;margin:auto;padding:38px 24px 70px}}h1{{font-size:30px;margin:0}}h2{{font-size:18px;margin:0 0 16px}}p{{color:var(--sub);line-height:1.6}}.head{{display:flex;justify-content:space-between;gap:20px;align-items:end}}.tag{{color:var(--sub)}}.section{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;margin-top:18px}}.plans{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.plan{{border:1px solid var(--line);border-radius:12px;padding:14px;min-height:118px}}.plan h3{{margin:0 0 10px;font-size:15px}}.muted{{color:var(--sub)}}.amount{{font-size:23px;font-weight:750;margin:5px 0}}.form{{display:grid;grid-template-columns:150px 130px 1fr 130px auto;gap:9px;margin-top:16px}}input,select,button{{font:inherit;border:1px solid var(--line);border-radius:9px;padding:9px;background:white;color:var(--ink)}}button{{background:var(--ink);color:white;border-color:var(--ink);font-weight:650;cursor:pointer}}.quotas{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.quota{{border-radius:12px;padding:17px;background:#f9fafc;border:1px solid var(--line)}}.quota.zero{{border-color:#f0b7bd;background:#fff7f7}}.quota strong{{display:block;font-size:29px;margin:7px 0}}.charts{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.chartbox{{border:1px solid var(--line);border-radius:12px;padding:14px;overflow:auto}}svg{{min-width:500px;width:100%;height:255px;display:block}}.axis{{stroke:#d9e0eb}}.tick{{fill:#7c8799;font-size:11px}}.tip{{position:fixed;display:none;pointer-events:none;background:#152035;color:#fff;border-radius:9px;padding:9px 10px;font-size:12px;line-height:1.55;box-shadow:0 8px 24px #24304b44}}table{{width:100%;border-collapse:collapse}}td,th{{padding:11px 8px;border-top:1px solid var(--line);text-align:right}}td:first-child,th:first-child{{text-align:left}}th{{color:var(--sub);font-size:12px}}@media(max-width:850px){{.plans,.charts{{grid-template-columns:1fr 1fr}}.form{{grid-template-columns:1fr 1fr}}}}@media(max-width:560px){{main{{padding:24px 14px}}.plans,.charts,.quotas{{grid-template-columns:1fr}}}}
</style></head><body><main><div class="head"><div><h1>Codex 用量</h1><p>最近 {days} 天 · 按电脑当前时区分日 · 数据来自本机 Codex 日志</p></div><div class="tag">更新后刷新此页</div></div><section class="section"><h2>订阅计划</h2><p>每个平台只显示当前有效计划。修改计划会保存旧计划，用于历史曲线计算。</p><div id="plans" class="plans"></div><div class="form"><select id="provider"><option>ChatGPT</option><option>Claude</option><option>Gemini</option><option>Grok</option></select><select id="cycle"><option value="month">按月</option><option value="year">按年</option></select><input id="start" type="date"><input id="amount" type="number" min="0" step="0.01" placeholder="金额 USD"><button id="save">保存计划</button></div></section><section class="section"><h2>Codex 额度</h2><div class="quotas" id="quotas"></div></section><section class="section"><h2>最近 {days} 天</h2><div class="charts"><div class="chartbox"><h3>每日 Token</h3><svg id="tokens" viewBox="0 0 560 255"></svg></div><div class="chartbox"><h3>每日倍数</h3><svg id="ratio" viewBox="0 0 560 255"></svg></div></div></section><section class="section"><h2>最近 {days} 天汇总</h2><div class="plans"><div class="plan"><div class="muted">API 等价价值</div><div class="amount" id="api">—</div></div><div class="plan"><div class="muted">订阅成本</div><div class="amount" id="sub">—</div></div><div class="plan"><div class="muted">总倍数</div><div class="amount" id="multiple">—</div></div><div class="plan"><div class="muted">未公开模型 Token</div><div class="amount" id="unpriced">不计入</div></div></div></section><section class="section"><h2>最近 {days} 天模型汇总</h2><table><thead><tr><th>模型</th><th>输入</th><th>输出</th><th>缓存输入</th><th>总 Token</th><th>API 等价价值</th></tr></thead><tbody>{model_rows}</tbody></table></section></main><div id="tip" class="tip"></div><script>const DATA={data};const KEY='ai-subscription-plans:v2';const P=['ChatGPT','Claude','Gemini','Grok'];let plans;try{{plans=JSON.parse(localStorage.getItem(KEY))||DATA.plans}}catch{{plans=DATA.plans}}const $=x=>document.getElementById(x),cash=x=>'$'+x.toFixed(2);function active(provider,date){{return plans.filter(p=>p.provider===provider&&p.start_date<=date).sort((a,b)=>a.start_date.localeCompare(b.start_date)).pop()}}function daysFor(p,date){{let s=new Date(p.start_date+'T12:00:00'),d=new Date(date+'T12:00:00');while(s.getTime()+86400000<d.getTime()){{s.setMonth(s.getMonth()+(p.cycle==='year'?12:1))}}let e=new Date(s);e.setMonth(e.getMonth()+(p.cycle==='year'?12:1));return Math.round((e-s)/86400000)}}function perDay(date){{let p=active('ChatGPT',date);return p?p.amount/daysFor(p,date):0}}function renderPlans(){{$('plans').innerHTML=P.map(provider=>{{let p=active(provider,new Date().toISOString().slice(0,10));return `<div class="plan"><h3>${{provider}}</h3>${{p?`<div class="amount">${{cash(p.amount)}} / ${{p.cycle==='year'?'年':'月'}}</div><div class="muted">${{p.start_date}} 起</div><div class="muted">当前周期至 ${{(() => {{let s=new Date(p.start_date+'T12:00:00');s.setMonth(s.getMonth()+(p.cycle==='year'?12:1));s.setDate(s.getDate()-1);return s.toISOString().slice(0,10)}})()}}</div>`:'<div class="muted">未设置</div>'}}</div>`}}).join('')}}function quota(name,q){{if(!q.available)return `<div class="quota"><span class="muted">${{name}}</span><strong>N/A</strong><span class="muted">本机日志未提供</span></div>`;let zero=q.remaining===0;return `<div class="quota ${{zero?'zero':''}}"><span class="muted">${{name}}</span><strong>剩余 ${{q.remaining.toFixed(0)}}%</strong><span class="muted">已用 ${{q.used.toFixed(0)}}% · 重置 ${{q.reset}}</span></div>`}}function chart(id,vals,color,format){{let s=$(id),w=560,h=255,l=42,r=10,t=18,b=32,m=Math.max(1,...vals),iw=w-l-r,ih=h-t-b,pts=vals.map((v,i)=>[l+i*iw/(vals.length-1),t+ih-v/m*ih]),path=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' '),labs=DATA.days.map((d,i)=>i%7===0||i===DATA.days.length-1?`<text x="${{pts[i][0]}}" y="244" text-anchor="middle" class="tick">${{d.date.slice(5)}}</text>`:'').join('');s.innerHTML=`<line class="axis" x1="${{l}}" y1="${{t+ih}}" x2="${{w-r}}" y2="${{t+ih}}"/><text x="3" y="${{t+8}}" class="tick">${{format(m)}}</text><path d="${{path}}" fill="none" stroke="${{color}}" stroke-width="3"/>${{pts.map(p=>`<circle cx="${{p[0]}}" cy="${{p[1]}}" r="3.5" fill="${{color}}"/>`).join('')}}${{labs}}`;s.onmousemove=e=>{{let box=s.getBoundingClientRect(),x=(e.clientX-box.left)/box.width*w,i=Math.max(0,Math.min(vals.length-1,Math.round((x-l)/iw))),d=DATA.days[i],extra=id==='tokens'?`Token：${{d.tokens.toLocaleString()}}`:`倍数：${{format(vals[i])}}<br>API：${{cash(d.cost)}}<br>订阅日成本：${{cash(perDay(d.date))}}`;$('tip').innerHTML=`${{d.date}}<br>${{extra}}`;$('tip').style.display='block';$('tip').style.left=(e.clientX+14)+'px';$('tip').style.top=(e.clientY+14)+'px'}};s.onmouseleave=()=>$('tip').style.display='none'}}function render(){{renderPlans();$('quotas').innerHTML=quota('五小时额度',DATA.quota.five_hour)+quota('周额度',DATA.quota.weekly);let sub=DATA.days.map(d=>perDay(d.date)),ratio=DATA.days.map((d,i)=>sub[i]?d.cost/sub[i]:0),api=DATA.days.reduce((n,d)=>n+d.cost,0),subscription=sub.reduce((a,b)=>a+b,0);$('api').textContent=cash(api);$('sub').textContent=cash(subscription);$('multiple').textContent=subscription?(api/subscription).toFixed(2)+'×':'未设置';chart('tokens',DATA.days.map(d=>d.tokens),'#396af6',v=>Math.round(v).toLocaleString());chart('ratio',ratio,'#0d9f74',v=>v.toFixed(2)+'×')}}$('save').onclick=()=>{{let provider=$('provider').value,cycle=$('cycle').value,start=$('start').value,amount=Number($('amount').value);if(!start||!(amount>0))return;plans.push({{provider,start_date:start,cycle,amount}});localStorage.setItem(KEY,JSON.stringify(plans));render()}};render();</script></body></html>'''


PROVIDER_META = {
    "Codex": {"label": "ChatGPT", "plan": "ChatGPT", "color": "#61a8ff", "quota": True},
    "Claude Code": {"label": "Claude", "plan": "Claude", "color": "#ff9f43", "quota": True},
    "Gemini CLI": {"label": "Gemini / Antigravity", "plan": "Gemini", "color": "#23d8aa", "quota": False},
    "Grok Build": {"label": "Grok", "plan": "Grok", "color": "#b180ff", "quota": False},
}


def render_dashboard(
    usages: list[Usage],
    snapshot: RateLimitSnapshot | None,
    days: int,
    source_files: dict[str, int],
    pricing: dict[str, Any],
    app_version: str = "development",
) -> str:
    """Render the overview and provider details from one provider-neutral payload."""
    today = report_today()
    dates = [(today - dt.timedelta(days=index)).isoformat() for index in range(days - 1, -1, -1)]
    by_provider: dict[str, list[Usage]] = {provider: [] for provider in PROVIDER_META}
    claude_quota_snapshot = load_claude_quota_snapshot()
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
        quota = {"five_hour": {"available": False}, "weekly": {"available": False}}
        if provider == "Codex" and meta["quota"]:
            for key, minutes in (("five_hour", 300), ("weekly", 10080)):
                window = quota_window(snapshot, minutes)
                if window:
                    used = window.used_percent if window.used_percent is not None else 0
                    quota[key] = {"available": True, "used": used, "remaining": max(0, 100 - used), "reset": local_reset_time(window.resets_at)}
        elif provider == "Claude Code" and meta["quota"] and isinstance(claude_quota_snapshot, dict):
            for key, source_key in (("five_hour", "five_hour"), ("weekly", "seven_day")):
                window = claude_quota_snapshot.get(source_key)
                if not isinstance(window, dict) or not isinstance(window.get("used_percentage"), (int, float)):
                    continue
                used = float(window["used_percentage"])
                reset = window.get("resets_at")
                quota[key] = {"available": True, "used": used, "remaining": max(0, 100 - used), "reset": local_reset_time(str(reset)) if reset is not None else "—"}
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
            "quota": quota,
            "quota_note": (
                "为避免账号风险，本工具不读取 OAuth/Auth Token；Claude Code 未通过官方 statusLine 提供额度"
                if provider == "Claude Code" else
                "Antigravity 本机公开记录未提供额度；本工具不读取 Google OAuth"
                if provider == "Gemini CLI" else
                "Grok 网页应用未提供本机额度记录"
                if provider == "Grok Build" else
                "本机记录未提供"
            ),
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
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>订阅 AI 用量报表</title><style>
:root{{--bg:#080d18;--card:#101a2b;--card2:#0c1728;--ink:#ecf5ff;--sub:#91a3bf;--line:#263854;--accent:#61a8ff;--danger:#ff6f86;color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1540px;margin:auto;padding:36px 24px 70px}}h1{{font-size:30px;margin:0}}h2{{font-size:19px;margin:0 0 8px}}h3{{font-size:15px;margin:0 0 10px}}p{{color:var(--sub);line-height:1.6;margin:6px 0 0}}.head{{display:flex;justify-content:space-between;gap:20px;align-items:end}}.head-actions{{display:flex;align-items:center;gap:10px}}.head-actions button{{height:36px}}.section{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;margin-top:18px;overflow-x:auto}}.summary{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;min-width:1100px}}.plan-grid,.quota-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px}}.detail-summary{{display:grid;grid-template-columns:repeat(5,minmax(180px,1fr));gap:12px;min-width:980px}}.metric-card,.plan-card,.quota-card{{border:1px solid var(--line);border-radius:12px;padding:14px;background:var(--card2)}}.metric-card{{display:flex;flex-direction:column;justify-content:space-between;min-height:108px}}.metric{{font-size:25px;font-weight:750;margin:0;padding-top:12px;white-space:nowrap}}.muted{{color:var(--sub)}}.plan-card{{min-height:126px}}.plan-card .price{{font-size:21px;font-weight:750;margin:10px 0}}.editor{{display:grid;grid-template-columns:minmax(210px,1.15fr) minmax(170px,.9fr) minmax(220px,1fr) minmax(280px,1.45fr) 132px;gap:16px;align-items:end;margin-top:24px}}label{{display:grid;gap:9px;color:var(--sub);font-size:13px}}input,select,button{{height:48px;border-radius:10px;border:1px solid var(--line);font:inherit}}input,select{{background:#0a1322;color:var(--ink);padding:0 14px;min-width:0}}input[type=number]{{appearance:textfield;-moz-appearance:textfield}}input[type=number]::-webkit-inner-spin-button,input[type=number]::-webkit-outer-spin-button{{-webkit-appearance:none;margin:0}}button{{background:var(--accent);color:#07101d;border-color:var(--accent);font-weight:750;padding:0 14px;cursor:pointer}}button:hover{{filter:brightness(1.12)}}.chartbox{{border:1px solid var(--line);border-radius:13px;padding:16px;margin-top:16px;background:var(--card2);overflow:hidden}}.legend{{display:flex;gap:17px;flex-wrap:wrap;margin:10px 0 5px;color:var(--sub)}}.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}}svg{{width:100%;height:300px;display:block}}.axis{{stroke:#365173;stroke-width:1}}.gridline{{stroke:#223651;stroke-width:1}}.tick{{fill:#91a3bf;font-size:11px}}.hoverline{{stroke:#d8f2ff;stroke-width:1;stroke-dasharray:4 4}}.tip{{position:fixed;display:none;pointer-events:none;z-index:10;background:#050b14;color:#fff;border:1px solid #405778;border-radius:9px;padding:10px 12px;font-size:12px;line-height:1.6;box-shadow:0 10px 28px #0009}}.quota-card{{min-height:220px}}.quota-card h3{{min-height:24px}}.quota-pair{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:10px}}.quota-item{{border-top:1px solid var(--line);padding-top:16px;display:grid;grid-template-rows:34px 48px 54px;align-items:start;min-width:0}}.quota-item strong{{display:flex;align-items:flex-start;font-size:19px;line-height:1.15;margin:0;white-space:nowrap}}.quota-item .quota-note{{line-height:1.35}}.tabs{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:20px 0 22px}}.tab{{background:#15243a;color:var(--sub);border-color:var(--line);width:100%;font-size:15px}}.tab.active{{background:var(--accent);color:#07101d}}.detail{{display:none}}.detail.active{{display:block}}table{{width:100%;border-collapse:collapse;margin-top:18px}}th,td{{padding:11px 8px;border-top:1px solid var(--line);text-align:center}}th{{font-size:12px;color:var(--sub);text-align:center}}.empty{{padding:26px;text-align:center;color:var(--sub)}}@media(max-width:900px){{.plan-grid,.quota-grid{{grid-template-columns:1fr 1fr}}.editor{{grid-template-columns:1fr 1fr}}}}@media(max-width:560px){{main{{padding:24px 14px}}.plan-grid,.quota-grid,.editor{{grid-template-columns:1fr}}svg{{height:260px}}}}
.help-link{{display:inline-flex;align-items:center;height:36px;border:1px solid var(--line);border-radius:9px;padding:0 12px;color:var(--ink);background:#15243a;text-decoration:none}}
</style></head><body><main><div class="head"><div><h1>订阅 AI 用量报表</h1><p>最近 {days} 天 · 按电脑当前时区分日 · 数据来自本机日志 · Ver {html.escape(app_version)}</p></div><div class="head-actions"><span class="muted" id="refresh-status">生成于本机</span><a class="help-link" href="http://127.0.0.1:17653/help">配置及使用说明</a><button id="refresh-local">更新本机数据</button></div></div>
<section class="section"><div class="summary"><div class="metric-card"><div class="muted">总 Token</div><div class="metric">{number(total_tokens)}</div></div><div class="metric-card"><div class="muted">输入 Token</div><div class="metric">{number(total_input)}</div></div><div class="metric-card"><div class="muted">输出 Token</div><div class="metric">{number(total_output)}</div></div><div class="metric-card"><div class="muted">API 等价价值</div><div class="metric" id="summary-api">—</div></div><div class="metric-card"><div class="muted">有效订阅成本</div><div class="metric" id="summary-sub">—</div></div><div class="metric-card"><div class="muted">价值倍数</div><div class="metric" id="summary-ratio">—</div></div></div></section>
<section class="section"><h2>订阅计划</h2><p>每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。</p><div id="plan-grid" class="plan-grid"></div><div class="editor"><label>平台<select id="provider"></select></label><label>周期<select id="cycle"><option value="month">按月</option><option value="year">按年</option></select></label><label>生效日期<input id="start" type="date"></label><label>订阅金额（USD）<input id="amount" type="number" min="0" step="0.01" placeholder="输入订阅金额"></label><button id="save">保存计划</button></div></section>
<section class="section"><h2>最近 {days} 天报表</h2><div class="chartbox"><h3>每日 Token</h3><p>各平台当天输入、输出和缓存口径合并后的 Token。</p><div class="legend" id="token-legend"></div><svg id="tokens" viewBox="0 0 1100 300" role="img" aria-label="各平台每日 Token 折线图"></svg></div><div class="chartbox"><h3>每日订阅价值倍数</h3><p>当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。</p><div class="legend" id="ratio-legend"></div><svg id="ratio" viewBox="0 0 1100 300" role="img" aria-label="各平台每日订阅价值倍数折线图"></svg></div></section>
<section class="section"><h2>平台额度</h2><p>只展示本机日志提供的真实额度快照；没有额度记录的平台显示“本机记录未提供”。</p><div id="quota-grid" class="quota-grid"></div></section>
<section class="section"><h2>平台详情</h2><div id="tabs" class="tabs"></div><div id="details"></div></section></main><div id="tip" class="tip"></div>
<script>const DATA={data};const $=id=>document.getElementById(id);let plans=Array.isArray(DATA.plans)?DATA.plans:[];document.addEventListener('DOMContentLoaded',()=>{{document.querySelectorAll('.metric-card').forEach(x=>{{x.style.alignItems='center';x.style.textAlign='center'}});document.querySelectorAll('table th,table td').forEach(x=>x.style.textAlign='center')}});
const cash=v=>'$'+Number(v).toFixed(2),num=v=>Number(v).toLocaleString(),esc=v=>String(v).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function activePlan(provider,date){{return plans.filter(p=>p.provider===provider&&p.start_date<=date).sort((a,b)=>a.start_date.localeCompare(b.start_date)).pop()||null}}function dailyCost(provider,date){{let p=activePlan(provider,date);return p?p.amount/(p.cycle==='year'?360:30):0}}
function renderSummary(){{let api=DATA.providers.reduce((n,p)=>n+p.totals.cost,0),sub=DATA.providers.reduce((n,p)=>n+p.daily.reduce((s,d)=>s+dailyCost(p.plan,d.date),0),0);$('summary-api').textContent=cash(api);$('summary-sub').textContent=cash(sub);$('summary-ratio').textContent=sub?(api/sub).toFixed(2)+'×':'未计算'}}
function renderPlans(){{$('provider').innerHTML=DATA.providers.map(p=>`<option value="${{esc(p.plan)}}">${{esc(p.label)}}</option>`).join('');$('plan-grid').innerHTML=DATA.providers.map(p=>{{let current=activePlan(p.plan,DATA.today);return `<div class="plan-card"><h3>${{esc(p.label)}}</h3>${{current?`<div class="price">${{cash(current.amount)}} / ${{current.cycle==='year'?'年':'月'}}</div><div class="muted">${{current.start_date}} 生效</div><div class="muted">历史计划 ${{plans.filter(x=>x.provider===p.plan).length}} 条</div>`:'<div class="price">未设置</div><div class="muted">不计算订阅成本与倍数</div>'}}</div>`}}).join('')}}
function focusProvider(providerId){{document.querySelectorAll('path.series').forEach(path=>{{let active=path.dataset.provider===providerId;path.style.opacity=active?'1':'.16';path.setAttribute('stroke-width',active?'5':'2')}})}}function clearProviderFocus(){{document.querySelectorAll('path.series').forEach(path=>{{path.style.opacity='1';path.setAttribute('stroke-width','3')}})}}function legend(id){{$(id).innerHTML=DATA.providers.map(p=>`<span class="legend-item" tabindex="0" data-provider="${{esc(p.id)}}" style="cursor:pointer;padding:4px 7px;border-radius:7px"><i class="dot" style="background:${{p.color}}"></i>${{esc(p.label)}}${{p.has_data?'':'（无数据）'}}</span>`).join('');$(id).querySelectorAll('.legend-item').forEach(item=>{{item.onmouseenter=item.onfocus=()=>focusProvider(item.dataset.provider);item.onmouseleave=item.onblur=clearProviderFocus}})}}
function series(type){{return DATA.providers.map(p=>{{let hasPriced=p.totals.tokens>p.totals.unpriced;return {{provider:p,values:p.daily.map(d=>{{if(!p.has_data)return null;if(type==='tokens')return d.tokens;let cost=dailyCost(p.plan,d.date);return hasPriced&&cost?d.cost/cost:null}})}}}})}}
function chart(id,type){{let svg=$(id),w=1100,h=300,l=64,r=20,t=18,b=38,iw=w-l-r,ih=h-t-b,all=series(type),finite=all.flatMap(s=>s.values.filter(v=>v!==null)),max=Math.max(1,...finite),x=i=>l+(DATA.days.length===1?0:i*iw/(DATA.days.length-1)),y=v=>t+ih-v/max*ih;let grid=[0,.25,.5,.75,1].map(k=>`<line class="gridline" x1="${{l}}" y1="${{y(max*k)}}" x2="${{w-r}}" y2="${{y(max*k)}}"/><text class="tick" x="4" y="${{y(max*k)+4}}">${{type==='tokens'?Math.round(max*k).toLocaleString():(max*k).toFixed(1)+'×'}}</text>`).join('');let paths=all.map(s=>{{let parts=[],open=false,points=[];s.values.forEach((v,i)=>{{if(v===null){{open=false;return}}parts.push(`${{open?'L':'M'}}${{x(i).toFixed(1)}} ${{y(v).toFixed(1)}}`);points.push(`<circle cx="${{x(i)}}" cy="${{y(v)}}" r="${{finite.length===1?5:2.6}}" fill="${{s.provider.color}}"/>`);open=true}});return parts.length?`<g data-provider="${{esc(s.provider.id)}}"><path class="series" data-provider="${{esc(s.provider.id)}}" d="${{parts.join(' ')}}" fill="none" stroke="${{s.provider.color}}" stroke-width="3"/>${{points.join('')}}</g>`:''}}).join('');let labels=DATA.days.map((d,i)=>i%3===0?`<text class="tick" x="${{x(i)}}" y="292" text-anchor="middle">${{d.slice(5)}}</text>`:'').join('');svg.innerHTML=grid+paths+`<line class="hoverline" visibility="hidden" x1="0" y1="${{t}}" x2="0" y2="${{t+ih}}"/><rect class="hit-area" x="${{l}}" y="${{t}}" width="${{iw}}" height="${{ih}}" fill="transparent" style="pointer-events:all"/>`+labels;let hit=svg.querySelector('.hit-area');hit.onmousemove=e=>{{let bounds=hit.getBoundingClientRect(),fraction=(e.clientX-bounds.left)/bounds.width,i=Math.max(0,Math.min(DATA.days.length-1,Math.round(fraction*(DATA.days.length-1)))),date=DATA.days[i],line=svg.querySelector('.hoverline');line.setAttribute('x1',x(i));line.setAttribute('x2',x(i));line.setAttribute('visibility','visible');let rows=DATA.providers.map(p=>{{let d=p.daily[i];if(!p.has_data)return `<span style="color:${{p.color}}">${{esc(p.label)}}</span>：无数据`;if(type==='tokens')return `<span style="color:${{p.color}}">${{esc(p.label)}}</span>：${{num(d.tokens)}} Token`;let sub=dailyCost(p.plan,date),priced=p.totals.tokens>p.totals.unpriced,ratio=priced&&sub?d.cost/sub:null,status=!sub?'无生效计划':!priced?'模型未计价':ratio.toFixed(2)+'×';return `<span style="color:${{p.color}}">${{esc(p.label)}}</span>：${{status}}<br>API ${{cash(d.cost)}} · 日成本 ${{cash(sub)}}`}}).join('<br>');$('tip').innerHTML=`${{date}}<br>${{rows}}`;$('tip').style.display='block';$('tip').style.left=Math.min(e.clientX+14,window.innerWidth-260)+'px';$('tip').style.top=(e.clientY+14)+'px'}};hit.onmouseleave=()=>{{svg.querySelector('.hoverline').setAttribute('visibility','hidden');$('tip').style.display='none'}}}}
function quotaItem(name,q,note){{return `<div class="quota-item"><div class="muted">${{name}}${{q.available?' · 剩余':''}}</div>${{q.available?`<strong>${{q.remaining.toFixed(0)}}%</strong><div class="muted quota-note">重置 ${{esc(q.reset)}}</div>`:`<strong>N/A</strong><div class="muted quota-note">${{esc(note)}}</div>`}}</div>`}}function renderQuotas(){{$('quota-grid').innerHTML=DATA.providers.map(p=>`<div class="quota-card"><h3>${{esc(p.label)}}</h3><div class="quota-pair">${{quotaItem('五小时额度',p.quota.five_hour,p.quota_note)}}${{quotaItem('周额度',p.quota.weekly,p.quota_note)}}</div></div>`).join('')}}
function renderDetails(){{$('tabs').innerHTML=DATA.providers.map((p,i)=>`<button class="tab ${{i===0?'active':''}}" data-id="${{esc(p.id)}}">${{esc(p.label)}}</button>`).join('');$('details').innerHTML=DATA.providers.map((p,i)=>{{let t=p.totals,subscription=p.daily.reduce((sum,d)=>sum+dailyCost(p.plan,d.date),0),hasPriced=t.tokens>t.unpriced,multiple=subscription&&hasPriced?t.cost/subscription:null,rows=p.models.map(m=>`<tr><td>${{esc(m.model)}}${{m.estimated?'（估算）':''}}</td><td>${{num(m.input)}}</td><td>${{num(m.output)}}</td><td>${{num(m.cached)}}</td><td>${{num(m.tokens)}}</td><td>${{m.cost===null?'未公开价格':cash(m.cost)}}</td></tr>`).join('')||'<tr><td colspan="6" class="empty">本机没有可解析记录</td></tr>';return `<div class="detail ${{i===0?'active':''}}" data-id="${{esc(p.id)}}"><div class="detail-summary"><div class="metric-card"><div class="muted">最近 {days} 天总 Token</div><div class="metric">${{num(t.tokens)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天 API 等价价值</div><div class="metric">${{cash(t.cost)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天有效订阅成本</div><div class="metric">${{cash(subscription)}}</div></div><div class="metric-card"><div class="muted">最近 {days} 天同区间价值倍数</div><div class="metric">${{multiple===null?'未计算':multiple.toFixed(2)+'×'}}</div></div><div class="metric-card"><div class="muted">未计价 Token</div><div class="metric">${{num(t.unpriced)}}</div></div></div><table><thead><tr><th>模型</th><th>输入</th><th>输出</th><th>缓存输入</th><th>总 Token</th><th>API 等价价值</th></tr></thead><tbody>${{rows}}</tbody></table></div>`}}).join('');document.querySelectorAll('.tab').forEach(tab=>tab.onclick=()=>{{document.querySelectorAll('.tab,.detail').forEach(x=>x.classList.remove('active'));tab.classList.add('active');document.querySelector(`.detail[data-id="${{CSS.escape(tab.dataset.id)}}"]`).classList.add('active')}})}}
$('save').onclick=async()=>{{let provider=$('provider').value,cycle=$('cycle').value,start=$('start').value,amount=Number($('amount').value);if(!start||!(amount>0))return;let candidate={{provider,start_date:start,cycle,amount}};try{{let response=await fetch('http://127.0.0.1:17653/plans',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(candidate)}});if(!response.ok)throw new Error();let result=await response.json();plans=result.plans;$('start').value='';$('amount').value='';renderPlans();renderSummary();chart('ratio','ratio');renderDetails()}}catch{{alert('本机应用未运行，订阅计划没有保存')}}}};$('refresh-local').onclick=async()=>{{let status=$('refresh-status');status.textContent='正在更新…';try{{let response=await fetch('http://127.0.0.1:17653/refresh',{{method:'POST'}});if(!response.ok)throw new Error();status.textContent='更新完成，正在打开本机报表';setTimeout(()=>location.href='http://127.0.0.1:17653/report',350)}}catch{{status.textContent='本机应用未运行'}}}};let reportVersion=0;async function syncLanguage(){{try{{let response=await fetch('http://127.0.0.1:17653/state?ts='+Date.now(),{{cache:'no-store'}});if(!response.ok)return;let state=await response.json(),current=document.documentElement.lang;if(reportVersion&&state.report_version!==reportVersion&&state.language!==current)location.replace('http://127.0.0.1:17653/report?ts='+Date.now());reportVersion=state.report_version}}catch{{}}}}setInterval(syncLanguage,1000);syncLanguage();renderPlans();renderSummary();legend('token-legend');legend('ratio-legend');chart('tokens','tokens');chart('ratio','ratio');renderQuotas();renderDetails();</script></body></html>'''


def collect_usages(
    days: int,
    codex_sessions: Path = LOCAL_CODEX_SESSIONS,
    claude_projects: Path = LOCAL_CLAUDE_PROJECTS,
    gemini_sessions: Path = LOCAL_GEMINI_SESSIONS,
    grok_sessions: Path = LOCAL_GROK_SESSIONS,
) -> tuple[list[Usage], RateLimitSnapshot | None, dict[str, int]]:
    configured = {(item["provider"], item["surface"]): Path(item["path"]) for item in load_configured_sources()}
    codex_sessions = configured.get(("chatgpt", "chatgpt-desktop"), codex_sessions)
    claude_projects = configured.get(("claude", "claude-code"), claude_projects)
    gemini_sessions = configured.get(("gemini", "gemini-cli"), gemini_sessions)
    grok_sessions = configured.get(("grok", "grok-local"), grok_sessions)
    since = report_today() - dt.timedelta(days=days - 1)
    codex_usages, snapshot, codex_files = parse_codex(codex_sessions, since)
    claude_usages, claude_files = parse_claude_code(claude_projects, since)
    gemini_usages, gemini_files = parse_gemini_cli(gemini_sessions, since)
    grok_usages, grok_files = parse_grok_build(grok_sessions, since)
    source_files = {"Codex": codex_files, "Claude Code": claude_files, "Gemini CLI": gemini_files, "Grok Build": grok_files}
    return codex_usages + claude_usages + gemini_usages + grok_usages, snapshot, source_files


def generate_report(days: int = 30, output: Path = DEFAULT_OUTPUT, pricing_path: Path = DEFAULT_PRICING, language: str = "zh-CN") -> Path:
    usages, snapshot, source_files = collect_usages(days)
    pricing = load_pricing(pricing_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(localize_html(render_dashboard(usages, snapshot, days, source_files, pricing), language), encoding="utf-8")
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
    codex_usages, snapshot, codex_files = parse_codex(args.codex_sessions, since)
    claude_usages, claude_files = parse_claude_code(args.claude_projects, since)
    gemini_usages, gemini_files = parse_gemini_cli(args.gemini_sessions, since)
    grok_usages, grok_files = parse_grok_build(args.grok_sessions, since)
    pricing = load_pricing(args.pricing)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    all_usages = codex_usages + claude_usages + gemini_usages + grok_usages
    source_files = {"Codex": codex_files, "Claude Code": claude_files, "Gemini CLI": gemini_files, "Grok Build": grok_files}
    page = localize_html(render_dashboard(all_usages, snapshot, args.days, source_files, pricing), args.language)
    args.output.write_text(page, encoding="utf-8")
    print(f"已生成：{args.output}")


if __name__ == "__main__":
    main()
