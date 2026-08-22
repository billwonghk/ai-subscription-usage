"""Localized configuration guide; technical prompt and commands stay English."""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

from favicon import FAVICON_TAG, LOGO_IMG
from source_discovery import doctor_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRICING = PROJECT_ROOT / "config" / "pricing.json"
DEFAULT_DEEPSEEK_TIER_MAP = PROJECT_ROOT / "config" / "deepseek_tier_map.json"


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


EN = {
    "title": "AI Subscription Usage: Configuration and User Guide", "intro": "This tool reads local AI usage records and calculates the last 30 days of API-equivalent value, subscription cost, and value multiple. No AI API is required.",
    "start": "First use", "start_body": "Choose Refresh now. The app checks known local directories and reports missing records, permissions, or unsupported formats.",
    "sources": "Data sources", "sources_body": "ChatGPT uses internal Codex JSONL; Claude uses Claude JSONL; Gemini CLI uses chat JSON. Antigravity and Grok are detected separately.",
    "ai": "Configure with your local AI", "ai_body": "Give the English setup prompt below to a local AI. It may only run read-only diagnostics and validated configuration commands.",
    "security": "Security boundary", "security_body": "OAuth, auth tokens, cookies, Keychain, and conversation content are never read.",
    "pricing": "Pricing and calculation", "pricing_body": "Regular input, cache reads, cache writes, and output use separate rates. Unknown models remain unpriced. Prices for supported models are refreshed automatically from OpenRouter's public API pricing data. Each provider's detail tab also shows its cache-hit rate and an estimated cost if the same usage ran on DeepSeek, matched by capability tier.",
    "trouble": "Troubleshooting", "trouble_body": "Run the doctor when data is missing. Each source reports an explicit status.",
    "commands": "Diagnostic and configuration commands", "detection": "Current detection", "detection_note": "This table is generated on this computer and stays in the current user's data directory. It is not included in public release packages.",
    "provider": "Provider", "surface": "Surface", "status": "Status", "files": "Record files", "prompt": "Prompt for your local AI", "version": "Version",
    "deepseek": "DeepSeek comparison method", "deepseek_body": "Cache-hit rate and the DeepSeek comparison cost both use the last 30 days of real usage. Each local model is matched to a DeepSeek V4 tier (Flash or Pro) by measured capability, not by price or product name — using the Artificial Analysis Intelligence Index (a composite of reasoning, knowledge, math, and coding, not a single coding-only score), snapshot taken 2026-08-21, where DeepSeek V4 Flash scored 51.8 and Pro scored 53.2; a local model scoring at or above that line is matched to Pro, below it to Flash. Prices are DeepSeek's own public rates in USD, kept current via OpenRouter and shown below as currently in effect. The cache-hit/miss split uses this period's real cache data, not a guessed ratio. Flagship models with no real DeepSeek equivalent are still compared against Pro, deliberately in DeepSeek's favor.",
    "deepseek_tier_table": "DeepSeek tier pricing (USD per million tokens)", "deepseek_tier_col": "Tier", "deepseek_input_col": "Input", "deepseek_cached_col": "Cache hit", "deepseek_output_col": "Output",
    "deepseek_map_table": "Local model → DeepSeek tier", "deepseek_model_col": "Local model",
    "model_pricing": "Current model pricing", "model_pricing_body": "The rates behind the API-equivalent value above, straight from the local pricing database — kept current the same way as the DeepSeek rates below, via OpenRouter, about once a week.",
}

TEXT = {
    "en": EN,
    "zh-CN": {**EN, "title":"AI 订阅用量：配置及使用说明", "intro":"本工具读取本机 AI 用量记录，计算最近 30 天 API 等价价值、订阅成本和价值倍数。计算不需要 AI API。", "start":"首次使用", "start_body":"打开应用后选择“立即更新”。程序检查已知本机目录，并明确显示没有记录、权限不足或格式不支持。", "sources":"数据来源", "sources_body":"ChatGPT 使用内部 Codex JSONL；Claude 使用 Claude JSONL；Gemini CLI 使用聊天 JSON。Antigravity 和 Grok 单独检测。", "ai":"使用本机 AI 帮助配置", "ai_body":"把下方英文配置提示词交给本机 AI。AI 只能执行只读诊断和经过校验的配置命令。", "security":"安全边界", "security_body":"程序不读取 OAuth、Auth Token、Cookie、钥匙串或对话正文。", "pricing":"价格与计算", "pricing_body":"普通输入、缓存读取、缓存写入和输出分别使用对应单价。未知模型不计算金额。已支持模型的价格会自动从 OpenRouter 的公开 API 价格数据更新。每个平台的详情标签页还会显示缓存命中率，以及按能力对应到 DeepSeek 档位后估算出的成本。", "trouble":"故障排查", "trouble_body":"缺少数据时运行诊断，每个数据源都会显示明确状态。", "commands":"诊断与配置命令", "detection":"本机检测结果", "detection_note":"此表在当前电脑上实时生成，只保存在当前用户的数据目录中，不会包含在通用发布包中。", "provider":"平台", "surface":"使用端", "status":"状态", "files":"记录文件", "prompt":"复制给本机 AI 的配置提示词", "version":"版本",
     "deepseek":"DeepSeek 对比方法", "deepseek_body":"缓存命中率和 DeepSeek 对比成本，用的都是最近 30 天的真实用量。每个本机模型对应到 DeepSeek V4 的 Flash 还是 Pro 档位，看的是实测能力，不是价格也不是产品名字——用的是 Artificial Analysis Intelligence Index 这个综合指数（推理、知识、数学、编程都算在内，不是只看编程一项），取的是 2026-08-21 这一天的快照，那天 DeepSeek V4 Flash 得分 51.8，Pro 得分 53.2；本机模型得分达到或超过这条线的对应 Pro，低于的对应 Flash。价格是 DeepSeek 自己的公开报价（美元），通过 OpenRouter 自动更新，下表显示的是当前生效的价格。命中/未命中的比例，用的是这段时间真实的缓存数据，不是猜的比例。DeepSeek 没有真正对应档位的旗舰模型，也按 Pro 档位计算，故意往 DeepSeek 那边让一步。",
     "deepseek_tier_table":"DeepSeek 档位价格（美元/百万 Token）", "deepseek_tier_col":"档位", "deepseek_input_col":"输入", "deepseek_cached_col":"缓存命中", "deepseek_output_col":"输出",
     "deepseek_map_table":"本机模型 → DeepSeek 档位对应关系", "deepseek_model_col":"本机模型",
     "model_pricing":"当前模型单价", "model_pricing_body":"上面“API 等价价值”用的就是这些单价，直接读自本机价格库——跟下面 DeepSeek 那两档一样，也是通过 OpenRouter 大约每周自动更新一次。"},
    "ja": {**EN, "title":"AIサブスクリプション使用量：設定・使用ガイド", "intro":"ローカルAI使用記録から直近30日間のAPI相当額、費用、価値倍率を計算します。AI APIは不要です。", "start":"初回使用", "start_body":"「今すぐ更新」を選択すると既知のローカルフォルダと状態を確認します。", "sources":"データソース", "sources_body":"ChatGPTはCodex JSONL、ClaudeはClaude JSONL、Gemini CLIはチャットJSONを使用します。AntigravityとGrokは別に検出します。", "ai":"ローカルAIによる設定", "ai_body":"下の英語プロンプトをローカルAIに渡します。読み取り専用診断と検証済み設定だけを実行できます。", "security":"セキュリティ境界", "security_body":"OAuth、Auth Token、Cookie、キーチェーン、会話本文は読み取りません。", "pricing":"価格と計算", "pricing_body":"通常入力、キャッシュ読み取り、キャッシュ書き込み、出力を別々の単価で計算します。対応モデルの価格は OpenRouter の公開 API 価格データから自動的に更新されます。各サービスの詳細タブには、キャッシュ命中率と、能力に応じて DeepSeek の対応ランクで見積もったコストも表示されます。", "trouble":"トラブルシューティング", "trouble_body":"データがない場合は診断を実行し、各ソースの状態を確認します。", "commands":"診断・設定コマンド", "detection":"現在の検出結果", "detection_note":"この表は現在の端末で生成され、ユーザーのデータフォルダだけに保存されます。公開パッケージには含まれません。", "provider":"サービス", "surface":"利用形態", "status":"状態", "files":"記録ファイル", "prompt":"ローカルAIに渡すプロンプト", "version":"バージョン",
     "deepseek":"DeepSeek 比較方法", "deepseek_body":"キャッシュ命中率と DeepSeek 比較コストは、いずれも直近30日間の実際の使用量を使用します。各ローカルモデルを DeepSeek V4 の Flash または Pro のどちらに対応させるかは、価格や製品名ではなく実測の能力で判断しています——Artificial Analysis Intelligence Index（推論・知識・数学・コーディングを総合したスコアで、コーディング単体の評価ではありません）の2026-08-21時点のスナップショットを使用し、その時点で DeepSeek V4 Flash は51.8点、Pro は53.2点でした。この基準以上のローカルモデルは Pro に、それ未満は Flash に対応させています。価格は DeepSeek 自身の公開料金（米ドル）で、OpenRouter 経由で自動更新され、下表には現在有効な価格を表示しています。キャッシュ命中/未命中の比率は、この期間の実際のキャッシュデータを使用しており、推定値ではありません。DeepSeek に本当に対応するランクがないフラッグシップモデルも、あえて DeepSeek 側に有利になるよう Pro と比較されます。",
     "deepseek_tier_table":"DeepSeek ランク別価格（米ドル/百万トークン）", "deepseek_tier_col":"ランク", "deepseek_input_col":"入力", "deepseek_cached_col":"キャッシュ命中", "deepseek_output_col":"出力",
     "deepseek_map_table":"ローカルモデル → DeepSeek ランク対応表", "deepseek_model_col":"ローカルモデル",
     "model_pricing":"現在のモデル単価", "model_pricing_body":"上記の「API相当額」はこの単価をもとに計算しています。ローカルの価格データベースから直接取得しており、下記の DeepSeek の価格と同様に OpenRouter 経由で約1週間ごとに自動更新されます。"},
    "ko": {**EN, "title":"AI 구독 사용량: 구성 및 사용 안내", "intro":"로컬 AI 사용 기록으로 최근 30일 API 환산 가치, 구독 비용 및 가치 배수를 계산합니다. AI API는 필요하지 않습니다.", "start":"처음 사용", "start_body":"‘지금 업데이트’를 선택하면 알려진 로컬 폴더와 상태를 확인합니다.", "sources":"데이터 소스", "sources_body":"ChatGPT는 Codex JSONL, Claude는 Claude JSONL, Gemini CLI는 채팅 JSON을 사용합니다. Antigravity와 Grok은 별도로 감지합니다.", "ai":"로컬 AI로 구성", "ai_body":"아래 영어 프롬프트를 로컬 AI에 전달합니다. 읽기 전용 진단과 검증된 구성만 실행할 수 있습니다.", "security":"보안 범위", "security_body":"OAuth, Auth Token, Cookie, 키체인 또는 대화 본문을 읽지 않습니다.", "pricing":"가격 및 계산", "pricing_body":"일반 입력, 캐시 읽기, 캐시 쓰기 및 출력은 각각의 단가로 계산합니다. 지원되는 모델의 가격은 OpenRouter의 공개 API 가격 데이터에서 자동으로 업데이트됩니다. 각 서비스의 상세 탭에는 캐시 명중률과, 성능에 따라 대응되는 DeepSeek 등급으로 추정한 비용도 표시됩니다.", "trouble":"문제 해결", "trouble_body":"데이터가 없으면 진단을 실행하여 각 소스의 상태를 확인합니다.", "commands":"진단 및 구성 명령", "detection":"현재 감지 결과", "detection_note":"이 표는 현재 컴퓨터에서 생성되어 사용자 데이터 폴더에만 저장됩니다. 공개 패키지에는 포함되지 않습니다.", "provider":"서비스", "surface":"사용 환경", "status":"상태", "files":"기록 파일", "prompt":"로컬 AI에 전달할 프롬프트", "version":"버전",
     "deepseek":"DeepSeek 비교 방법", "deepseek_body":"캐시 명중률과 DeepSeek 비교 비용은 모두 최근 30일간의 실제 사용량을 사용합니다. 각 로컬 모델을 DeepSeek V4의 Flash 또는 Pro 중 어디에 대응시킬지는 가격이나 제품명이 아니라 실측 성능으로 판단합니다——Artificial Analysis Intelligence Index(추론·지식·수학·코딩을 종합한 지수이며 코딩 단일 점수가 아닙니다)의 2026-08-21 스냅샷을 기준으로, 그 시점에 DeepSeek V4 Flash는 51.8점, Pro는 53.2점을 기록했습니다. 이 기준 이상인 로컬 모델은 Pro에, 미만인 모델은 Flash에 대응시킵니다. 가격은 DeepSeek 자체의 공개 요금(미국 달러)이며 OpenRouter를 통해 자동으로 최신 상태로 유지되고, 아래 표는 현재 적용 중인 가격을 표시합니다. 캐시 명중/미스 비율은 이 기간의 실제 캐시 데이터를 사용했으며, 추정치가 아닙니다. DeepSeek에 실제로 대응되는 등급이 없는 플래그십 모델도 의도적으로 DeepSeek에 유리하게 Pro와 비교됩니다.",
     "deepseek_tier_table":"DeepSeek 등급별 가격 (백만 토큰당 미국 달러)", "deepseek_tier_col":"등급", "deepseek_input_col":"입력", "deepseek_cached_col":"캐시 명중", "deepseek_output_col":"출력",
     "deepseek_map_table":"로컬 모델 → DeepSeek 등급 대응표", "deepseek_model_col":"로컬 모델",
     "model_pricing":"현재 모델 단가", "model_pricing_body":"위의 “API 환산 가치”는 이 단가를 기준으로 계산됩니다. 로컬 가격 데이터베이스에서 직접 가져오며, 아래 DeepSeek 가격과 마찬가지로 OpenRouter를 통해 약 주 1회 자동으로 업데이트됩니다."},
    "fr": {**EN, "title":"Utilisation des abonnements IA : configuration et guide", "intro":"Cet outil calcule sur 30 jours la valeur API, le coût et le multiple à partir des journaux locaux. Aucune API d’IA n’est requise.", "start":"Première utilisation", "start_body":"Choisissez Actualiser pour vérifier les dossiers et leur état.", "sources":"Sources de données", "sources_body":"ChatGPT utilise Codex JSONL, Claude utilise Claude JSONL et Gemini CLI utilise le JSON de conversation. Antigravity et Grok sont détectés séparément.", "ai":"Configurer avec votre IA locale", "ai_body":"Donnez l’invite anglaise ci-dessous à votre IA locale. Seuls le diagnostic en lecture seule et la configuration validée sont autorisés.", "security":"Limites de sécurité", "security_body":"OAuth, Auth Token, cookies, Trousseau et contenu des conversations ne sont jamais lus.", "pricing":"Tarifs et calcul", "pricing_body":"Entrées normales, lectures de cache, écritures de cache et sorties utilisent des tarifs distincts. Les tarifs des modèles pris en charge sont mis à jour automatiquement à partir des données de prix API publiques d’OpenRouter. L’onglet de détail de chaque fournisseur affiche aussi son taux de succès du cache et un coût estimé si le même usage tournait sur DeepSeek, selon le niveau de capacité correspondant.", "trouble":"Dépannage", "trouble_body":"Exécutez le diagnostic et consultez l’état de chaque source.", "commands":"Commandes de diagnostic et de configuration", "detection":"Détection actuelle", "detection_note":"Ce tableau est généré sur cet ordinateur et reste dans le dossier de données de l’utilisateur. Il n’est pas inclus dans les versions publiques.", "provider":"Fournisseur", "surface":"Interface", "status":"État", "files":"Fichiers de données", "prompt":"Invite pour votre IA locale", "version":"Version",
     "deepseek":"Méthode de comparaison DeepSeek", "deepseek_body":"Le taux de succès du cache et le coût de comparaison DeepSeek utilisent tous deux les 30 derniers jours d'utilisation réelle. Le niveau DeepSeek V4 (Flash ou Pro) associé à chaque modèle local est déterminé par sa capacité mesurée, pas par son prix ni son nom commercial — à partir de l'Artificial Analysis Intelligence Index (un score composite de raisonnement, de connaissances, de mathématiques et de code, pas un score de code seul), instantané pris le 2026-08-21, où DeepSeek V4 Flash obtenait 51,8 et Pro 53,2 ; un modèle local atteignant ou dépassant ce seuil est associé à Pro, en dessous à Flash. Les tarifs sont ceux publiés par DeepSeek lui-même (en USD), tenus à jour via OpenRouter, et le tableau ci-dessous affiche les tarifs actuellement en vigueur. La répartition succès/échec du cache utilise les données réelles de cette période, pas un ratio estimé. Les modèles haut de gamme sans véritable équivalent chez DeepSeek sont tout de même comparés au niveau Pro, délibérément en faveur de DeepSeek.",
     "deepseek_tier_table":"Tarifs par niveau DeepSeek (USD par million de jetons)", "deepseek_tier_col":"Niveau", "deepseek_input_col":"Entrée", "deepseek_cached_col":"Succès du cache", "deepseek_output_col":"Sortie",
     "deepseek_map_table":"Modèle local → niveau DeepSeek", "deepseek_model_col":"Modèle local",
     "model_pricing":"Tarifs actuels des modèles", "model_pricing_body":"Les tarifs derrière la « valeur API équivalente » ci-dessus, tirés directement de la base de données tarifaires locale — tenus à jour de la même façon que les tarifs DeepSeek ci-dessous, via OpenRouter, environ une fois par semaine."},
    "de": {**EN, "title":"KI-Abonnementnutzung: Konfiguration und Anleitung", "intro":"Dieses Tool berechnet aus lokalen Protokollen den API-Gegenwert, die Abokosten und den Wertfaktor der letzten 30 Tage. Keine KI-API ist nötig.", "start":"Erste Verwendung", "start_body":"Jetzt aktualisieren prüft bekannte Ordner und deren Status.", "sources":"Datenquellen", "sources_body":"ChatGPT nutzt Codex JSONL, Claude nutzt Claude JSONL und Gemini CLI nutzt Chat-JSON. Antigravity und Grok werden getrennt erkannt.", "ai":"Mit lokaler KI konfigurieren", "ai_body":"Geben Sie den englischen Prompt unten an Ihre lokale KI. Nur Lesediagnose und validierte Konfiguration sind erlaubt.", "security":"Sicherheitsgrenze", "security_body":"OAuth, Auth Token, Cookies, Schlüsselbund und Gesprächsinhalte werden nie gelesen.", "pricing":"Preise und Berechnung", "pricing_body":"Normale Eingabe, Cache-Lesen, Cache-Schreiben und Ausgabe werden getrennt berechnet. Preise für unterstützte Modelle werden automatisch anhand der öffentlichen API-Preisdaten von OpenRouter aktualisiert. Der Detailtab jedes Anbieters zeigt außerdem die Cache-Trefferquote und geschätzte Kosten, falls dieselbe Nutzung auf DeepSeek liefe, passend zur Leistungsstufe.", "trouble":"Fehlerbehebung", "trouble_body":"Führen Sie die Diagnose aus und prüfen Sie den Status jeder Quelle.", "commands":"Diagnose- und Konfigurationsbefehle", "detection":"Aktuelle Erkennung", "detection_note":"Diese Tabelle wird auf diesem Computer erzeugt und nur im Benutzerdatenordner gespeichert. Öffentliche Pakete enthalten sie nicht.", "provider":"Anbieter", "surface":"Oberfläche", "status":"Status", "files":"Datendateien", "prompt":"Prompt für Ihre lokale KI", "version":"Version",
     "deepseek":"DeepSeek-Vergleichsmethode", "deepseek_body":"Sowohl die Cache-Trefferquote als auch die DeepSeek-Vergleichskosten basieren auf der echten Nutzung der letzten 30 Tage. Welcher DeepSeek-V4-Stufe (Flash oder Pro) ein lokales Modell zugeordnet wird, richtet sich nach der gemessenen Leistungsfähigkeit, nicht nach Preis oder Produktname — anhand des Artificial Analysis Intelligence Index (ein Gesamtwert aus Schlussfolgern, Wissen, Mathematik und Code, kein reiner Code-Wert), Stand 2026-08-21: DeepSeek V4 Flash erreichte damals 51,8 Punkte, Pro 53,2 Punkte; ein lokales Modell mit diesem Wert oder darüber wird Pro zugeordnet, darunter Flash. Die Preise sind DeepSeeks eigene öffentliche Preise (in USD), über OpenRouter aktuell gehalten, die Tabelle unten zeigt die derzeit gültigen Preise. Der Anteil an Cache-Treffern/-Fehlern basiert auf den echten Cache-Daten dieses Zeitraums, nicht auf einer geschätzten Quote. Flaggschiff-Modelle ohne echtes DeepSeek-Gegenstück werden trotzdem mit Pro verglichen, bewusst zugunsten von DeepSeek.",
     "deepseek_tier_table":"DeepSeek-Preise nach Stufe (USD pro Million Token)", "deepseek_tier_col":"Stufe", "deepseek_input_col":"Eingabe", "deepseek_cached_col":"Cache-Treffer", "deepseek_output_col":"Ausgabe",
     "deepseek_map_table":"Lokales Modell → DeepSeek-Stufe", "deepseek_model_col":"Lokales Modell",
     "model_pricing":"Aktuelle Modellpreise", "model_pricing_body":"Die Preise hinter dem oben genannten API-Gegenwert, direkt aus der lokalen Preisdatenbank — genauso aktuell gehalten wie die DeepSeek-Preise unten, über OpenRouter, etwa einmal pro Woche."},
    "es": {**EN, "title":"Uso de suscripciones de IA: configuración y guía", "intro":"Esta herramienta calcula durante 30 días el valor API, el coste y el múltiplo mediante registros locales. No necesita una API de IA.", "start":"Primer uso", "start_body":"Actualizar ahora revisa directorios conocidos y su estado.", "sources":"Fuentes de datos", "sources_body":"ChatGPT usa Codex JSONL, Claude usa Claude JSONL y Gemini CLI usa JSON de chat. Antigravity y Grok se detectan por separado.", "ai":"Configurar con su IA local", "ai_body":"Entregue el prompt en inglés siguiente a su IA local. Solo se permiten diagnóstico de lectura y configuración validada.", "security":"Límite de seguridad", "security_body":"Nunca se leen OAuth, Auth Token, cookies, Llavero ni contenido de conversaciones.", "pricing":"Precios y cálculo", "pricing_body":"Entrada normal, lectura de caché, escritura de caché y salida usan precios separados. Los precios de los modelos compatibles se actualizan automáticamente con los datos públicos de precios de la API de OpenRouter. La pestaña de detalle de cada proveedor también muestra su tasa de aciertos de caché y un coste estimado si el mismo uso se ejecutara en DeepSeek, según el nivel de capacidad correspondiente.", "trouble":"Solución de problemas", "trouble_body":"Ejecute el diagnóstico y consulte el estado de cada fuente.", "commands":"Comandos de diagnóstico y configuración", "detection":"Detección actual", "detection_note":"Esta tabla se genera en este equipo y solo se guarda en la carpeta de datos del usuario. No se incluye en paquetes públicos.", "provider":"Proveedor", "surface":"Interfaz", "status":"Estado", "files":"Archivos de datos", "prompt":"Prompt para su IA local", "version":"Versión",
     "deepseek":"Método de comparación con DeepSeek", "deepseek_body":"Tanto la tasa de aciertos de caché como el coste de comparación con DeepSeek usan los últimos 30 días de uso real. El nivel DeepSeek V4 (Flash o Pro) asignado a cada modelo local se determina por su capacidad medida, no por su precio ni su nombre comercial — usando el Artificial Analysis Intelligence Index (una puntuación compuesta de razonamiento, conocimiento, matemáticas y código, no solo código), instantánea tomada el 2026-08-21, en la que DeepSeek V4 Flash obtuvo 51,8 puntos y Pro 53,2; un modelo local que alcance o supere esa cifra se asigna a Pro, por debajo a Flash. Los precios son los propios precios públicos de DeepSeek (en USD), mantenidos al día mediante OpenRouter, y la tabla siguiente muestra los precios actualmente vigentes. La proporción de aciertos/fallos de caché usa los datos reales de caché de ese período, no una proporción estimada. Los modelos insignia sin un equivalente real en DeepSeek también se comparan con el nivel Pro, deliberadamente a favor de DeepSeek.",
     "deepseek_tier_table":"Precios por nivel de DeepSeek (USD por millón de tokens)", "deepseek_tier_col":"Nivel", "deepseek_input_col":"Entrada", "deepseek_cached_col":"Acierto de caché", "deepseek_output_col":"Salida",
     "deepseek_map_table":"Modelo local → nivel DeepSeek", "deepseek_model_col":"Modelo local",
     "model_pricing":"Precios actuales de los modelos", "model_pricing_body":"Los precios detrás del “valor equivalente en API” de arriba, tomados directamente de la base de datos de precios local — mantenidos al día igual que los precios de DeepSeek de abajo, mediante OpenRouter, aproximadamente una vez por semana."},
}

AI_PROMPT = "Read the configuration guide for AI Subscription Usage. Run the bundled application with --doctor --json. Do not read OAuth, auth tokens, cookies, Keychain, or conversation content. Do not modify any AI client. If a known source exists outside its default path, use --configure-source with an allowed provider, surface, format, and existing read-only directory. Finish with --verify-sources --json and report only statuses, formats, and file counts."
COMMANDS = "AI Subscription Usage --doctor --json\nAI Subscription Usage --configure-source --provider PROVIDER --surface SURFACE --format FORMAT --path DIRECTORY\nAI Subscription Usage --verify-sources --json\nAI Subscription Usage --refresh"


def render_help(
    language: str,
    app_version: str = "development",
    pricing: dict | None = None,
    deepseek_tiers: dict[str, str] | None = None,
) -> str:
    t = TEXT.get(language, EN)
    if pricing is None:
        pricing = _load_json(DEFAULT_PRICING)
    if deepseek_tiers is None:
        raw_tiers = _load_json(DEFAULT_DEEPSEEK_TIER_MAP)
        deepseek_tiers = {key: value for key, value in raw_tiers.items() if not key.startswith("_")}
    rows = "".join(f"<tr><td>{html.escape(x['label'])}</td><td>{html.escape(x['surface'])}</td><td>{html.escape(x['status'])}</td><td>{x['matching_files']}</td></tr>" for x in doctor_report()["discovered_sources"])
    sections = "".join(f"<section><h2>{html.escape(t[key])}</h2><p>{html.escape(t[key + '_body'])}</p></section>" for key in ("start", "sources", "ai", "security", "pricing", "trouble"))

    models = pricing.get("models") if isinstance(pricing.get("models"), dict) else {}

    def current_rate(rate: dict) -> dict | None:
        periods = rate.get("periods")
        if not isinstance(periods, list):
            return rate
        today = dt.date.today().isoformat()
        candidates = [p for p in periods if isinstance(p, dict) and str(p.get("start_date", "")) <= today and (not p.get("end_date") or today <= str(p["end_date"]))]
        if not candidates:
            return None
        return sorted(candidates, key=lambda p: str(p.get("start_date", "")))[-1]

    model_price_rows = ""
    for name, rate in sorted(models.items()):
        if name.startswith("deepseek-v4-") or not isinstance(rate, dict):
            continue
        r = current_rate(rate)
        if r is None or "input_per_million" not in r or "output_per_million" not in r:
            continue
        cached = r.get("cached_input_per_million", r["input_per_million"])
        model_price_rows += f"<tr><td>{html.escape(name)}</td><td>${r['input_per_million']}</td><td>${cached}</td><td>${r['output_per_million']}</td></tr>"
    model_pricing_section = (
        f"<section><h2>{html.escape(t['model_pricing'])}</h2><p>{html.escape(t['model_pricing_body'])}</p>"
        f"<table><thead><tr><th>{html.escape(t['deepseek_model_col'])}</th><th>{html.escape(t['deepseek_input_col'])}</th><th>{html.escape(t['deepseek_cached_col'])}</th><th>{html.escape(t['deepseek_output_col'])}</th></tr></thead><tbody>{model_price_rows}</tbody></table></section>"
    )

    tier_rows = ""
    for tier_key, tier_label in (("flash", "Flash"), ("pro", "Pro")):
        rate = models.get(f"deepseek-v4-{tier_key}")
        if not isinstance(rate, dict):
            continue
        tier_rows += f"<tr><td>DeepSeek V4 {tier_label}</td><td>${rate.get('input_per_million', '—')}</td><td>${rate.get('cached_input_per_million', '—')}</td><td>${rate.get('output_per_million', '—')}</td></tr>"
    map_rows = "".join(
        f"<tr><td>{html.escape(model)}</td><td>DeepSeek V4 {'Pro' if tier == 'pro' else 'Flash'}</td></tr>"
        for model, tier in sorted(deepseek_tiers.items())
    )
    deepseek_section = (
        f"<section><h2>{html.escape(t['deepseek'])}</h2><p>{html.escape(t['deepseek_body'])}</p>"
        f"<h3>{html.escape(t['deepseek_tier_table'])}</h3>"
        f"<table><thead><tr><th>{html.escape(t['deepseek_tier_col'])}</th><th>{html.escape(t['deepseek_input_col'])}</th><th>{html.escape(t['deepseek_cached_col'])}</th><th>{html.escape(t['deepseek_output_col'])}</th></tr></thead><tbody>{tier_rows}</tbody></table>"
        f"<h3>{html.escape(t['deepseek_map_table'])}</h3>"
        f"<table><thead><tr><th>{html.escape(t['deepseek_model_col'])}</th><th>{html.escape(t['deepseek_tier_col'])}</th></tr></thead><tbody>{map_rows}</tbody></table></section>"
    )

    style = ':root{color-scheme:dark;--bg:#080d18;--card:#101a2b;--ink:#ecf5ff;--sub:#a8b7ce;--line:#263854}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:1100px;margin:auto;padding:38px 24px 72px}h1{font-size:30px;margin:0 0 10px;display:flex;align-items:center;gap:12px}.brand-logo{width:34px;height:34px;border-radius:8px;flex:none}h2{font-size:19px;margin:0 0 8px}h3{font-size:14px;margin:18px 0 8px;color:var(--ink)}p{color:var(--sub);line-height:1.7}section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:16px}pre{white-space:pre-wrap;background:#07101d;border:1px solid var(--line);padding:16px;border-radius:10px;color:#d8eaff}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-top:1px solid var(--line);text-align:left}th{color:var(--sub)}.prompt{user-select:all}'
    script = "let v=0;async function sync(){try{let r=await fetch('http://127.0.0.1:17653/state?ts='+Date.now(),{cache:'no-store'});if(!r.ok)return;let s=await r.json();if(v&&s.report_version!==v&&s.language!==document.documentElement.lang)location.replace('http://127.0.0.1:17653/help?ts='+Date.now());v=s.report_version}catch{}}setInterval(sync,1000);sync();"
    return f'''<!doctype html><html lang="{html.escape(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{FAVICON_TAG}<title>{html.escape(t['title'])}</title><style>{style}</style></head><body><main><h1>{LOGO_IMG}{html.escape(t['title'])}</h1><p>{html.escape(t['intro'])} · Ver {html.escape(app_version)}</p>{sections}{model_pricing_section}{deepseek_section}<section><h2>{html.escape(t['commands'])}</h2><pre>{html.escape(COMMANDS)}</pre></section><section><h2>{html.escape(t['detection'])}</h2><p>{html.escape(t['detection_note'])}</p><table><thead><tr><th>{html.escape(t['provider'])}</th><th>{html.escape(t['surface'])}</th><th>{html.escape(t['status'])}</th><th>{html.escape(t['files'])}</th></tr></thead><tbody>{rows}</tbody></table></section><section><h2>{html.escape(t['prompt'])}</h2><pre class="prompt">{html.escape(AI_PROMPT)}</pre></section></main><script>{script}</script></body></html>'''


def write_help(
    path: Path,
    language: str,
    app_version: str = "development",
    pricing: dict | None = None,
    deepseek_tiers: dict[str, str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_help(language, app_version, pricing, deepseek_tiers), encoding="utf-8")
    return path
