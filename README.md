# AI Subscription Usage

A local, no-account menu-bar / system-tray app that reads on-device usage logs from ChatGPT, Claude Code, Claude Desktop, Gemini CLI, and Grok, then compares 30 days of API-equivalent value against what you actually pay for each subscription. Everything runs on your own machine — no AI API key, no account login, no OAuth/Auth Token/Cookie access, and no cloud service in the loop.

**Features**
- 30-day dashboard: total/input/output tokens, API-equivalent value, effective subscription cost, and value multiple, per provider
- Daily token and value-multiple charts, per-model breakdown
- Subscription plan history (monthly/annual, prorated by effective date)
- Auto-discovery of local usage logs, with a safe, whitelisted way to point it at a non-default folder
- Seven languages: 简体中文, English, 日本語, 한국어, Français, Deutsch, Español
- Launch at login, adjustable refresh interval, one-click access to your local data folder
- Opt-in, anonymized diagnostics only — never conversation content, file paths, or credentials

**Screenshots**

| Report | Settings |
| --- | --- |
| ![Report dashboard](assets/screenshots/report.png) | ![Settings panel](assets/screenshots/settings.png) |

**Getting it**

No tagged release has been cut yet, so there isn't a prebuilt download on the [Releases](../../releases) page yet. Until then, build it yourself:

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/pip install pyinstaller
.venv-desktop/bin/pyinstaller --clean --noconfirm ai-subscription-usage.spec
```

The macOS build lands in `dist/AI Subscription Usage.app`; the Windows build (compiled and self-tested in CI, not yet hands-tested on a physical Windows machine — see the "Windows" note below) lands in `dist/AI Subscription Usage.exe`.

**Not supported**

Google Antigravity / Gemini Spark write encrypted local session files (`~/.gemini/antigravity/conversations/*.pb`) with no readable structure and no documented safe local API, so token usage for those cannot be read — they show up as detected but unpriced. Everything else in this README covers what already works.

---

AI Subscription Usage 读取本机 ChatGPT、Claude Desktop、Claude Code、Gemini CLI、Antigravity 和 Grok 的公开本地用量记录，将最近 30 天 Token 按官方 API 单价折算，并与同区间订阅成本比较。计算、图表和刷新均由确定性程序完成，不需要任何 AI API Key。ChatGPT 当前使用内部 Codex JSONL 格式，因此默认数据目录仍是 `~/.codex/sessions/`。

版本号显示在托盘菜单、报表页和帮助页。macOS 用户数据保存在 `~/Library/Application Support/AI Subscription Usage/`，Windows 用户数据保存在 `%LOCALAPPDATA%\AI Subscription Usage\`。升级只替换程序、内置价格库、语言和适配器；订阅计划、数据源配置、语言、诊断授权和本机报表不会被安装包覆盖。迁移配置前会在用户数据目录的 `backups/` 中保存原文件。

GitHub 通用发布包不包含订阅计划、Current detection、本机绝对路径、Token 统计或生成报表。Current detection 只在安装后的电脑上实时生成。发布工作流先执行 `scripts/privacy_check.py`，检查失败时停止构建。

macOS 版本运行在顶部菜单栏。Windows 版本运行在右下角系统托盘，由 GitHub Actions 的 Windows Runner 构建 `AI Subscription Usage.exe` 和 Inno Setup 安装程序。

报表顶部展示总 Token、输入 Token、输出 Token、API 等价价值、有效订阅成本和价值倍数。页面还提供四个平台的每日 Token、每日价值倍数、模型明细和未计价 Token。月订阅按 30 天、年订阅按 360 天分摊，计划生效日前不计算订阅成本。

## 数据来源

| 平台 | 本机目录 | 数据口径 |
| --- | --- | --- |
| ChatGPT | `~/.codex/sessions/` | 内部 Codex JSONL；输入、输出和缓存输入 |
| Claude Code | `~/.claude/projects/` | 输入、输出、缓存读取和缓存写入 |
| Claude Desktop | `~/Library/Application Support/Claude/local-agent-mode-sessions/` | 检测桌面会话；Token 使用量通过共享 Claude JSONL 汇总 |
| Gemini CLI | `~/.gemini/tmp/*/chats/` | 输入、输出、思考和缓存 Token |
| Antigravity Desktop | `~/.gemini/antigravity/` | 自动检测；当前 `.pb`格式未验证 Token 字段时不计价 |
| Antigravity CLI | `~/.gemini/antigravity-cli/` | 自动检测；未验证格式不计价 |
| Grok Build | `~/.grok/logs/unified.jsonl` | 优先读取精确输入、输出、推理和缓存 Token |
| Grok Build 降级来源 | `~/.grok/sessions/**/signals.json` | 仅在没有 `unified.jsonl` 时使用，标记为估算 |

模型名必须与 `config/pricing.json` 精确匹配。未知模型继续统计 Token，但不计算 API 等价价值，也不会套用其他模型价格。价格库支持按生效日期保存不同价格，历史记录使用当天有效价格。

## 命令行生成

```bash
python3 src/ai_usage_report.py --days 30
```

结果写入 `outputs/ai-usage-report.html`。页面右上角的“更新本机数据”按钮连接桌面应用在 `127.0.0.1:17653` 提供的本机刷新接口；端口只绑定回环地址，不对局域网或公网开放。

## macOS 菜单栏与 Windows 托盘

桌面应用提供打开报表、立即更新、更新模型价格、检查应用更新、切换语言、配置及使用说明、匿名诊断开关和退出。首次启动自动打开配置及使用说明，其中显示本机数据源检测状态、诊断命令和可复制给本机 AI 的安全配置提示词。默认每 24 小时更新一次本机数据并检查应用版本。

## 自动发现与 AI 辅助配置

应用只检查已登记的默认目录，不扫描整个硬盘。运行 `AI Subscription Usage --doctor --json` 查看 ChatGPT、Claude Desktop、Claude Code、Gemini CLI、Antigravity Desktop、Antigravity CLI 和 Grok 的检测状态。非默认目录使用受控命令配置：

```bash
AI\ Subscription\ Usage --configure-source --provider chatgpt --surface chatgpt-desktop --format codex-jsonl --path "$HOME/.codex/sessions"
AI\ Subscription\ Usage --verify-sources --json
```

`SETUP_WITH_AI.md` 可以交给用户自己的 ChatGPT、Claude Code、Gemini CLI 或其他本机 AI。AI只能调用上述只读诊断与受控配置命令。配置文件不接受命令、网络地址、凭证或任意解析代码。

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/python src/desktop_app.py
```

桌面应用是长期运行的菜单栏或托盘进程。启动前应确认本机没有其他程序占用 `17653`，退出菜单会关闭托盘和本机刷新接口。

## 多语言

桌面外壳包含简体中文、英语、日语、韩语、法语、德语和西班牙语资源，默认跟随操作系统语言，可从托盘菜单切换。所有计算字段和价格数据库不因语言变化。

## 价格库更新

`config/pricing.json` 保存价格版本、官方来源、模型价格和生效日期。客户端从价格清单下载价格文件，先校验 SHA-256 和字段结构，再原子替换本机价格库。发布 GitHub 仓库后，将 `config/update-settings.example.json` 中的占位地址替换为正式仓库地址，并发布 `pricing-manifest.json`。

## 匿名诊断

匿名诊断默认关闭，用户在托盘菜单明确开启后才上传。允许字段只有应用版本、操作系统、语言、错误模块、错误类型、脱敏调用栈和适配器状态。禁止上传对话正文、提示词、回复内容、用户名、本机文件路径、API Key、订阅信息、Token 明细和原始日志。AI Crew 诊断入口发布后写入 `telemetry_endpoint`。

## 自动发布

`.github/workflows/release.yml` 在版本标签推送后执行测试，构建 macOS 与 Windows 产物，生成 SHA-256 校验文件并创建 GitHub Release。正式自动更新还需要 GitHub 仓库地址、macOS Developer ID、公证凭证和 Windows 代码签名证书。

## 许可证

项目自有代码采用 MIT 许可证。复用第三方代码时必须将许可证、版权声明和来源写入 `THIRD_PARTY_NOTICES.md`。
