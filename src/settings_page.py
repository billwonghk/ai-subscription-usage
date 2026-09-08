"""Localized settings panel served over the local HTTP server."""

from __future__ import annotations

import html
import json

from favicon import FAVICON_TAG, LOGO_IMG


EN = {
    "title": "AI Subscription Usage: Settings",
    "language": "Language",
    "autostart": "Launch at login",
    "telemetry": "Send anonymous diagnostics",
    "refresh_interval": "Automatic refresh",
    "refresh_schedule": "Once per local day at 03:00. If missed, refresh 15 minutes after the next launch unless today's refresh already succeeded.",
    "open_data_folder": "Open data folder",
    "clear_diagnostics": "Clear diagnostic records",
    "diagnostics_cleared": "Diagnostic records cleared",
    "report_issue": "Report an issue",
    "on": "On",
    "off": "Off",
    "app_not_running": "Local app is not running",
    "providers": "Monitored platforms",
    "providers_note": "Only enabled platforms are read, calculated, and shown in the report.",
    "add": "Add",
    "remove": "Remove",
    "copy_prompt": "Copy setup prompt",
    "prompt_copied": "Setup prompt copied",
    "prompt_copy_failed": "Could not copy automatically. Please copy the prompt manually.",
    "provider_updating": "Saving platform selection and updating the report…",
    "provider_added": "{provider} added. The report is updating.",
    "provider_removed": "{provider} removed. The report is updating.",
    "ready": "Local records found",
    "ready_enabled": "Added · local records will be included",
    "ready_available": "Local records found · not included until added",
    "no_records": "No local records found",
    "not_found": "App or data directory not found",
    "permission_required": "Read permission required",
    "unsupported_format": "Records detected, format not supported",
    "enabled": "Added",
    "available": "Available platforms",
    "plans": "Subscription plan management",
    "plans_note": "Delete an incorrect plan here. Report cards never contain delete controls.",
    "no_plans": "No subscription plans saved",
    "delete_plan": "Delete",
    "delete_confirm": "Delete this subscription plan? Only the selected provider and effective date will be removed.",
    "plan_deleting": "Deleting the selected plan and updating the report…",
    "month": "month",
    "year": "year",
}

TEXT = {
    "en": EN,
    "zh-CN": {**EN, "title": "AI 订阅用量：设置", "language": "语言", "autostart": "开机自动启动", "telemetry": "发送匿名诊断", "refresh_interval": "刷新频率", "open_data_folder": "打开数据文件夹", "clear_diagnostics": "清除诊断记录", "diagnostics_cleared": "诊断记录已清除", "report_issue": "反馈问题", "hours_suffix": "小时", "on": "已开启", "off": "已关闭", "app_not_running": "本机应用未运行", "providers": "监控平台", "providers_note": "选择需要统计的平台。只有已添加的平台会被读取、计算并显示在报表中。", "add": "添加", "remove": "移除", "copy_prompt": "复制配置提示词", "prompt_copied": "配置提示词已复制", "prompt_copy_failed": "自动复制失败，请手动复制配置提示词。", "provider_updating": "正在保存平台选择并更新报表…", "provider_added": "{provider} 已添加，报表正在更新。", "provider_removed": "{provider} 已移除，报表正在更新。", "ready": "已找到本机记录", "ready_enabled": "已添加 · 本机记录将纳入统计", "ready_available": "已找到本机记录 · 添加后才会纳入统计", "no_records": "没有找到本机记录", "not_found": "未找到应用或数据目录", "permission_required": "需要读取权限", "unsupported_format": "已检测记录，等待格式验证", "enabled": "已添加", "available": "可添加平台"},
    "ja": {**EN, "title": "AIサブスクリプション使用量：設定", "language": "言語", "autostart": "ログイン時に起動", "telemetry": "匿名診断を送信", "refresh_interval": "更新間隔", "open_data_folder": "データフォルダを開く", "clear_diagnostics": "診断記録を消去", "diagnostics_cleared": "診断記録を消去しました", "report_issue": "問題を報告", "hours_suffix": "時間", "on": "オン", "off": "オフ", "app_not_running": "ローカルアプリが起動していません", "providers": "監視するプラットフォーム", "providers_note": "追加したプラットフォームだけを読み取り、計算して表示します。", "add": "追加", "remove": "削除", "copy_prompt": "設定プロンプトをコピー", "prompt_copied": "設定プロンプトをコピーしました", "ready": "ローカル記録を検出", "no_records": "ローカル記録なし", "not_found": "アプリまたはデータフォルダが見つかりません", "permission_required": "読み取り権限が必要", "unsupported_format": "記録を検出しましたが形式は未対応"},
    "ko": {**EN, "title": "AI 구독 사용량: 설정", "language": "언어", "autostart": "로그인 시 시작", "telemetry": "익명 진단 전송", "refresh_interval": "새로고침 주기", "open_data_folder": "데이터 폴더 열기", "clear_diagnostics": "진단 기록 지우기", "diagnostics_cleared": "진단 기록이 삭제되었습니다", "report_issue": "문제 신고", "hours_suffix": "시간", "on": "켜짐", "off": "꺼짐", "app_not_running": "로컬 앱이 실행 중이 아닙니다", "providers": "모니터링 플랫폼", "providers_note": "추가한 플랫폼만 읽고 계산하여 보고서에 표시합니다.", "add": "추가", "remove": "제거", "copy_prompt": "설정 프롬프트 복사", "prompt_copied": "설정 프롬프트를 복사했습니다", "ready": "로컬 기록 발견", "no_records": "로컬 기록 없음", "not_found": "앱 또는 데이터 폴더를 찾지 못함", "permission_required": "읽기 권한 필요", "unsupported_format": "기록을 찾았지만 형식은 지원되지 않음"},
    "fr": {**EN, "title": "Utilisation des abonnements IA : paramètres", "language": "Langue", "autostart": "Lancer à l'ouverture de session", "telemetry": "Envoyer les diagnostics anonymes", "refresh_interval": "Intervalle d'actualisation", "open_data_folder": "Ouvrir le dossier de données", "clear_diagnostics": "Effacer les journaux de diagnostic", "diagnostics_cleared": "Journaux de diagnostic effacés", "report_issue": "Signaler un problème", "hours_suffix": "heures", "on": "Activé", "off": "Désactivé", "app_not_running": "L'application locale ne fonctionne pas", "providers": "Plateformes surveillées", "providers_note": "Seules les plateformes ajoutées sont lues, calculées et affichées.", "add": "Ajouter", "remove": "Retirer", "copy_prompt": "Copier l'invite de configuration", "prompt_copied": "Invite de configuration copiée", "ready": "Données locales trouvées", "no_records": "Aucune donnée locale", "not_found": "Application ou dossier introuvable", "permission_required": "Autorisation de lecture requise", "unsupported_format": "Données détectées, format non pris en charge"},
    "de": {**EN, "title": "KI-Abonnementnutzung: Einstellungen", "language": "Sprache", "autostart": "Bei Anmeldung starten", "telemetry": "Anonyme Diagnosen senden", "refresh_interval": "Aktualisierungsintervall", "open_data_folder": "Datenordner öffnen", "clear_diagnostics": "Diagnoseprotokolle löschen", "diagnostics_cleared": "Diagnoseprotokolle gelöscht", "report_issue": "Problem melden", "hours_suffix": "Stunden", "on": "Ein", "off": "Aus", "app_not_running": "Lokale App läuft nicht", "providers": "Überwachte Plattformen", "providers_note": "Nur hinzugefügte Plattformen werden gelesen, berechnet und angezeigt.", "add": "Hinzufügen", "remove": "Entfernen", "copy_prompt": "Einrichtungs-Prompt kopieren", "prompt_copied": "Einrichtungs-Prompt kopiert", "ready": "Lokale Daten gefunden", "no_records": "Keine lokalen Daten", "not_found": "App oder Datenordner nicht gefunden", "permission_required": "Leseberechtigung erforderlich", "unsupported_format": "Daten erkannt, Format nicht unterstützt"},
    "es": {**EN, "title": "Uso de suscripciones de IA: configuración", "language": "Idioma", "autostart": "Iniciar al iniciar sesión", "telemetry": "Enviar diagnósticos anónimos", "refresh_interval": "Intervalo de actualización", "open_data_folder": "Abrir carpeta de datos", "clear_diagnostics": "Borrar registros de diagnóstico", "diagnostics_cleared": "Registros de diagnóstico borrados", "report_issue": "Informar un problema", "hours_suffix": "horas", "on": "Activado", "off": "Desactivado", "app_not_running": "La aplicación local no está activa", "providers": "Plataformas supervisadas", "providers_note": "Solo se leen, calculan y muestran las plataformas añadidas.", "add": "Añadir", "remove": "Quitar", "copy_prompt": "Copiar instrucción de configuración", "prompt_copied": "Instrucción de configuración copiada", "ready": "Registros locales encontrados", "no_records": "Sin registros locales", "not_found": "Aplicación o carpeta no encontrada", "permission_required": "Se requiere permiso de lectura", "unsupported_format": "Registros detectados, formato no compatible"},
}

TEXT["ja"].update({"enabled": "追加済み", "available": "追加できるプラットフォーム"})
TEXT["ko"].update({"enabled": "추가됨", "available": "추가 가능한 플랫폼"})
TEXT["fr"].update({"enabled": "Ajoutée", "available": "Plateformes disponibles"})
TEXT["de"].update({"enabled": "Hinzugefügt", "available": "Verfügbare Plattformen"})
TEXT["es"].update({"enabled": "Añadida", "available": "Plataformas disponibles"})
TEXT["zh-CN"].update({
    "refresh_interval": "自动刷新",
    "refresh_schedule": "按本机时间每天凌晨 3:00 更新一次。当天未成功更新时，应用启动 15 分钟后补更新一次；当天已经更新则跳过。",
    "plans": "订阅计划管理",
    "plans_note": "填写错误的订阅计划只能在这里删除，报表卡片不提供删除入口。",
    "no_plans": "尚未保存订阅计划",
    "delete_plan": "删除",
    "delete_confirm": "确认删除这条订阅计划吗？只会删除当前平台和生效日期对应的记录。",
    "plan_deleting": "正在删除指定计划并更新报表…",
    "month": "月",
    "year": "年",
})

LANGUAGE_NAMES = {"en": "English", "zh-CN": "中文", "ja": "日本語", "ko": "한국어", "fr": "Français", "de": "Deutsch", "es": "Español"}
ISSUE_TRACKER_URL = "https://github.com/billwonghk/ai-subscription-usage/issues/new"


def render_settings(language: str, current_settings: dict, autostart_enabled: bool, autostart_supported: bool, app_version: str = "development", provider_states: list[dict] | None = None, setup_prompt: str = "", subscription_plans: list[dict] | None = None) -> str:
    """Every control applies and saves immediately on click; there is no separate save step."""
    t = TEXT.get(language, EN)
    telemetry_on = bool(current_settings.get("telemetry_consent"))
    provider_states = provider_states or []
    subscription_plans = subscription_plans or []
    def provider_label(value: str) -> str:
        return "Alibaba Bailian" if language == "en" and value == "阿里百炼" else value

    language_buttons = "".join(
        f'<button class="chip{" active" if code == language else ""}" aria-pressed="{str(code == language).lower()}" data-action="set_language" data-value="{html.escape(code)}">{html.escape(name)}</button>'
        for code, name in LANGUAGE_NAMES.items()
    )
    autostart_row = ""
    if autostart_supported:
        autostart_row = (
            '<div class="row"><div class="label">' + html.escape(t["autostart"]) + '</div>'
            f'<button class="toggle{" on" if autostart_enabled else ""}" data-action="set_autostart" data-value="{"false" if autostart_enabled else "true"}">'
            f'{html.escape(t["on"] if autostart_enabled else t["off"])}</button></div>'
        )
    telemetry_row = (
        '<div class="row"><div class="label">' + html.escape(t["telemetry"]) + '</div>'
        f'<button class="toggle{" on" if telemetry_on else ""}" data-action="set_telemetry" data-value="{"false" if telemetry_on else "true"}">'
        f'{html.escape(t["on"] if telemetry_on else t["off"])}</button></div>'
    )
    provider_cards = "".join(
        '<article class="provider-card' + (' selected' if item["enabled"] else '') + '"><div class="provider-head"><span class="provider-mark" style="--provider-color:' + html.escape(item.get("color", "#61a8ff")) + '"></span><strong>' + html.escape(provider_label(item["label"])) + '</strong>'
        + (f'<span class="provider-badge">{html.escape(t["enabled"])}</span>' if item["enabled"] else '') + '</div><div class="provider-status"><span class="status-dot status-' + html.escape(item["status"]) + '"></span>'
        + html.escape(t.get(("ready_enabled" if item["enabled"] else "ready_available") if item["status"] == "ready" else item["status"], item["status"])) + '</div><div class="provider-actions">'
        + (f'<button class="action copy-prompt" data-provider="{html.escape(item["label"])}">{html.escape(t["copy_prompt"])}</button>' if item["status"] != "ready" else "")
        + f'<button class="toggle{" on" if item["enabled"] else ""}" data-action="toggle_provider" data-value="{html.escape(item["id"])}">{html.escape(t["remove"] if item["enabled"] else t["add"])}</button>'
        + '</div></article>'
        for item in provider_states
    )
    plan_rows = "".join(
        '<div class="plan-row"><div><strong>' + html.escape(provider_label(plan["provider"])) + '</strong><div class="plan-meta">'
        + html.escape(plan["start_date"]) + ' · ' + html.escape(str(plan["amount"])) + ' ' + html.escape(plan.get("currency", "USD"))
        + ' / ' + html.escape(t["year"] if plan["cycle"] == "year" else t["month"]) + '</div></div>'
        + '<button class="danger delete-plan" data-provider="' + html.escape(plan["provider"]) + '" data-start="' + html.escape(plan["start_date"]) + '">' + html.escape(t["delete_plan"]) + '</button></div>'
        for plan in subscription_plans
    ) or '<div class="status">' + html.escape(t["no_plans"]) + '</div>'

    style = (
        ':root{color-scheme:dark;--bg:#080d18;--card:#101a2b;--ink:#ecf5ff;--sub:#a8b7ce;--line:#263854;--accent:#61a8ff}'
        '*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}'
        'main{max-width:980px;margin:auto;padding:38px 24px 72px}h1{font-size:26px;margin:0 0 24px;display:flex;align-items:center;gap:12px}'
        '.brand-logo{width:30px;height:30px;border-radius:7px;flex:none}'
        'section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:16px}'
        '.row{display:flex;align-items:center;justify-content:space-between;gap:16px}'
        '.row+.row{margin-top:16px;padding-top:16px;border-top:1px solid var(--line)}'
        '.label{color:var(--sub);font-size:14px}'
        '.chips{display:flex;flex-wrap:wrap;gap:8px}'
        '.chip{font:inherit;border:1px solid var(--line);border-radius:9px;padding:8px 14px;background:#0a1322;color:var(--ink);cursor:pointer}'
        '.chip.active{background:var(--accent);color:#07101d;border-color:var(--accent);font-weight:650}'
        '.toggle{font:inherit;border:1px solid var(--line);border-radius:9px;padding:8px 16px;background:#0a1322;color:var(--sub);cursor:pointer;min-width:84px}'
        '.toggle.on{background:var(--accent);color:#07101d;border-color:var(--accent);font-weight:650}'
        '.action-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}'
        'button.action,a.action{font:inherit;border:1px solid var(--line);border-radius:9px;padding:9px 16px;background:#0a1322;color:var(--ink);cursor:pointer;text-decoration:none;display:inline-block}'
        '.status{color:var(--sub);font-size:13px;margin-top:10px;min-height:16px}'
        '.provider-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:16px}'
        '.provider-card{min-height:154px;border:1px solid var(--line);border-radius:13px;padding:16px;background:#0b1525;display:flex;flex-direction:column;gap:12px;transition:border-color .18s,background .18s,transform .18s}'
        '.provider-card:hover{transform:translateY(-1px);border-color:#3b577d}.provider-card.selected{background:linear-gradient(145deg,#10223a,#0b1525);border-color:#3e6c9f}'
        '.provider-head{display:flex;align-items:center;gap:10px;font-size:16px}.provider-mark{width:10px;height:30px;border-radius:6px;background:var(--provider-color);box-shadow:0 0 14px color-mix(in srgb,var(--provider-color),transparent 35%)}'
        '.provider-badge{margin-left:auto;padding:4px 8px;border-radius:999px;background:#18385a;color:#8fc5ff;font-size:11px;font-weight:650}'
        '.provider-status{display:flex;align-items:center;gap:7px;color:var(--sub);font-size:13px}.status-dot{width:7px;height:7px;border-radius:50%;background:#60708a}.status-ready{background:#2ed5a7;box-shadow:0 0 8px #2ed5a788}.status-unsupported_format{background:#ffb454}.provider-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:auto}.provider-actions .toggle{margin-left:auto}'
        '.plan-list{margin-top:14px;border:1px solid var(--line);border-radius:11px;overflow:hidden}.plan-row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px;background:#0b1525}.plan-row+.plan-row{border-top:1px solid var(--line)}.plan-meta{color:var(--sub);font-size:13px;margin-top:5px}.danger{font:inherit;border:1px solid #7d3b4a;border-radius:9px;padding:8px 14px;background:#28131a;color:#ff9aae;cursor:pointer}.danger:hover{background:#381821}'
        '@media(max-width:680px){.provider-grid{grid-template-columns:1fr}}'
    )
    script = (
        "async function post(action,value){const r=await fetch('http://127.0.0.1:17653/settings',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:JSON.stringify({action,value})});if(!r.ok)throw new Error();return r.json()}"
        "const statusEl=document.getElementById('status');const savedNotice=sessionStorage.getItem('settingsNotice');if(savedNotice){statusEl.textContent=savedNotice;sessionStorage.removeItem('settingsNotice')}"
        "document.querySelectorAll('[data-action]').forEach(el=>{el.addEventListener('click',async()=>{"
        "const action=el.dataset.action;let value=el.dataset.value;"
        "if(value==='true')value=true;else if(value==='false')value=false;else if(!isNaN(value))value=Number(value);"
        "el.disabled=true;if(action==='toggle_provider')statusEl.textContent='" + html.escape(t["provider_updating"]) + "';"
        "try{const result=await post(action,value);if(action==='toggle_provider'){const name=el.closest('.provider-card').querySelector('strong').textContent;const message=(result.enabled?" + json.dumps(t["provider_added"], ensure_ascii=False) + ":" + json.dumps(t["provider_removed"], ensure_ascii=False) + ").replace('{provider}',name);sessionStorage.setItem('settingsNotice',message)}location.reload()}catch{el.disabled=false;statusEl.textContent='" + html.escape(t["app_not_running"]) + "'}"
        "})});"
        "document.getElementById('open-folder').addEventListener('click',async()=>{try{await post('open_data_folder',null)}catch{}});"
        "document.getElementById('clear-diagnostics').addEventListener('click',async()=>{try{await post('clear_diagnostics',null);document.getElementById('status').textContent='"
        + html.escape(t["diagnostics_cleared"]) + "'}catch{}});"
        "const setupPrompt=" + json.dumps(setup_prompt, ensure_ascii=False) + ";"
        "async function copyText(value){if(navigator.clipboard&&window.isSecureContext){try{await navigator.clipboard.writeText(value);return true}catch{}}const area=document.createElement('textarea');area.value=value;area.setAttribute('readonly','');area.style.position='fixed';area.style.opacity='0';document.body.appendChild(area);area.select();let copied=false;try{copied=document.execCommand('copy')}catch{}area.remove();return copied}"
        "document.querySelectorAll('.copy-prompt').forEach(el=>el.addEventListener('click',async()=>{const copied=await copyText(setupPrompt+' Focus on provider: '+el.dataset.provider+'.');statusEl.textContent=copied?'" + html.escape(t["prompt_copied"]) + "':'" + html.escape(t["prompt_copy_failed"]) + "'}));"
        "document.querySelectorAll('.delete-plan').forEach(el=>el.addEventListener('click',async()=>{if(!confirm(" + json.dumps(t["delete_confirm"], ensure_ascii=False) + "))return;el.disabled=true;statusEl.textContent=" + json.dumps(t["plan_deleting"], ensure_ascii=False) + ";try{await post('delete_plan',{provider:el.dataset.provider,start_date:el.dataset.start});location.reload()}catch{el.disabled=false;statusEl.textContent=" + json.dumps(t["app_not_running"], ensure_ascii=False) + "}}));"
    )
    return f'''<!doctype html><html lang="{html.escape(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{FAVICON_TAG}<title>{html.escape(t['title'])}</title><style>{style}</style></head><body><main>
<h1>{LOGO_IMG}{html.escape(t['title'])} · Ver {html.escape(app_version)}</h1>
<section><div class="label">{html.escape(t['language'])}</div><div class="chips" style="margin-top:10px">{language_buttons}</div></section>
<section><div class="label">{html.escape(t['providers'])}</div><p class="provider-status">{html.escape(t['providers_note'])}</p><div class="provider-grid">{provider_cards}</div></section>
<section><div class="label">{html.escape(t['plans'])}</div><p class="provider-status">{html.escape(t['plans_note'])}</p><div class="plan-list">{plan_rows}</div></section>
<section>{autostart_row}{telemetry_row}</section>
<section><div class="label">{html.escape(t['refresh_interval'])}</div><p class="provider-status">{html.escape(t['refresh_schedule'])}</p></section>
<section><div class="action-row"><button class="action" id="open-folder">{html.escape(t['open_data_folder'])}</button><button class="action" id="clear-diagnostics">{html.escape(t['clear_diagnostics'])}</button><a class="action" href="{html.escape(ISSUE_TRACKER_URL)}" target="_blank" rel="noopener">{html.escape(t['report_issue'])}</a></div><div class="status" id="status"></div></section>
</main><script>{script}</script></body></html>'''
