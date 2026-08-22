# AI Subscription Usage

**English** | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Español](README.es.md)

A local, no-account menu-bar / system-tray app that reads on-device usage logs from ChatGPT, Claude Code, Claude Desktop, Gemini CLI, and Grok, then compares 30 days of API-equivalent value against what you actually pay for each subscription. Everything runs on your own machine — no AI API key, no account login, no OAuth/Auth Token/Cookie access, and no cloud service in the loop.

**Features**
- 30-day dashboard: total/input/output tokens, API-equivalent value, effective subscription cost, and value multiple, per provider
- Daily token and value-multiple charts, per-model breakdown
- Subscription plan history (monthly/annual, prorated by effective date)
- Auto-discovery of local usage logs, with a safe, whitelisted way to point it at a non-default folder
- Model pricing for supported models refreshes automatically about once a week from [OpenRouter](https://openrouter.ai/)'s public API pricing data — no manual editing needed
- Seven languages: English, Français, Deutsch, Español, 简体中文, 日本語, 한국어
- Launch at login, adjustable refresh interval, one-click access to your local data folder
- Opt-in, anonymized diagnostics only — never conversation content, file paths, or credentials

**Screenshots**

| Report | Settings |
| --- | --- |
| ![Report dashboard](assets/screenshots/report.png) | ![Settings panel](assets/screenshots/settings.png) |

Per-provider detail (per-model tokens and value), and the same report in Chinese:

![Claude provider detail](assets/screenshots/report-claude-tab.png)
![Report in Chinese](assets/screenshots/report-zh.png)

**Getting it**

Download the latest build from the [Releases](../../releases) page:
- **macOS**: `AI-Subscription-Usage-macOS.zip` — unzip it and move `AI Subscription Usage.app` to Applications.
- **Windows**: `AI-Subscription-Usage-Windows-Setup.exe` for a normal install (Start Menu shortcut, proper uninstall), or `AI-Subscription-Usage-Windows-Portable.zip` if you'd rather just unzip and run the .exe directly with nothing written to the registry or Program Files.

Every release also ships a `SHA256SUMS.txt` to verify your download. The Windows build is compiled and self-tested in CI but hasn't been hands-tested on a physical Windows machine yet — see the table below.

Prefer building from source instead?

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/pip install pyinstaller
.venv-desktop/bin/pyinstaller --clean --noconfirm ai-subscription-usage.spec
```

The macOS build lands in `dist/AI Subscription Usage.app`; the Windows build lands in `dist/AI Subscription Usage.exe`.

## What's verified so far

| Platform | macOS (desktop + CLI) | Windows (desktop + CLI) |
| --- | --- | --- |
| ChatGPT | ✅ Works, verified | 🟡 Same code path, should work — not tested on real Windows |
| Claude | ✅ Works, verified (desktop and CLI share the same log) | 🟡 Desktop has a dedicated Windows path; CLI should work too — not tested on real Windows |
| Gemini CLI | ✅ Works, verified | 🟡 Should work — not tested on real Windows |
| Gemini Desktop (Antigravity/Spark) | ❌ Confirmed not possible | ❌ Likely also not possible (same product) — not specifically confirmed |
| Grok | 🟡 Code should be correct, but there's no real Grok data on this machine to verify against | 🟡 Also unverified, and Windows testing hasn't happened either |

Gemini Desktop (Antigravity/Spark) writes encrypted local session files (`~/.gemini/antigravity/conversations/*.pb`) with no readable structure and no documented safe local API, so token usage for those cannot be read — they show up as detected but unpriced.

If you have a Windows machine, or you actually use Grok, testing and feedback are especially welcome — those are the two areas that can't be verified here. Please open an [Issue](../../issues) if you run into problems.

## Overview

Version numbers are shown in the tray menu, the report page, and the help page. macOS stores user data in `~/Library/Application Support/AI Subscription Usage/`; Windows stores it in `%LOCALAPPDATA%\AI Subscription Usage\`. An upgrade only replaces the program, the built-in pricing database, language files, and adapters — subscription plans, data-source configuration, language choice, diagnostics opt-in, and local reports are never overwritten by the installer. Before migrating settings, the original files are backed up under `backups/` in the user data directory.

The public GitHub release does not contain subscription plans, detection results, local absolute paths, token counts, or generated reports — detection results are only ever generated live, on the machine where the app is installed. The release workflow runs `scripts/privacy_check.py` first and stops the build if it fails.

## Data sources

| Platform | Local folder | What's counted |
| --- | --- | --- |
| ChatGPT | `~/.codex/sessions/` | Internal Codex JSONL; input, output, and cached input |
| Claude Code | `~/.claude/projects/` | Input, output, cache read, and cache write |
| Claude Desktop | `~/Library/Application Support/Claude/local-agent-mode-sessions/` | Detects desktop sessions; token usage is aggregated via the shared Claude JSONL log |
| Gemini CLI | `~/.gemini/tmp/*/chats/` | Input, output, thinking, and cached tokens |
| Antigravity Desktop | `~/.gemini/antigravity/` | Auto-detected; not priced while the `.pb` format's token fields remain unverified |
| Antigravity CLI | `~/.gemini/antigravity-cli/` | Auto-detected; not priced while the format is unverified |
| Grok Build | `~/.grok/logs/unified.jsonl` | Prefers exact input, output, reasoning, and cached tokens |
| Grok Build fallback | `~/.grok/sessions/**/signals.json` | Used only when `unified.jsonl` isn't present; flagged as an estimate |

Model names must match `config/pricing.json` exactly. Unknown models still have their tokens counted, but no API-equivalent value is calculated for them, and no other model's price is applied. The pricing database can store different prices per effective date; historical records use whichever price was in effect on that day.

## Generating from the command line

```bash
python3 src/ai_usage_report.py --days 30
```

Output is written to `outputs/ai-usage-report.html`. The "Refresh local data" button in the top-right corner talks to the local refresh endpoint the desktop app serves on `127.0.0.1:17653`; the port only binds to loopback and is never exposed to the LAN or the internet.

## macOS menu bar & Windows tray

The desktop app provides: open report, refresh now, update model pricing, check for app updates, switch language, configuration & user guide, an anonymous-diagnostics toggle, and quit. On first launch it automatically opens the configuration & user guide, which shows local data-source detection status, diagnostic commands, and a safe configuration prompt you can copy to your own local AI assistant. By default it refreshes local data and checks the app version every 24 hours.

## Auto-discovery & AI-assisted configuration

The app only checks registered default folders — it never scans the whole disk. Run `AI Subscription Usage --doctor --json` to see detection status for ChatGPT, Claude Desktop, Claude Code, Gemini CLI, Antigravity Desktop, Antigravity CLI, and Grok. Non-default folders are configured through controlled commands:

```bash
AI\ Subscription\ Usage --configure-source --provider chatgpt --surface chatgpt-desktop --format codex-jsonl --path "$HOME/.codex/sessions"
AI\ Subscription\ Usage --verify-sources --json
```

`SETUP_WITH_AI.md` can be handed to your own ChatGPT, Claude Code, Gemini CLI, or other local AI assistant — it can only call the read-only diagnostic and controlled-configuration commands above. The configuration file never accepts commands, network addresses, credentials, or arbitrary parsing code.

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/python src/desktop_app.py
```

The desktop app is a long-running menu-bar/tray process. Make sure nothing else on your machine is already using port `17653` before starting it; quitting from the menu shuts down both the tray icon and the local refresh endpoint.

## Multiple languages

The desktop shell ships with English, French, German, Spanish, Simplified Chinese, Japanese, and Korean resources. It follows the OS language by default and can be switched from the settings page. No calculated field or pricing data changes with language.

## Pricing database updates

`config/pricing.json` stores the pricing version, official sources, model prices, and effective dates. The client downloads pricing updates from a manifest, verifies the SHA-256 checksum and field structure, then atomically replaces the local pricing database. This tool is meant to show a trend, not to be a perfectly precise pricing reference, so the update source is [OpenRouter](https://openrouter.ai/)'s public API pricing data — a well-known LLM proxy whose API prices generally track official rates.

`config/model_id_map.json` maps this project's local model names to their exact OpenRouter model id. `scripts/fetch_pricing.py` uses that map to pull current prices and rewrite `config/pricing.json` and `config/pricing-manifest.json`; `.github/workflows/update-pricing.yml` runs it automatically about once a week and commits only if a price actually changed. A genuine price change is recorded as a new dated period so past report dates keep using whatever rate was actually in effect back then. Models that already use a hand-written dated schedule are left untouched by the automation. When usage logs show a brand-new model name that isn't in the map yet, it's simply shown as unpriced until a line is added to `config/model_id_map.json` — the desktop app also tries an on-the-spot price refresh the moment it detects a new model.

Each provider's detail tab also shows its cache-hit rate for the period, plus an estimated cost if the same usage had run on [DeepSeek](https://www.deepseek.com/) instead. Each model is matched to a DeepSeek V4 Flash or Pro tier by capability class (see `config/deepseek_tier_map.json`), using DeepSeek's own public pricing (also kept current via OpenRouter) and this period's real cache-hit/miss split — not a guessed ratio. Flagship models with no real DeepSeek equivalent are still compared against Pro, deliberately in DeepSeek's favor, so the comparison never overstates the case.

## Anonymous diagnostics

Anonymous diagnostics are off by default and only upload after you explicitly turn them on in settings. Allowed fields are limited to: app version, OS, language, error module, error type, a redacted stack trace, and adapter status. Never uploaded: conversation content, prompts, replies, usernames, local file paths, API keys, subscription details, token breakdowns, or raw logs. The `telemetry_endpoint` will be filled in once the diagnostics intake is published.

## Automatic releases

`.github/workflows/release.yml` runs tests after a version tag is pushed, builds macOS and Windows artifacts, generates SHA-256 checksums, and creates a GitHub Release. Fully automatic updates additionally require a GitHub repo address, a macOS Developer ID, notarization credentials, and a Windows code-signing certificate.

## License

This project is released under the [PolyForm Noncommercial 1.0.0](LICENSE) license — free to use, study, modify, and share for any non-commercial purpose. Commercial use is not permitted. Questions about the license, or about a specific use case? Please open an [Issue](../../issues). Reused third-party code must still have its license, copyright notice, and source recorded in `THIRD_PARTY_NOTICES.md`.
