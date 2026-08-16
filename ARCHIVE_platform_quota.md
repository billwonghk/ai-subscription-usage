# 平台额度模块归档（0.5.0 版本移除）

## 移除原因

`0.4.0` 版本曾在报表里展示 ChatGPT / Claude / Gemini / Grok 四个平台的"五小时额度"和"周额度"。经过对 Claude Desktop 的安全边界核查（详见接手记录），实际情况是：

- **ChatGPT（Codex）**：本机日志自带 `primary`/`secondary` 额度字段，是四个平台里唯一能稳定读到实时数据的。
- **Claude**：唯一安全渠道是 Claude Code 命令行工具的官方 `statusLine` 机制。该机制只在用户直接在终端交互式运行 `claude` 时触发，Claude Desktop 普通聊天窗口和 Cowork/本机代理模式都不会触发——经实测确认，即使在 statusLine 配置正确、脚本路径修复之后，Cowork 场景下额度快照文件仍然不会生成。对使用 Claude Desktop 聊天为主的用户，这块永远显示 N/A。
- **Gemini / Antigravity**：没有公开本机额度数据源。
- **Grok**：没有公开本机额度数据源，甚至连 token 用量都拿不到。

四个平台里三个在实际使用场景下永远显示不出数据，为了避免报表长期呈现"一边有数据一边一直空着"的残缺状态，`0.5.0` 版本把"平台额度"这个区块整体从报表、代码和多语言翻译里移除，**只保留其余用量统计（Token、API 等价价值、订阅成本、价值倍数）**。

如果以后某个平台（尤其是 Anthropic）开放了安全、稳定、不需要 OAuth/Token/Cookie 的实时额度接口，可以照本文档恢复。

---

## 移除前的完整实现（可直接复制恢复）

### 1. `src/claude_code_quota.py`（整份文件）

```python
#!/usr/bin/env python3
"""Capture Claude Code's documented statusLine rate-limit snapshot."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

from runtime_data import app_data_root

SNAPSHOT_PATH = app_data_root() / "claude-code-quota.json"


def _window(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    used, reset = value.get("used_percentage"), value.get("resets_at")
    if not isinstance(used, (int, float)) and not isinstance(reset, (int, float, str)):
        return None
    result: dict[str, Any] = {}
    if isinstance(used, (int, float)):
        result["used_percentage"] = max(0.0, min(100.0, float(used)))
    if isinstance(reset, (int, float, str)):
        result["resets_at"] = reset
    return result


def snapshot_from_statusline(payload: Any) -> dict[str, Any] | None:
    limits = payload.get("rate_limits") if isinstance(payload, dict) else None
    if not isinstance(limits, dict):
        return None
    snapshot = {
        "captured_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "five_hour": _window(limits.get("five_hour")),
        "seven_day": _window(limits.get("seven_day")),
    }
    return snapshot if snapshot["five_hour"] or snapshot["seven_day"] else None


def save_snapshot(snapshot: dict[str, Any], path: Path = SNAPSHOT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def main() -> int:
    try:
        snapshot = snapshot_from_statusline(json.load(sys.stdin))
    except (json.JSONDecodeError, OSError):
        return 0
    if snapshot:
        try:
            save_snapshot(snapshot)
        except OSError:
            pass
        parts = []
        for label, key in (("5h", "five_hour"), ("7d", "seven_day")):
            window = snapshot.get(key)
            if isinstance(window, dict) and isinstance(window.get("used_percentage"), (int, float)):
                parts.append(f"{label} {window['used_percentage']:.0f}% used")
        if parts:
            print(" · ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

需要在 `~/.claude/settings.json` 里配置 `statusLine` 指向这个脚本才会有数据：

```json
{"type": "command", "command": "/usr/bin/python3 /path/to/src/claude_code_quota.py"}
```

### 2. `src/ai_usage_report.py` 里的额度相关代码

```python
@dataclass
class RateLimitWindow:
    window_minutes: int
    used_percent: float | None = None
    resets_at: str | None = None


@dataclass
class RateLimitSnapshot:
    windows: list[RateLimitWindow]
    source_file: str | None = None


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
```

`parse_codex()` 内部会调用 `extract_rate_limit(record, path)`，把最新的快照记录在 `latest_snapshot` 变量里，随 `(usages, latest_snapshot, files_read)` 一起返回。

```python
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
```

`PROVIDER_META` 曾经带 `"quota": True/False` 字段：

```python
PROVIDER_META = {
    "Codex": {"label": "ChatGPT", "plan": "ChatGPT", "color": "#61a8ff", "quota": True},
    "Claude Code": {"label": "Claude", "plan": "Claude", "color": "#ff9f43", "quota": True},
    "Gemini CLI": {"label": "Gemini / Antigravity", "plan": "Gemini", "color": "#23d8aa", "quota": False},
    "Grok Build": {"label": "Grok", "plan": "Grok", "color": "#b180ff", "quota": False},
}
```

`render_dashboard()` 里，在给每个 provider 组装 payload 之前，先加载 Claude 的 statusLine 快照：

```python
claude_quota_snapshot = load_claude_quota_snapshot()
```

然后每个 provider 循环内计算额度：

```python
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
```

写进 provider payload 的字段：

```python
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
```

报表 HTML 里的"平台额度"区块：

```html
<section class="section"><h2>平台额度</h2><p>只展示本机日志提供的真实额度快照；没有额度记录的平台显示"本机记录未提供"。</p><div id="quota-grid" class="quota-grid"></div></section>
```

配套的渲染 JS：

```javascript
function quotaItem(name,q,note){return `<div class="quota-item"><div class="muted">${name}${q.available?' · 剩余':''}</div>${q.available?`<strong>${q.remaining.toFixed(0)}%</strong><div class="muted quota-note">重置 ${esc(q.reset)}</div>`:`<strong>N/A</strong><div class="muted quota-note">${esc(note)}</div>`}</div>`}
function renderQuotas(){$('quota-grid').innerHTML=DATA.providers.map(p=>`<div class="quota-card"><h3>${esc(p.label)}</h3><div class="quota-pair">${quotaItem('五小时额度',p.quota.five_hour,p.quota_note)}${quotaItem('周额度',p.quota.weekly,p.quota_note)}</div></div>`).join('')}
```

页面加载时调用 `renderQuotas()`。

配套 CSS：`.quota-grid`、`.quota-card`、`.quota-pair`、`.quota-item`、`.quota-note`（定义在 `render_dashboard` 内嵌样式表里）。

### 3. `src/report_i18n.py` 里的翻译条目

`ZH` 列表和每个语言的 `TRANSLATIONS` 数组里，按位置对应删掉了："平台额度"/"Provider quotas"、"五小时额度"/"Five-hour quota"、"周额度"/"Weekly quota"、"剩余"/"Remaining"、"已用"/"Used"、"重置"/"Reset"、"本机记录未提供"/"Not provided by local records"（"平台详情"/"Provider details" 保留，报表详情区块还在用）。

`EXTRA_TRANSLATIONS` 六种语言字典里各删掉了 4 条：额度区块说明句、Claude/Gemini/Grok 三条 quota_note 译文。具体文本见 git 历史（`git log -p -- src/report_i18n.py`，0.5.0 之前的提交）。

### 4. `tests/test_adapters.py` 里被删除的测试

- `test_claude_statusline_keeps_only_rate_limits`（测试 `claude_code_quota.snapshot_from_statusline`）
- `test_codex_report_has_independent_charts_and_subscription_input`（测试已经死代码化的 `render_report`，该函数本身也随额度一起被删除）
- `test_dashboard_aggregates_all_providers_and_builds_provider_details` 里的 `self.assertIn("不读取 OAuth/Auth Token", page)` 断言

---

## 如何恢复

1. 把上面的代码原样粘回对应文件。
2. `src/ai_usage_report.py` 的 `parse_codex()`、`collect_usages()`、`generate_report()`、`main()`、`render_dashboard()` 需要重新带上 `RateLimitSnapshot` 参数（0.5.0 移除时把这些函数签名精简为不带 snapshot）。
3. `PROVIDER_META` 加回 `"quota"` 字段。
4. `src/runtime_data.py` 的 `initialize_user_data()` 迁移文件清单里把 `"claude-code-quota.json"` 加回去。
5. 重新跑一遍测试，把上面第 4 节列的测试加回来。
