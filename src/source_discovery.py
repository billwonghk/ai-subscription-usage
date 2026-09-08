"""Read-only discovery and validated configuration for local AI usage sources."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from runtime_data import app_data_root


CONFIG_ROOT = app_data_root()
SOURCES_PATH = CONFIG_ROOT / "sources.json"


@dataclass(frozen=True)
class SourceDefinition:
    provider: str
    surface: str
    format: str
    label: str
    candidates: tuple[str, ...]
    patterns: tuple[str, ...]
    usage_support: str


DEFINITIONS = (
    SourceDefinition("chatgpt", "chatgpt-desktop", "codex-jsonl", "ChatGPT", ("~/.codex/sessions",), ("**/*.jsonl",), "exact"),
    SourceDefinition("claude", "claude-code", "claude-jsonl", "Claude Code", ("~/.claude/projects",), ("**/*.jsonl",), "exact"),
    SourceDefinition(
        "claude", "claude-desktop", "claude-desktop-metadata", "Claude Desktop",
        ("~/Library/Application Support/Claude/local-agent-mode-sessions", "%APPDATA%/Claude/local-agent-mode-sessions"),
        ("**/*.json", "**/*.jsonl"), "shared-log",
    ),
    SourceDefinition("gemini", "gemini-cli", "gemini-chat-json", "Gemini CLI", ("~/.gemini/tmp",), ("**/chats/*.json", "**/chats/*.jsonl"), "exact"),
    SourceDefinition("gemini", "antigravity-desktop", "antigravity-protobuf", "Antigravity Desktop", ("~/.gemini/antigravity",), ("conversations/*.pb", "conversations/*.db"), "detected-only"),
    SourceDefinition("gemini", "antigravity-cli", "antigravity-cli-session", "Antigravity CLI", ("~/.gemini/antigravity-cli",), ("conversations/*.db", "conversations/*.pb", "conversations/*.trajectory.json"), "detected-only"),
    SourceDefinition("grok", "grok-local", "grok-session", "Grok", ("~/.grok/sessions",), ("**/unified.jsonl", "**/signals.json", "**/chat_history.jsonl"), "exact-or-estimate"),
    SourceDefinition("minimax", "minimax-agent", "minimax-sqlite", "MiniMax", ("~/.minimax",), ("sqlite.db",), "exact"),
    SourceDefinition("kimi", "kimi-code", "kimi-wire-jsonl", "Kimi", ("~/.kimi/sessions", "~/.kimi-code/sessions"), ("**/wire.jsonl",), "exact"),
    SourceDefinition("kimi", "claude-code", "claude-jsonl", "Kimi via Claude Code", (), ("**/*.jsonl",), "exact"),
    SourceDefinition("glm", "claude-code", "claude-jsonl", "GLM via Claude Code", (), ("**/*.jsonl",), "exact"),
    SourceDefinition("bailian", "claude-code", "claude-jsonl", "Bailian via Claude Code", (), ("**/*.jsonl",), "exact"),
    SourceDefinition("glm", "glm-local", "glm-local-records", "GLM", ("~/.glm", "~/.zhipu"), ("**/*.jsonl", "**/*.db"), "detected-only"),
    SourceDefinition("bailian", "bailian-local", "bailian-local-records", "阿里百炼", ("~/.bailian", "~/.aliyun"), ("**/*.jsonl", "**/*.db"), "detected-only"),
)

ALLOWED = {(item.provider, item.surface, item.format): item for item in DEFINITIONS}


def expand_path(value: str) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(value.replace("%APPDATA%", os.environ.get("APPDATA", "%APPDATA%"))))
    return Path(expanded)


def _candidate_paths(definition: SourceDefinition) -> list[Path]:
    paths = []
    for candidate in definition.candidates:
        path = expand_path(candidate)
        if "%APPDATA%" not in str(path):
            paths.append(path)
    return paths


def _matching_files(path: Path, patterns: tuple[str, ...], limit: int = 10_000) -> int:
    total = 0
    for pattern in patterns:
        try:
            for candidate in path.glob(pattern):
                if candidate.is_file():
                    total += 1
                    if total >= limit:
                        return total
        except OSError:
            continue
    return total


def detect_installed_apps() -> dict[str, bool]:
    home = Path.home()
    applications = Path("/Applications")
    user_apps = home / "Applications"
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    programs = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
    return {
        "chatgpt": (applications / "ChatGPT.app").exists() or (local / "Programs" / "ChatGPT" / "ChatGPT.exe").exists(),
        "claude": (applications / "Claude.app").exists() or (local / "AnthropicClaude" / "claude.exe").exists(),
        "gemini": (applications / "Gemini.app").exists() or (local / "Programs" / "Gemini" / "Gemini.exe").exists(),
        "antigravity": (applications / "Antigravity.app").exists() or (programs / "Antigravity" / "Antigravity.exe").exists(),
        "grok": (user_apps / "Chrome Apps.localized" / "Grok.app").exists() or (applications / "Grok.app").exists() or (local / "Programs" / "Grok" / "Grok.exe").exists(),
        "minimax": (applications / "MiniMax.app").exists() or (home / ".minimax").exists(),
        "kimi": (applications / "Kimi.app").exists() or (home / ".kimi-code").exists() or (home / ".kimi").exists(),
        "glm": (applications / "智谱清言.app").exists() or (home / ".glm").exists() or (home / ".zhipu").exists(),
        "bailian": (home / ".bailian").exists() or (home / ".aliyun").exists(),
    }


def discover_sources() -> list[dict[str, Any]]:
    results = []
    for definition in DEFINITIONS:
        candidates = _candidate_paths(definition)
        existing = next((path for path in candidates if path.is_dir()), None)
        readable = bool(existing and os.access(existing, os.R_OK))
        files = _matching_files(existing, definition.patterns) if existing and readable else 0
        if not existing:
            status = "not_found"
        elif not readable:
            status = "permission_required"
        elif files:
            status = "ready" if definition.usage_support in {"exact", "exact-or-estimate", "shared-log"} else "unsupported_format"
        else:
            status = "no_records"
        results.append({
            "provider": definition.provider,
            "surface": definition.surface,
            "format": definition.format,
            "label": definition.label,
            "path": str(existing) if existing else str(candidates[0]) if candidates else "",
            "status": status,
            "matching_files": files,
            "usage_support": definition.usage_support,
            "read_only": True,
        })
    return results


def load_configured_sources() -> list[dict[str, Any]]:
    try:
        data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("sources"), list):
        return []
    valid = []
    for source in data["sources"]:
        try:
            valid.append(validate_source(source))
        except ValueError:
            continue
    return valid


def validate_source(source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise ValueError("source must be an object")
    key = (source.get("provider"), source.get("surface"), source.get("format"))
    definition = ALLOWED.get(key)
    if not definition:
        raise ValueError("unsupported provider, surface, or format")
    raw_path = source.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip() or "\x00" in raw_path:
        raise ValueError("invalid source path")
    path = expand_path(raw_path).resolve(strict=False)
    home = Path.home().resolve()
    if path != home and home not in path.parents:
        raise ValueError("source path must be inside the current user profile")
    if not path.is_dir():
        raise ValueError("source directory does not exist")
    if not os.access(path, os.R_OK):
        raise ValueError("source directory is not readable")
    files = _matching_files(path, definition.patterns)
    if files == 0:
        raise ValueError("source directory does not match the selected format")
    return {
        "provider": definition.provider,
        "surface": definition.surface,
        "format": definition.format,
        "path": str(path),
        "read_only": True,
    }


def configure_source(provider: str, surface: str, format_name: str, path: str) -> dict[str, Any]:
    validated = validate_source({"provider": provider, "surface": surface, "format": format_name, "path": path})
    sources = load_configured_sources()
    sources = [item for item in sources if (item["provider"], item["surface"]) != (provider, surface)]
    if surface == "claude-code" and provider != "claude":
        target = Path(validated["path"])
        for item in sources:
            if item["surface"] == "claude-code" and item["provider"] not in {"claude", provider}:
                other = Path(item["path"])
                if target.is_relative_to(other) or other.is_relative_to(target):
                    raise ValueError("subscription source directories must not overlap")
    sources.append(validated)
    payload = {"schema_version": 1, "sources": sorted(sources, key=lambda item: (item["provider"], item["surface"]))}
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = SOURCES_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(SOURCES_PATH)
    return validated


def doctor_report() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "os": platform.system(),
        "installed_apps": detect_installed_apps(),
        "discovered_sources": discover_sources(),
        "configured_sources": load_configured_sources(),
        "credentials_read": False,
        "conversation_content_read": False,
    }
