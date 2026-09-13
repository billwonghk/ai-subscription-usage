# AI Subscription Usage

[English](README.md) | [简体中文](README.zh-CN.md) | **繁體中文** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Deutsch](README.de.md) | [Español](README.es.md)

這是一個在本機執行、不需要註冊帳號的選單列／系統匣應用程式。它會讀取本機 ChatGPT、Claude Code、Claude Desktop、Gemini CLI、Grok 和 MiniMax 已支援的用量記錄，並比較最近 30 天的 API 等價價值與實際訂閱費用。Kimi、GLM 和阿里百鍊目前只偵測安裝與記錄檔案，格式驗證完成前不計入用量。所有計算都在使用者自己的電腦上完成，不需要 AI API Key、不需要帳號登入，也不會讀取 OAuth、Auth Token、Cookie 或對話內容。

⭐ 如果這個工具協助你了解 AI 訂閱是否划算，可以為專案加上 Star。

📺 **影片示範：** [YouTube](https://youtu.be/VXnwn82lOsc) · [B 站](https://www.bilibili.com/video/BV1kN8h6NEQy/)

**功能**

- 30 天儀表板：顯示每個平台的 Token 總數、輸入、輸出、API 等價價值、有效訂閱成本和價值倍數
- 每日 Token 與每日價值倍數圖表，並依模型顯示詳細資料
- 訂閱方案記錄：支援月繳、年繳與生效日期分攤
- 平台管理：只讀取、計算並顯示使用者已新增的平台
- 支援以 USD 或 CNY 儲存訂閱金額和切換報表幣別，並依 ECB 每日參考匯率換算
- 自動尋找本機用量記錄，也可透過安全的白名單方式指定非預設目錄
- OpenRouter 支援的模型價格約每週自動更新；價格變更會建立新的日期區間，歷史報表仍使用用量當日有效的價格
- 支援八種語言：简体中文、繁體中文、English、日本語、한국어、Français、Deutsch、Español
- 登入時自動啟動、每天凌晨 3:00 自動更新、當天漏更時於啟動 15 分鐘後補更新，以及一鍵開啟本機資料夾
- 匿名診斷預設關閉，只有手動開啟後才會傳送，且不會傳送對話內容、檔案路徑或金鑰

## 取得應用程式

前往 [Releases](../../releases) 頁面下載最新版本。Apple Silicon Mac（M1 及後續晶片）使用者下載 `AI-Subscription-Usage-macOS-Apple-Silicon.zip`，Intel Mac 使用者下載 `AI-Subscription-Usage-macOS-Intel.zip`；解壓縮後把 `AI Subscription Usage.app` 拖入「應用程式」資料夾。Windows 使用者可安裝 `AI-Subscription-Usage-Windows-Setup.exe`，或下載 `AI-Subscription-Usage-Windows-Portable.zip` 後直接執行其中的程式。

每次發行都附有 `SHA256SUMS.txt`，可用於確認下載檔案未被竄改。Windows 版本會在 CI 中編譯並執行自動測試，但尚未在實體 Windows 電腦上完成手動驗證。

從原始碼建置：

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/pip install pyinstaller
.venv-desktop/bin/pyinstaller --clean --noconfirm ai-subscription-usage.spec
```

macOS 建置結果位於 `dist/AI Subscription Usage.app`；Windows 建置結果位於 `dist/AI Subscription Usage.exe`。

## 平台驗證狀態

| 平台 | macOS | Windows |
| --- | --- | --- |
| ChatGPT | 已驗證 | 程式邏輯相同，尚未在實體 Windows 測試 |
| Claude | 桌面版與命令列均已驗證 | 已加入 Windows 路徑，尚未在實體 Windows 測試 |
| Gemini CLI | 已驗證 | 尚未在實體 Windows 測試 |
| Gemini Desktop（Antigravity／Spark） | 本機檔案已加密，無法解析 | 同一產品，尚未在 Windows 單獨驗證 |
| Grok | 已完成程式邏輯，本機沒有真實資料可驗證 | 尚未驗證 |
| MiniMax | 已在 macOS 驗證本機 Token 計量表 | 已實作解析器，尚未在實體 Windows 測試 |
| Kimi／GLM／阿里百鍊 | 只偵測安裝與本機檔案，格式驗證前不解析用量 | 相同 |

Gemini Desktop（Antigravity／Spark）把本機工作階段記錄寫入加密的 `.pb` 檔案，沒有可讀結構或公開且安全的本機介面，因此無法讀取其 Token 用量。

## 資料與隱私

版本號會顯示在選單列／系統匣選單、報表頁和說明頁。macOS 使用者資料儲存在 `~/Library/Application Support/AI Subscription Usage/`，Windows 使用者資料儲存在 `%LOCALAPPDATA%\AI Subscription Usage\`。升級只替換程式、內建價格庫、語言資源與介面卡；訂閱方案、資料來源設定、語言、診斷授權和本機報表不會被安裝程式覆寫。設定遷移前，原始檔案會備份到使用者資料目錄的 `backups/`。

GitHub 公開發行套件不包含訂閱方案、偵測結果、本機絕對路徑、Token 統計或產生的報表。發行工作流程會先執行 `scripts/privacy_check.py`，檢查失敗時停止建置。

匿名診斷預設關閉。允許傳送的欄位只包含應用程式版本、作業系統、語言、錯誤模組、錯誤類型、去識別化呼叫堆疊和介面卡狀態。程式禁止傳送對話內容、提示詞、回覆、使用者名稱、本機檔案路徑、API Key、訂閱資料、Token 明細與原始記錄。

## 資料來源

| 平台 | 本機目錄 | 資料口徑 |
| --- | --- | --- |
| ChatGPT | `~/.codex/sessions/` | 內部 Codex JSONL；輸入、輸出與快取輸入 |
| Claude Code | `~/.claude/projects/` | 輸入、輸出、快取讀取與快取寫入 |
| Claude Desktop | `~/Library/Application Support/Claude/local-agent-mode-sessions/` | 偵測桌面工作階段；Token 用量透過共用 Claude JSONL 彙總 |
| Gemini CLI | `~/.gemini/tmp/*/chats/` | 輸入、輸出、思考與快取 Token |
| Antigravity Desktop | `~/.gemini/antigravity/` | 自動偵測；`.pb` 格式未驗證 Token 欄位時不計價 |
| Antigravity CLI | `~/.gemini/antigravity-cli/` | 自動偵測；未驗證格式不計價 |
| Grok Build | `~/.grok/logs/unified.jsonl` | 優先讀取精確的輸入、輸出、推理與快取 Token |
| Grok Build 備用來源 | `~/.grok/sessions/**/signals.json` | 只有缺少 `unified.jsonl` 時使用，並標示為估算 |
| MiniMax | `~/.minimax/sqlite.db` | 從本機計量表讀取輸入、輸出、推理、快取讀取與快取寫入 Token |
| Kimi | `~/.kimi-code/sessions/` 或 `~/.kimi/sessions/` | 只偵測；本機格式尚未驗證，不計入用量 |
| GLM | `~/.glm/` 或 `~/.zhipu/` | 只偵測；本機格式尚未驗證，不計入用量 |
| 阿里百鍊 | `~/.bailian/` 或 `~/.aliyun/` | 只偵測；本機格式尚未驗證，不計入用量 |

模型名稱必須與 `config/pricing.json` 精確符合。未知模型仍會統計 Token，但不計算 API 等價價值，也不會套用其他模型的價格。價格庫可以依生效日期保存不同價格，歷史記錄使用當日有效價格。

## 執行與設定

使用命令列產生報表：

```bash
python3 src/ai_usage_report.py --days 30
```

結果會寫入 `outputs/ai-usage-report.html`。桌面應用程式只在 `127.0.0.1:17653` 提供本機報表和控制介面，該連接埠只綁定回送位址，不會對區域網路或網際網路開放。每位使用者只執行一個應用程式實例；重複啟動時，新程序會通知既有實例開啟報表後自行結束。

左鍵點擊狀態列圖示只會立即開啟或重用既有報表，不會觸發更新。首次安裝且沒有報表時會產生初始報表。之後依本機時間每天凌晨 3:00 更新一次；當天漏更時，應用程式在下次啟動 15 分鐘後補更新；當天已成功更新則略過。

應用程式只檢查已登記的預設目錄，不會掃描整個硬碟。可使用下列命令檢查和設定資料來源：

```bash
AI\ Subscription\ Usage --doctor --json
AI\ Subscription\ Usage --configure-source --provider PROVIDER --surface SURFACE --format FORMAT --path DIRECTORY
AI\ Subscription\ Usage --verify-sources --json
AI\ Subscription\ Usage --refresh
```

`SETUP_WITH_AI.md` 可以交給使用者自己的本機 AI。AI 只能執行上述唯讀診斷與受控設定命令。設定檔不接受命令、網路位址、憑證或任意解析程式碼。

## 語言、價格與更新

桌面外殼包含简体中文、繁體中文、英文、日文、韓文、法文、德文和西班牙文資源。預設會依作業系統語言選擇，`zh-TW`、`zh-HK`、`zh-MO` 和 `zh-Hant` 使用繁體中文，其他中文地區使用简体中文。使用者可以在設定頁切換語言；切換只更新顯示文字，不會掃描用量、更新價格，或修改訂閱金額、幣別、平台 ID 和模型 ID。

`config/pricing.json` 保存價格版本、來源、模型價格和生效日期。`scripts/fetch_pricing.py` 依 `config/model_id_map.json` 從 OpenRouter 取得目前價格，變價時關閉既有期間並建立從當日開始的新期間。標示為其他官方來源且由人工維護的項目不會被 OpenRouter 覆寫。

每個平台的詳細資料也會顯示快取命中率，以及同一批用量改用 DeepSeek 時的參考成本。模型依 `config/deepseek_tier_map.json` 對應 DeepSeek V4 Flash 或 Pro；快取命中與未命中比例使用真實記錄，不使用推測比例。

Windows 版本支援在應用程式內下載並啟動更新。macOS 版本因未開通 Apple Developer Program 付費會員，無法使用 Developer ID 簽章和 Apple 公證，因此不提供 macOS 自動安裝更新。使用者需要手動下載並替換應用程式。

## 授權條款

本專案採用 [PolyForm Noncommercial 1.0.0](LICENSE) 授權條款：可以免費使用、學習、修改和分享，但不得用於商業用途。重用第三方程式碼時，仍需在 `THIRD_PARTY_NOTICES.md` 保留對方的授權條款、著作權聲明和來源。
