# AI Subscription Usage

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | **한국어** | [Français](README.fr.md) | [Deutsch](README.de.md) | [Español](README.es.md)

ChatGPT, Claude Code, Claude Desktop, Gemini CLI, Grok의 온디바이스 사용 기록을 읽어, 최근 30일간의 API 환산 가치와 실제로 지불한 구독 비용을 비교해 주는 계정 등록 불필요한 메뉴바 / 시스템 트레이 앱입니다. 모든 처리는 사용자 자신의 컴퓨터에서만 이루어집니다 — AI API 키 불필요, 계정 로그인 불필요, OAuth/Auth Token/Cookie 접근 없음, 클라우드 서비스도 전혀 개입하지 않습니다.

⭐ 이 도구가 AI 구독이 정말 그만한 가치가 있는지 확인하는 데 도움이 되었다면, Star를 눌러 다른 사람들도 찾을 수 있게 해주세요.

📺 **데모 영상:** YouTube (링크 준비 중) · Bilibili (링크 준비 중)

**기능**
- 30일 대시보드: 제공업체별 총/입력/출력 토큰, API 환산 가치, 유효 구독 비용, 가치 배수
- 일별 토큰 및 가치 배수 차트, 모델별 세부 내역
- 구독 플랜 이력(월간/연간, 적용일 기준 일할 계산)
- 로컬 사용 기록 자동 탐지, 기본 위치가 아닌 폴더를 지정할 수 있는 안전한 화이트리스트 방식도 지원
- 지원되는 모델의 가격은 [OpenRouter](https://openrouter.ai/)의 공개 API 가격 데이터에서 약 주 1회 자동 업데이트 — 수동 편집 불필요
- 7개 언어 지원: English, Français, Deutsch, Español, 简体中文, 日本語, 한국어
- 로그인 시 자동 실행, 갱신 주기 조절, 로컬 데이터 폴더로의 원클릭 접근
- 옵트인 방식의 익명 진단만 수집 — 대화 내용, 파일 경로, 자격 증명은 절대 포함되지 않음

**스크린샷**

| 리포트 | 설정 |
| --- | --- |
| ![리포트 대시보드](assets/screenshots/report.png) | ![설정 패널](assets/screenshots/settings.png) |

제공업체별 상세(모델별 토큰과 가치), 그리고 중국어판 리포트:

![Claude 제공업체 상세](assets/screenshots/report-claude-tab.png)
![중국어판 리포트](assets/screenshots/report-zh.png)

DeepSeek 비교와 전체 모델-등급 매핑에 대한 자세한 내용은 앱 내 구성 및 사용 안내에 문서화되어 있습니다:

![DeepSeek 비교 방법론과 모델 매핑 표](assets/screenshots/deepseek-methodology-en.png)

**받는 방법**

[Releases](../../releases) 페이지에서 최신 빌드를 다운로드하세요:
- **macOS**: `AI-Subscription-Usage-macOS.zip` — 압축을 풀고 `AI Subscription Usage.app`을 Applications 폴더로 옮기세요.
- **Windows**: 일반 설치(시작 메뉴 바로가기, 정상적인 제거 기능)를 원하면 `AI-Subscription-Usage-Windows-Setup.exe`를, 레지스트리나 Program Files에 아무것도 기록하고 싶지 않다면 압축만 풀고 바로 실행할 수 있는 `AI-Subscription-Usage-Windows-Portable.zip`을 사용하세요.

모든 릴리스에는 다운로드 검증용 `SHA256SUMS.txt`도 함께 제공됩니다. Windows 빌드는 CI에서 컴파일 및 자체 테스트를 거쳤지만, 아직 실제 Windows 기기에서 직접 테스트되지는 않았습니다 — 아래 표를 참고하세요.

소스에서 직접 빌드하고 싶다면:

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/pip install pyinstaller
.venv-desktop/bin/pyinstaller --clean --noconfirm ai-subscription-usage.spec
```

macOS 빌드는 `dist/AI Subscription Usage.app`에, Windows 빌드는 `dist/AI Subscription Usage.exe`에 생성됩니다.

## 현재까지 검증된 사항

| 플랫폼 | macOS(데스크톱 + CLI) | Windows(데스크톱 + CLI) |
| --- | --- | --- |
| ChatGPT | ✅ 작동 확인됨 | 🟡 코드 경로는 동일하여 작동할 것으로 예상되나, 실제 Windows에서는 미검증 |
| Claude | ✅ 작동 확인됨(데스크톱과 CLI가 동일한 로그를 공유) | 🟡 데스크톱은 전용 Windows 경로가 있고 CLI도 작동할 것으로 예상되나 미검증 |
| Gemini CLI | ✅ 작동 확인됨 | 🟡 작동할 것으로 예상되나 미검증 |
| Gemini Desktop(Antigravity/Spark) | ❌ 불가능함을 확인함 | ❌ 동일 제품이라 마찬가지로 불가능할 가능성이 높음 — 개별 확인은 안 됨 |
| Grok | 🟡 코드는 맞을 것으로 보이나, 이 기기에는 검증할 실제 Grok 데이터가 없음 | 🟡 마찬가지로 미검증이며 Windows 테스트도 이루어지지 않음 |

Gemini Desktop(Antigravity/Spark)은 로컬 세션 기록을 암호화된 파일(`~/.gemini/antigravity/conversations/*.pb`)로 저장하며, 읽을 수 있는 구조도 없고 안전하게 접근할 수 있는 공개 로컬 API도 없어 토큰 사용량을 읽어올 수 없습니다 — 감지는 되지만 가격은 계산되지 않습니다.

Windows 기기를 가지고 계시거나 실제로 Grok을 사용하신다면 테스트와 피드백을 특히 환영합니다 — 이 두 가지는 저희가 직접 검증할 수 없는 부분입니다. 문제가 있다면 [Issue](../../issues)를 열어 알려주세요.

## 개요

버전 번호는 트레이 메뉴, 리포트 페이지, 도움말 페이지에 표시됩니다. macOS는 사용자 데이터를 `~/Library/Application Support/AI Subscription Usage/`에, Windows는 `%LOCALAPPDATA%\AI Subscription Usage\`에 저장합니다. 업그레이드 시에는 프로그램 본체, 내장 가격 데이터베이스, 언어 파일, 어댑터만 교체됩니다 — 구독 플랜, 데이터 소스 설정, 언어 선택, 진단 동의 여부, 로컬 리포트는 설치 프로그램에 의해 절대 덮어써지지 않습니다. 설정을 마이그레이션하기 전에 원본 파일은 사용자 데이터 디렉터리의 `backups/`에 백업됩니다.

공개되는 GitHub 릴리스에는 구독 플랜, 감지 결과, 로컬 절대 경로, 토큰 수, 생성된 리포트가 포함되지 않습니다 — 감지 결과는 앱이 설치된 기기에서 그때그때 실시간으로 생성됩니다. 릴리스 워크플로는 먼저 `scripts/privacy_check.py`를 실행하며, 실패하면 빌드를 중단합니다.

## 데이터 소스

| 플랫폼 | 로컬 폴더 | 집계 대상 |
| --- | --- | --- |
| ChatGPT | `~/.codex/sessions/` | 내부 Codex JSONL; 입력, 출력, 캐시 입력 |
| Claude Code | `~/.claude/projects/` | 입력, 출력, 캐시 읽기, 캐시 쓰기 |
| Claude Desktop | `~/Library/Application Support/Claude/local-agent-mode-sessions/` | 데스크톱 세션을 감지; 토큰 사용량은 공유되는 Claude JSONL 로그를 통해 집계 |
| Gemini CLI | `~/.gemini/tmp/*/chats/` | 입력, 출력, 사고(thinking), 캐시 토큰 |
| Antigravity Desktop | `~/.gemini/antigravity/` | 자동 감지; `.pb` 형식의 토큰 필드가 검증되지 않아 가격 미계산 |
| Antigravity CLI | `~/.gemini/antigravity-cli/` | 자동 감지; 형식이 검증되지 않아 가격 미계산 |
| Grok Build | `~/.grok/logs/unified.jsonl` | 정확한 입력, 출력, 추론, 캐시 토큰을 우선적으로 읽음 |
| Grok Build 대체 소스 | `~/.grok/sessions/**/signals.json` | `unified.jsonl`이 없을 때만 사용되며 추정치로 표시됨 |

모델 이름은 `config/pricing.json`과 정확히 일치해야 합니다. 알 수 없는 모델도 토큰은 계속 집계되지만 API 환산 가치는 계산되지 않으며, 다른 모델의 가격이 대신 적용되지도 않습니다. 가격 데이터베이스는 적용일별로 다른 가격을 저장할 수 있으며, 과거 기록에는 해당 날짜에 실제로 적용되던 가격이 사용됩니다.

## 명령줄에서 생성하기

```bash
python3 src/ai_usage_report.py --days 30
```

결과는 `outputs/ai-usage-report.html`에 저장됩니다. 우측 상단의 "Refresh local data" 버튼은 데스크톱 앱이 `127.0.0.1:17653`에서 제공하는 로컬 갱신 엔드포인트에 연결됩니다. 이 포트는 루프백에만 바인딩되며 LAN이나 인터넷에는 절대 노출되지 않습니다.

## macOS 메뉴바와 Windows 트레이

데스크톱 앱은 리포트 열기, 지금 새로고침, 모델 가격 업데이트, 앱 업데이트 확인, 언어 전환, 설정 및 사용 안내, 익명 진단 켜기/끄기, 종료 기능을 제공합니다. 처음 실행하면 자동으로 설정 및 사용 안내가 열리며, 로컬 데이터 소스의 감지 상태, 진단 명령어, 그리고 자신의 로컬 AI 어시스턴트에 그대로 복사해 사용할 수 있는 안전한 설정 프롬프트가 표시됩니다. 기본적으로 24시간마다 로컬 데이터를 새로고침하고 앱 버전을 확인합니다.

## 자동 탐지 및 AI 지원 설정

이 앱은 등록된 기본 폴더만 확인하며, 디스크 전체를 스캔하지 않습니다. `AI Subscription Usage --doctor --json`을 실행하면 ChatGPT, Claude Desktop, Claude Code, Gemini CLI, Antigravity Desktop, Antigravity CLI, Grok의 감지 상태를 확인할 수 있습니다. 기본 위치가 아닌 폴더는 제어된 명령어로 설정합니다:

```bash
AI\ Subscription\ Usage --configure-source --provider chatgpt --surface chatgpt-desktop --format codex-jsonl --path "$HOME/.codex/sessions"
AI\ Subscription\ Usage --verify-sources --json
```

`SETUP_WITH_AI.md`는 사용자 자신의 ChatGPT, Claude Code, Gemini CLI, 또는 다른 로컬 AI 어시스턴트에게 전달할 수 있습니다 — 실행 가능한 것은 위의 읽기 전용 진단 명령어와 제어된 설정 명령어뿐입니다. 설정 파일은 명령어, 네트워크 주소, 자격 증명, 임의의 파싱 코드를 절대 허용하지 않습니다.

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/pip install -r requirements-desktop.txt
.venv-desktop/bin/python src/desktop_app.py
```

데스크톱 앱은 장시간 실행되는 메뉴바/트레이 프로세스입니다. 실행하기 전에 다른 프로그램이 `17653` 포트를 사용하고 있지 않은지 확인하세요. 메뉴에서 종료하면 트레이 아이콘과 로컬 갱신 엔드포인트가 모두 함께 종료됩니다.

## 다국어 지원

데스크톱 셸에는 영어, 프랑스어, 독일어, 스페인어, 중국어 간체, 일본어, 한국어 리소스가 포함되어 있습니다. 기본적으로 운영체제 언어를 따르며, 설정 페이지에서 직접 전환할 수도 있습니다. 언어가 바뀌어도 계산되는 값이나 가격 데이터는 변하지 않습니다.

## 가격 데이터베이스 업데이트

`config/pricing.json`에는 가격 버전, 공식 출처, 모델별 가격, 적용일이 저장되어 있습니다. 클라이언트는 매니페스트에서 가격 업데이트를 다운로드하고, SHA-256 체크섬과 필드 구조를 검증한 뒤 로컬 가격 데이터베이스를 원자적으로 교체합니다. 이 도구는 완벽하게 정확한 가격 기준이 아니라 전반적인 추세를 보여주기 위한 것이므로, 업데이트 소스로는 [OpenRouter](https://openrouter.ai/)의 공개 API 가격 데이터를 사용합니다 — OpenRouter는 잘 알려진 LLM 프록시로, API 가격이 대체로 공식 요금을 따라갑니다.

`config/model_id_map.json`은 이 프로젝트의 로컬 모델 이름을 OpenRouter의 정확한 모델 ID에 매핑합니다. `scripts/fetch_pricing.py`는 이 매핑을 사용해 현재 가격을 가져와 `config/pricing.json`과 `config/pricing-manifest.json`을 다시 작성합니다. `.github/workflows/update-pricing.yml`은 이를 약 주 1회 자동으로 실행하며, 실제로 가격이 변경된 경우에만 커밋합니다. 실제 가격 변동은 날짜가 지정된 새로운 구간으로 기록되므로, 과거 리포트 날짜는 그 당시 실제로 적용되던 요금을 계속 사용합니다. 이미 수동으로 날짜별 스케줄이 지정된 모델은 이 자동화의 대상에서 제외됩니다. 사용 기록에 아직 매핑되지 않은 완전히 새로운 모델 이름이 나타나면, `config/model_id_map.json`에 한 줄이 추가될 때까지 단순히 미가격 상태로 표시됩니다 — 데스크톱 앱은 새 모델을 감지하는 즉시 현장에서 가격 갱신도 시도합니다.

각 서비스의 상세 탭에는 해당 기간의 캐시 명중률과, 동일한 사용량을 [DeepSeek](https://www.deepseek.com/)에서 실행했을 때의 예상 비용도 표시됩니다. 각 모델은 성능 등급에 따라 DeepSeek V4의 Flash 또는 Pro 등급에 대응되며(대응 관계는 `config/deepseek_tier_map.json` 참고), DeepSeek 자체의 공개 가격(마찬가지로 OpenRouter를 통해 최신 상태로 유지됨)과 이 기간의 실제 캐시 명중/미스 비율을 사용합니다 — 추정한 비율이 아닙니다. DeepSeek에 실제로 대응되는 등급이 없는 플래그십 모델도 의도적으로 DeepSeek에 유리하게 Pro와 비교되므로, 이 비교가 과장되는 일은 없습니다.

## 익명 진단

익명 진단은 기본적으로 꺼져 있으며, 설정에서 명시적으로 켠 경우에만 업로드됩니다. 허용되는 필드는 앱 버전, OS, 언어, 오류 모듈, 오류 유형, 비식별화된 스택 트레이스, 어댑터 상태로 제한됩니다. 대화 내용, 프롬프트, 응답, 사용자 이름, 로컬 파일 경로, API 키, 구독 정보, 토큰 세부 내역, 원본 로그는 절대 업로드되지 않습니다. `telemetry_endpoint`는 진단 수신 서버가 공개되는 시점에 채워질 예정입니다.

## 자동 릴리스

`.github/workflows/release.yml`은 버전 태그가 푸시된 후 테스트를 실행하고, macOS와 Windows 빌드 산출물을 생성하고, SHA-256 체크섬을 만들고, GitHub Release를 생성합니다. 완전 자동 업데이트를 위해서는 추가로 GitHub 저장소 주소, macOS Developer ID, 공증 자격 증명, Windows 코드 서명 인증서가 필요합니다.

## 라이선스

이 프로젝트는 [PolyForm Noncommercial 1.0.0](LICENSE) 라이선스로 배포됩니다 — 비상업적 목적이라면 자유롭게 사용, 학습, 수정, 공유할 수 있습니다. 상업적 이용은 허용되지 않습니다. 라이선스나 특정 사용 사례에 대해 궁금한 점이 있다면 [Issue](../../issues)를 열어주세요. 타사 코드를 재사용할 경우에도 해당 라이선스, 저작권 표시, 출처를 `THIRD_PARTY_NOTICES.md`에 기록해야 합니다.
