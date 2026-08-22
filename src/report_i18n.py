"""Static report localization without changing numeric calculations."""

from __future__ import annotations

import re


ZH = [
    "订阅 AI 用量报表", "最近", "天", "按电脑当前时区分日", "数据来自本机日志", "生成于本机", "更新本机数据",
    "总 Token", "输入 Token", "输出 Token", "API 等价价值", "有效订阅成本", "价值倍数", "订阅计划",
    "平台", "周期", "按月", "按年", "生效日期", "订阅金额（USD）", "保存计划", "报表", "每日 Token",
    "每日订阅价值倍数", "平台详情",
    "未设置", "未计算", "未计价 Token", "读取文件", "模型", "缓存输入", "未公开价格",
    "正在更新…", "更新完成，正在刷新", "本机应用未运行", "无数据", "本机没有可解析记录", "生效", "历史计划",
    "API 价格数据来自 OpenRouter",
]

TRANSLATIONS = {
    "en": ["AI Subscription Usage Report", "Last ", " days", "Grouped by the computer's local timezone", "Data from local logs", "Generated locally", "Refresh local data", "Total tokens", "Input tokens", "Output tokens", "API-equivalent value", "Effective subscription cost", "Value multiple", "Subscription plans", "Provider", "Billing", "Monthly", "Annual", "Effective date", "Subscription amount (USD)", "Save plan", "report", "Daily tokens", "Daily subscription value multiple", "Provider details", "Not set", "Not calculated", "Unpriced tokens", "Files read", "Model", "Cached input", "No public price", "Refreshing…", "Refresh complete; reloading", "Local app is not running", "No data", "No parsable local records", "effective", "plan history", "API pricing data from OpenRouter"],
    "ja": ["AIサブスクリプション使用量レポート", "直近", "日", "端末のタイムゾーンで日別集計", "ローカルログから取得", "ローカルで生成", "ローカルデータを更新", "総Token", "入力Token", "出力Token", "API相当額", "有効なサブスクリプション費用", "価値倍率", "サブスクリプションプラン", "サービス", "周期", "月額", "年額", "適用日", "料金（USD）", "プランを保存", "レポート", "日別Token", "日別サブスクリプション価値倍率", "サービス詳細", "未設定", "未計算", "未評価Token", "読込ファイル", "モデル", "キャッシュ入力", "公開価格なし", "更新中…", "更新完了、再読み込み中", "ローカルアプリが起動していません", "データなし", "解析可能なローカル記録なし", "適用", "プラン履歴", "API 価格データは OpenRouter より取得"],
    "ko": ["AI 구독 사용량 보고서", "최근", "일", "컴퓨터 현지 시간대로 일별 집계", "로컬 로그 데이터", "로컬에서 생성", "로컬 데이터 업데이트", "총 Token", "입력 Token", "출력 Token", "API 환산 가치", "유효 구독 비용", "가치 배수", "구독 요금제", "서비스", "주기", "월간", "연간", "적용일", "구독 금액(USD)", "요금제 저장", "보고서", "일별 Token", "일별 구독 가치 배수", "서비스 상세", "설정 안 됨", "계산 안 됨", "미가격 Token", "읽은 파일", "모델", "캐시 입력", "공개 가격 없음", "업데이트 중…", "업데이트 완료, 새로고침 중", "로컬 앱이 실행 중이 아닙니다", "데이터 없음", "분석 가능한 로컬 기록 없음", "적용", "요금제 기록", "API 가격 데이터 출처: OpenRouter"],
    "fr": ["Rapport d’utilisation des abonnements IA", "Derniers ", " jours", "Regroupé selon le fuseau horaire local", "Données des journaux locaux", "Généré localement", "Actualiser les données locales", "Total des jetons", "Jetons d’entrée", "Jetons de sortie", "Valeur API équivalente", "Coût d’abonnement effectif", "Multiple de valeur", "Abonnements", "Fournisseur", "Période", "Mensuel", "Annuel", "Date d’effet", "Montant (USD)", "Enregistrer", "rapport", "Jetons quotidiens", "Multiple de valeur quotidien", "Détails par fournisseur", "Non défini", "Non calculé", "Jetons non tarifés", "Fichiers lus", "Modèle", "Entrée en cache", "Aucun tarif public", "Actualisation…", "Actualisation terminée", "L’application locale ne fonctionne pas", "Aucune donnée", "Aucune donnée locale analysable", "en vigueur", "historique des abonnements", "Données tarifaires de l’API fournies par OpenRouter"],
    "de": ["Bericht zur KI-Abonnementnutzung", "Letzte ", " Tage", "Nach lokaler Zeitzone gruppiert", "Daten aus lokalen Protokollen", "Lokal erzeugt", "Lokale Daten aktualisieren", "Token gesamt", "Eingabe-Token", "Ausgabe-Token", "API-Gegenwert", "Effektive Abokosten", "Wertfaktor", "Abonnements", "Anbieter", "Zeitraum", "Monatlich", "Jährlich", "Gültig ab", "Abobetrag (USD)", "Plan speichern", "Bericht", "Token pro Tag", "Täglicher Abo-Wertfaktor", "Anbieterdetails", "Nicht festgelegt", "Nicht berechnet", "Token ohne Preis", "Gelesene Dateien", "Modell", "Cache-Eingabe", "Kein öffentlicher Preis", "Aktualisierung…", "Aktualisiert; Seite wird neu geladen", "Lokale App läuft nicht", "Keine Daten", "Keine auswertbaren lokalen Daten", "gültig", "Planverlauf", "API-Preisdaten von OpenRouter"],
    "es": ["Informe de uso de suscripciones de IA", "Últimos ", " días", "Agrupado por la zona horaria local", "Datos de registros locales", "Generado localmente", "Actualizar datos locales", "Tokens totales", "Tokens de entrada", "Tokens de salida", "Valor equivalente de API", "Coste efectivo de suscripción", "Múltiplo de valor", "Planes de suscripción", "Proveedor", "Periodo", "Mensual", "Anual", "Fecha de vigencia", "Importe (USD)", "Guardar plan", "informe", "Tokens diarios", "Múltiplo de valor diario", "Detalles por proveedor", "Sin configurar", "Sin calcular", "Tokens sin precio", "Archivos leídos", "Modelo", "Entrada en caché", "Sin precio público", "Actualizando…", "Actualización completa; recargando", "La aplicación local no está activa", "Sin datos", "No hay registros locales analizables", "vigente", "historial de planes", "Datos de precios de la API de OpenRouter"],
}

DAYS_FORMAT = {"en": "Last {days} days", "ja": "直近{days}日", "ko": "최근 {days}일", "fr": "Derniers {days} jours", "de": "Letzte {days} Tage", "es": "Últimos {days} días"}
GENERATED_FORMAT = {"en": "Generated locally · {time}", "ja": "ローカルで生成 · {time}", "ko": "로컬에서 생성 · {time}", "fr": "Généré localement · {time}", "de": "Lokal erzeugt · {time}", "es": "Generado localmente · {time}"}
HELP_LINKS = {"en": "Configuration and user guide", "ja": "設定・使用ガイド", "ko": "구성 및 사용 안내", "fr": "Configuration et guide", "de": "Konfiguration und Anleitung", "es": "Configuración y guía"}

EXTRA_TRANSLATIONS = {
    "en": {
        "每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。": "Each provider keeps its own plan history. Monthly plans are allocated over 30 days and annual plans over 360 days; subscription cost is excluded before the effective date.",
        "按这段时间里每天实际生效的订阅价格计算；订阅价格中途变动过的话，这里会是新旧价格混合后的结果。": "Calculated using whichever subscription price was in effect each day in this period; if your subscription price changed partway through, this blends the old and new rates.",
        "各平台当天输入、输出和缓存口径合并后的 Token。": "Daily Token combines input, output, and cached input for each provider.",
        "当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。": "Daily API-equivalent value divided by daily subscription cost. No multiple is calculated when a model has no public price or no plan is active.",
        "输入订阅金额": "Enter subscription amount", "不计算订阅成本与倍数": "Subscription cost and multiple are not calculated",
        "无生效计划": "No active plan", "模型未计价": "Model is unpriced", "日成本": "Daily cost",
        "（无数据）": " (no data)", "（估算）": " (estimated)", "（今日）": " (Today)",
        "更新完成，正在打开本机报表": "Update complete; opening local report", "每个平台": "Each provider", "当天": "Daily",
        "各平台每日 Token 折线图": "Daily Token chart by provider", "各平台每日订阅价值倍数折线图": "Daily subscription value multiple chart by provider",
        "同区间价值倍数": "value multiple for the same period", "<th>输入</th>": "<th>Input</th>", "<th>输出</th>": "<th>Output</th>", "'年'": "'year'", "'月'": "'month'", " 条": " plans",
        "缓存命中率": "Cache hit rate", "对应 DeepSeek 成本": "Est. DeepSeek cost", "对应 DeepSeek": "DeepSeek cost",
        "对应 DeepSeek V4 Pro": "Compared to DeepSeek V4 Pro", "对应 DeepSeek V4 Flash": "Compared to DeepSeek V4 Flash",
        "以 DeepSeek 定价核算的成本，缓存命中率已计入": "Cost estimated using DeepSeek's pricing; cache-hit rate already factored in",
        "各平台已计价模型的 DeepSeek 参考成本合计。": "Sum of DeepSeek reference costs for priced models across providers.",
        "无法确认具体模型的记录保留 Token，但不参与价格计算；所示金额为已确认模型的保守估算。": "Records without an identifiable model remain in Token totals but are excluded from pricing. Displayed costs are conservative estimates based on confirmed models.",
    },
    "ja": {
        "每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。": "サービスごとに個別のプラン履歴を保存します。月額プランは30日、年額プランは360日で日割りし、適用日前の費用は計算しません。",
        "按这段时间里每天实际生效的订阅价格计算；订阅价格中途变动过的话，这里会是新旧价格混合后的结果。": "この期間中、実際にその日ごとに有効だったサブスクリプション価格で計算しています。途中で価格が変わった場合、新旧の価格が混ざった結果になります。",
        "各平台当天输入、输出和缓存口径合并后的 Token。": "各サービスの入力、出力、キャッシュ入力を合算した日別Tokenです。",
        "当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。": "日別API相当額を日別サブスクリプション費用で割った値です。公開価格または有効なプランがない日は倍率を計算しません。",
        "输入订阅金额": "料金を入力", "不计算订阅成本与倍数": "費用と倍率は計算されません", "无生效计划": "有効なプランなし", "模型未计价": "モデル価格なし", "日成本": "日別費用", "（无数据）": "（データなし）", "（估算）": "（推定）", "（今日）": "（本日）", "更新完成，正在打开本机报表": "更新完了、ローカルレポートを開いています",
        "各平台每日 Token 折线图": "サービス別日別Token折れ線グラフ", "各平台每日订阅价值倍数折线图": "サービス別日別サブスクリプション価値倍率グラフ", "同区间价值倍数": "同期間の価値倍率", "<th>输入</th>": "<th>入力</th>", "<th>输出</th>": "<th>出力</th>", "'年'": "'年'", "'月'": "'月'", " 条": "件",
        "缓存命中率": "キャッシュ命中率", "对应 DeepSeek 成本": "DeepSeek概算コスト", "对应 DeepSeek": "DeepSeekコスト",
        "对应 DeepSeek V4 Pro": "DeepSeek V4 Pro と比較", "对应 DeepSeek V4 Flash": "DeepSeek V4 Flash と比較",
        "以 DeepSeek 定价核算的成本，缓存命中率已计入": "DeepSeek の価格で算出した概算コスト。キャッシュ命中率は計算済みです",
        "各平台已计价模型的 DeepSeek 参考成本合计。": "各サービスの価格が確認済みのモデルについて算出した DeepSeek 参考コストの合計です。",
        "无法确认具体模型的记录保留 Token，但不参与价格计算；所示金额为已确认模型的保守估算。": "モデルを特定できない記録も Token 合計には残りますが、価格計算には含まれません。表示金額は特定できたモデルのみに基づく控えめな見積もりです。",
    },
    "ko": {
        "每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。": "서비스별 요금제 이력을 저장합니다. 월간 요금제는 30일, 연간 요금제는 360일로 배분하며 적용일 전에는 구독 비용을 계산하지 않습니다.",
        "按这段时间里每天实际生效的订阅价格计算；订阅价格中途变动过的话，这里会是新旧价格混合后的结果。": "이 기간 동안 매일 실제로 적용된 구독 가격으로 계산합니다. 중간에 구독 가격이 바뀌었다면 신구 가격이 섞인 결과입니다.",
        "各平台当天输入、输出和缓存口径合并后的 Token。": "각 서비스의 입력, 출력, 캐시 입력을 합산한 일별 Token입니다.",
        "当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。": "일별 API 환산 가치를 일별 구독 비용으로 나눈 값입니다. 공개 가격이나 적용 중인 요금제가 없으면 배수를 계산하지 않습니다.",
        "输入订阅金额": "구독 금액 입력", "不计算订阅成本与倍数": "구독 비용과 배수를 계산하지 않음", "无生效计划": "적용 중인 요금제 없음", "模型未计价": "모델 가격 없음", "日成本": "일별 비용", "（无数据）": "(데이터 없음)", "（估算）": "(추정)", "（今日）": "(오늘)", "更新完成，正在打开本机报表": "업데이트 완료, 로컬 보고서를 여는 중",
        "各平台每日 Token 折线图": "서비스별 일별 Token 선 그래프", "各平台每日订阅价值倍数折线图": "서비스별 일별 구독 가치 배수 선 그래프", "同区间价值倍数": "동일 기간 가치 배수", "<th>输入</th>": "<th>입력</th>", "<th>输出</th>": "<th>출력</th>", "'年'": "'연'", "'月'": "'월'", " 条": "개",
        "缓存命中率": "캐시 명중률", "对应 DeepSeek 成本": "DeepSeek 예상 비용", "对应 DeepSeek": "DeepSeek 비용",
        "对应 DeepSeek V4 Pro": "DeepSeek V4 Pro와 비교", "对应 DeepSeek V4 Flash": "DeepSeek V4 Flash와 비교",
        "以 DeepSeek 定价核算的成本，缓存命中率已计入": "DeepSeek 가격으로 산출한 예상 비용입니다. 캐시 명중률은 이미 반영되었습니다",
        "各平台已计价模型的 DeepSeek 参考成本合计。": "각 서비스에서 가격이 확인된 모델의 DeepSeek 참고 비용 합계입니다.",
        "无法确认具体模型的记录保留 Token，但不参与价格计算；所示金额为已确认模型的保守估算。": "모델을 확인할 수 없는 기록도 Token 합계에는 포함되지만 가격 계산에는 포함되지 않습니다. 표시된 금액은 확인된 모델만을 기준으로 한 보수적인 추정치입니다.",
    },
    "fr": {
        "每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。": "Chaque fournisseur conserve son propre historique. Les abonnements mensuels sont répartis sur 30 jours et les annuels sur 360 jours ; aucun coût n’est calculé avant la date d’effet.",
        "按这段时间里每天实际生效的订阅价格计算；订阅价格中途变动过的话，这里会是新旧价格混合后的结果。": "Calculé à partir du tarif d’abonnement réellement en vigueur chaque jour de cette période ; si votre tarif a changé en cours de route, ce montant mélange l’ancien et le nouveau tarif.",
        "各平台当天输入、输出和缓存口径合并后的 Token。": "Les Token quotidiens regroupent les entrées, les sorties et les entrées en cache de chaque fournisseur.",
        "当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。": "Valeur API quotidienne divisée par le coût quotidien de l’abonnement. Aucun multiple n’est calculé sans tarif public ou abonnement actif.",
        "输入订阅金额": "Saisir le montant", "不计算订阅成本与倍数": "Coût et multiple non calculés", "无生效计划": "Aucun abonnement actif", "模型未计价": "Modèle non tarifé", "日成本": "Coût quotidien", "（无数据）": " (aucune donnée)", "（估算）": " (estimation)", "（今日）": " (Aujourd’hui)", "更新完成，正在打开本机报表": "Mise à jour terminée ; ouverture du rapport local",
        "各平台每日 Token 折线图": "Courbe des Token quotidiens par fournisseur", "各平台每日订阅价值倍数折线图": "Courbe du multiple quotidien par fournisseur", "同区间价值倍数": "multiple de valeur sur la même période", "<th>输入</th>": "<th>Entrée</th>", "<th>输出</th>": "<th>Sortie</th>", "'年'": "'an'", "'月'": "'mois'", " 条": " plans",
        "缓存命中率": "Taux de succès du cache", "对应 DeepSeek 成本": "Coût DeepSeek estimé", "对应 DeepSeek": "Coût DeepSeek",
        "对应 DeepSeek V4 Pro": "Comparé à DeepSeek V4 Pro", "对应 DeepSeek V4 Flash": "Comparé à DeepSeek V4 Flash",
        "以 DeepSeek 定价核算的成本，缓存命中率已计入": "Coût estimé avec les tarifs de DeepSeek ; le taux de succès du cache est déjà pris en compte",
        "各平台已计价模型的 DeepSeek 参考成本合计。": "Somme des coûts de référence DeepSeek pour les modèles tarifés, tous fournisseurs confondus.",
        "无法确认具体模型的记录保留 Token，但不参与价格计算；所示金额为已确认模型的保守估算。": "Les enregistrements sans modèle identifiable restent comptés dans les Token totaux mais sont exclus du calcul des coûts. Les montants affichés sont des estimations prudentes basées sur les modèles confirmés.",
    },
    "de": {
        "每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。": "Für jeden Anbieter wird ein eigener Planverlauf gespeichert. Monatspläne werden auf 30 Tage und Jahrespläne auf 360 Tage verteilt; vor dem Gültigkeitsdatum werden keine Kosten berechnet.",
        "按这段时间里每天实际生效的订阅价格计算；订阅价格中途变动过的话，这里会是新旧价格混合后的结果。": "Berechnet anhand des Abopreises, der an jedem einzelnen Tag dieses Zeitraums tatsächlich galt; hat sich Ihr Abopreis zwischenzeitlich geändert, vermischt dieser Wert den alten und den neuen Preis.",
        "各平台当天输入、输出和缓存口径合并后的 Token。": "Die täglichen Token umfassen Eingabe, Ausgabe und Cache-Eingabe jedes Anbieters.",
        "当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。": "Täglicher API-Gegenwert geteilt durch tägliche Abokosten. Ohne öffentlichen Modellpreis oder aktiven Plan wird kein Faktor berechnet.",
        "输入订阅金额": "Abobetrag eingeben", "不计算订阅成本与倍数": "Abokosten und Faktor werden nicht berechnet", "无生效计划": "Kein aktiver Plan", "模型未计价": "Modell ohne Preis", "日成本": "Tageskosten", "（无数据）": " (keine Daten)", "（估算）": " (geschätzt)", "（今日）": " (Heute)", "更新完成，正在打开本机报表": "Aktualisierung abgeschlossen; lokaler Bericht wird geöffnet",
        "各平台每日 Token 折线图": "Tägliches Token-Liniendiagramm nach Anbieter", "各平台每日订阅价值倍数折线图": "Tägliches Wertfaktor-Liniendiagramm nach Anbieter", "同区间价值倍数": "Wertfaktor im selben Zeitraum", "<th>输入</th>": "<th>Eingabe</th>", "<th>输出</th>": "<th>Ausgabe</th>", "'年'": "'Jahr'", "'月'": "'Monat'", " 条": " Pläne",
        "缓存命中率": "Cache-Trefferquote", "对应 DeepSeek 成本": "Geschätzte DeepSeek-Kosten", "对应 DeepSeek": "DeepSeek-Kosten",
        "对应 DeepSeek V4 Pro": "Verglichen mit DeepSeek V4 Pro", "对应 DeepSeek V4 Flash": "Verglichen mit DeepSeek V4 Flash",
        "以 DeepSeek 定价核算的成本，缓存命中率已计入": "Geschätzte Kosten anhand der DeepSeek-Preise; die Cache-Trefferquote ist bereits berücksichtigt",
        "各平台已计价模型的 DeepSeek 参考成本合计。": "Summe der DeepSeek-Referenzkosten für bepreiste Modelle über alle Anbieter hinweg.",
        "无法确认具体模型的记录保留 Token，但不参与价格计算；所示金额为已确认模型的保守估算。": "Datensätze ohne erkennbares Modell bleiben in der Token-Gesamtsumme enthalten, fließen aber nicht in die Preisberechnung ein. Die angezeigten Beträge sind vorsichtige Schätzungen auf Basis bestätigter Modelle.",
    },
    "es": {
        "每个平台保存独立的计划历史。月订阅按 30 天分摊，年订阅按 360 天分摊；计划生效日前不计算订阅成本。": "Cada proveedor conserva su propio historial. Los planes mensuales se reparten en 30 días y los anuales en 360 días; no se calcula coste antes de la fecha de vigencia.",
        "按这段时间里每天实际生效的订阅价格计算；订阅价格中途变动过的话，这里会是新旧价格混合后的结果。": "Se calcula con el precio de suscripción que estuvo realmente vigente cada día de este periodo; si el precio cambió a mitad de camino, este importe mezcla la tarifa antigua y la nueva.",
        "各平台当天输入、输出和缓存口径合并后的 Token。": "Los Token diarios combinan entrada, salida y entrada en caché de cada proveedor.",
        "当天 API 等价价值 ÷ 当天订阅日成本。没有公开模型价格或没有生效订阅计划时，该平台当天不计算倍数。": "Valor API diario dividido por el coste diario de suscripción. No se calcula el múltiplo sin precio público o plan activo.",
        "输入订阅金额": "Introducir importe", "不计算订阅成本与倍数": "No se calculan el coste ni el múltiplo", "无生效计划": "Sin plan activo", "模型未计价": "Modelo sin precio", "日成本": "Coste diario", "（无数据）": " (sin datos)", "（估算）": " (estimado)", "（今日）": " (Hoy)", "更新完成，正在打开本机报表": "Actualización completa; abriendo el informe local",
        "各平台每日 Token 折线图": "Gráfico de Token diarios por proveedor", "各平台每日订阅价值倍数折线图": "Gráfico del múltiplo diario por proveedor", "同区间价值倍数": "múltiplo de valor del mismo periodo", "<th>输入</th>": "<th>Entrada</th>", "<th>输出</th>": "<th>Salida</th>", "'年'": "'año'", "'月'": "'mes'", " 条": " planes",
        "缓存命中率": "Tasa de aciertos de caché", "对应 DeepSeek 成本": "Coste estimado en DeepSeek", "对应 DeepSeek": "Coste DeepSeek",
        "对应 DeepSeek V4 Pro": "Comparado con DeepSeek V4 Pro", "对应 DeepSeek V4 Flash": "Comparado con DeepSeek V4 Flash",
        "以 DeepSeek 定价核算的成本，缓存命中率已计入": "Coste estimado con los precios de DeepSeek; la tasa de aciertos de caché ya está incluida",
        "各平台已计价模型的 DeepSeek 参考成本合计。": "Suma de los costes de referencia de DeepSeek de los modelos con precio, en todos los proveedores.",
        "无法确认具体模型的记录保留 Token，但不参与价格计算；所示金额为已确认模型的保守估算。": "Los registros sin un modelo identificable permanecen en los totales de Token, pero se excluyen del cálculo de precios. Los importes mostrados son estimaciones conservadoras basadas en modelos confirmados.",
    },
}


def localize_html(page: str, language: str) -> str:
    if language == "zh-CN" or language not in TRANSLATIONS:
        return page
    translated = page.replace('lang="zh-CN"', f'lang="{language}"')
    translated = translated.replace("配置及使用说明", HELP_LINKS[language])
    for source, target in sorted(EXTRA_TRANSLATIONS[language].items(), key=lambda pair: len(pair[0]), reverse=True):
        translated = translated.replace(source, target)
    translated = re.sub(r"最近 (\d+) 天", lambda match: DAYS_FORMAT[language].format(days=match.group(1)), translated)
    translated = re.sub(r"生成于本机 · (\d{4}-\d{2}-\d{2} \d{2}:\d{2})", lambda match: GENERATED_FORMAT[language].format(time=match.group(1)), translated)
    pairs = sorted(zip(ZH, TRANSLATIONS[language]), key=lambda pair: len(pair[0]), reverse=True)
    for source, target in pairs:
        if source in {"最近", "天"}:
            continue
        translated = translated.replace(source, target)
    return translated
