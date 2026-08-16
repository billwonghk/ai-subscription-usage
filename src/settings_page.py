"""Localized settings panel served over the local HTTP server."""

from __future__ import annotations

import html


EN = {
    "title": "AI Subscription Usage: Settings",
    "language": "Language",
    "autostart": "Launch at login",
    "telemetry": "Send anonymous diagnostics",
    "refresh_interval": "Refresh interval",
    "open_data_folder": "Open data folder",
    "clear_diagnostics": "Clear diagnostic records",
    "diagnostics_cleared": "Diagnostic records cleared",
    "hours_suffix": "hours",
    "on": "On",
    "off": "Off",
    "app_not_running": "Local app is not running",
}

TEXT = {
    "en": EN,
    "zh-CN": {**EN, "title": "AI 订阅用量：设置", "language": "语言", "autostart": "开机自动启动", "telemetry": "发送匿名诊断", "refresh_interval": "刷新频率", "open_data_folder": "打开数据文件夹", "clear_diagnostics": "清除诊断记录", "diagnostics_cleared": "诊断记录已清除", "hours_suffix": "小时", "on": "已开启", "off": "已关闭", "app_not_running": "本机应用未运行"},
    "ja": {**EN, "title": "AIサブスクリプション使用量：設定", "language": "言語", "autostart": "ログイン時に起動", "telemetry": "匿名診断を送信", "refresh_interval": "更新間隔", "open_data_folder": "データフォルダを開く", "clear_diagnostics": "診断記録を消去", "diagnostics_cleared": "診断記録を消去しました", "hours_suffix": "時間", "on": "オン", "off": "オフ", "app_not_running": "ローカルアプリが起動していません"},
    "ko": {**EN, "title": "AI 구독 사용량: 설정", "language": "언어", "autostart": "로그인 시 시작", "telemetry": "익명 진단 전송", "refresh_interval": "새로고침 주기", "open_data_folder": "데이터 폴더 열기", "clear_diagnostics": "진단 기록 지우기", "diagnostics_cleared": "진단 기록이 삭제되었습니다", "hours_suffix": "시간", "on": "켜짐", "off": "꺼짐", "app_not_running": "로컬 앱이 실행 중이 아닙니다"},
    "fr": {**EN, "title": "Utilisation des abonnements IA : paramètres", "language": "Langue", "autostart": "Lancer à l'ouverture de session", "telemetry": "Envoyer les diagnostics anonymes", "refresh_interval": "Intervalle d'actualisation", "open_data_folder": "Ouvrir le dossier de données", "clear_diagnostics": "Effacer les journaux de diagnostic", "diagnostics_cleared": "Journaux de diagnostic effacés", "hours_suffix": "heures", "on": "Activé", "off": "Désactivé", "app_not_running": "L'application locale ne fonctionne pas"},
    "de": {**EN, "title": "KI-Abonnementnutzung: Einstellungen", "language": "Sprache", "autostart": "Bei Anmeldung starten", "telemetry": "Anonyme Diagnosen senden", "refresh_interval": "Aktualisierungsintervall", "open_data_folder": "Datenordner öffnen", "clear_diagnostics": "Diagnoseprotokolle löschen", "diagnostics_cleared": "Diagnoseprotokolle gelöscht", "hours_suffix": "Stunden", "on": "Ein", "off": "Aus", "app_not_running": "Lokale App läuft nicht"},
    "es": {**EN, "title": "Uso de suscripciones de IA: configuración", "language": "Idioma", "autostart": "Iniciar al iniciar sesión", "telemetry": "Enviar diagnósticos anónimos", "refresh_interval": "Intervalo de actualización", "open_data_folder": "Abrir carpeta de datos", "clear_diagnostics": "Borrar registros de diagnóstico", "diagnostics_cleared": "Registros de diagnóstico borrados", "hours_suffix": "horas", "on": "Activado", "off": "Desactivado", "app_not_running": "La aplicación local no está activa"},
}

LANGUAGE_NAMES = {"zh-CN": "中文", "en": "English", "ja": "日本語", "ko": "한국어", "fr": "Français", "de": "Deutsch", "es": "Español"}
REFRESH_HOURS_CHOICES = (6, 12, 24)


def render_settings(language: str, current_settings: dict, autostart_enabled: bool, autostart_supported: bool, app_version: str = "development") -> str:
    """Every control applies and saves immediately on click; there is no separate save step."""
    t = TEXT.get(language, EN)
    current_refresh_hours = int(current_settings.get("refresh_hours", 24))
    telemetry_on = bool(current_settings.get("telemetry_consent"))

    language_buttons = "".join(
        f'<button class="chip{" active" if code == language else ""}" data-action="set_language" data-value="{html.escape(code)}">{html.escape(name)}</button>'
        for code, name in LANGUAGE_NAMES.items()
    )
    refresh_buttons = "".join(
        f'<button class="chip{" active" if hours == current_refresh_hours else ""}" data-action="set_refresh_hours" data-value="{hours}">{hours} {html.escape(t["hours_suffix"])}</button>'
        for hours in REFRESH_HOURS_CHOICES
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

    style = (
        ':root{color-scheme:dark;--bg:#080d18;--card:#101a2b;--ink:#ecf5ff;--sub:#a8b7ce;--line:#263854;--accent:#61a8ff}'
        '*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}'
        'main{max-width:720px;margin:auto;padding:38px 24px 72px}h1{font-size:26px;margin:0 0 24px}'
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
        'button.action{font:inherit;border:1px solid var(--line);border-radius:9px;padding:9px 16px;background:#0a1322;color:var(--ink);cursor:pointer}'
        '.status{color:var(--sub);font-size:13px;margin-top:10px;min-height:16px}'
    )
    script = (
        "async function post(action,value){const r=await fetch('http://127.0.0.1:17653/settings',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:JSON.stringify({action,value})});if(!r.ok)throw new Error();return r.json()}"
        "document.querySelectorAll('[data-action]').forEach(el=>{el.addEventListener('click',async()=>{"
        "const action=el.dataset.action;let value=el.dataset.value;"
        "if(value==='true')value=true;else if(value==='false')value=false;else if(!isNaN(value))value=Number(value);"
        "try{await post(action,value);location.reload()}catch{document.getElementById('status').textContent='" + html.escape(t["app_not_running"]) + "'}"
        "})});"
        "document.getElementById('open-folder').addEventListener('click',async()=>{try{await post('open_data_folder',null)}catch{}});"
        "document.getElementById('clear-diagnostics').addEventListener('click',async()=>{try{await post('clear_diagnostics',null);document.getElementById('status').textContent='"
        + html.escape(t["diagnostics_cleared"]) + "'}catch{}});"
    )
    return f'''<!doctype html><html lang="{html.escape(language)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(t['title'])}</title><style>{style}</style></head><body><main>
<h1>{html.escape(t['title'])} · Ver {html.escape(app_version)}</h1>
<section><div class="label">{html.escape(t['language'])}</div><div class="chips" style="margin-top:10px">{language_buttons}</div></section>
<section>{autostart_row}{telemetry_row}</section>
<section><div class="label">{html.escape(t['refresh_interval'])}</div><div class="chips" style="margin-top:10px">{refresh_buttons}</div></section>
<section><div class="action-row"><button class="action" id="open-folder">{html.escape(t['open_data_folder'])}</button><button class="action" id="clear-diagnostics">{html.escape(t['clear_diagnostics'])}</button></div><div class="status" id="status"></div></section>
</main><script>{script}</script></body></html>'''
