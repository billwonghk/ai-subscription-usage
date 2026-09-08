#!/usr/bin/env python3
"""macOS menu-bar and Windows system-tray shell."""

from __future__ import annotations

import json
import datetime as dt
import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser
import shutil
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

if sys.platform == "darwin":
    import AppKit
    from PyObjCTools import AppHelper

import ai_usage_report
import autostart
import fx_rates
import refresh_schedule
from app_instance import AppInstance
from diagnostics import diagnostic_payload, save_pending, send_diagnostic
from i18n import SUPPORTED, load_messages, system_language
from report_i18n import localize_html
from report_view import should_open_new_report
from updater import latest_release, update_pricing
from help_page import AI_PROMPT, write_help
from settings_page import render_settings
from source_discovery import configure_source, doctor_report, load_configured_sources
from runtime_data import app_data_root, initialize_user_data, load_subscriptions, save_subscriptions


APP_VERSION = "0.5.0"
CONFIG_ROOT = app_data_root()
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
REPORT_PATH = CONFIG_ROOT / "ai-usage-report.html"
BASE_REPORT_PATH = CONFIG_ROOT / "ai-usage-report.base.html"
HELP_PATH = CONFIG_ROOT / "help.html"
PRICING_PATH = CONFIG_ROOT / "pricing.json"
SETTINGS_PATH = CONFIG_ROOT / "settings.json"
SUBSCRIPTIONS_PATH = CONFIG_ROOT / "subscriptions.json"
PENDING_DIAGNOSTIC = CONFIG_ROOT / "pending-diagnostic.json"
FX_RATES_PATH = CONFIG_ROOT / "fx-rates.json"
LOCAL_PORT = 17653
LOCAL_ORIGIN = f"http://127.0.0.1:{LOCAL_PORT}"
ALLOWED_ORIGINS = {LOCAL_ORIGIN}
PLAN_PROVIDERS = {
    "ChatGPT": "Codex", "Claude": "Claude", "Gemini": "Gemini", "Grok": "Grok",
    "MiniMax": "MiniMax", "Kimi": "Kimi", "GLM": "GLM", "阿里百炼": "Bailian",
}
PROVIDER_SETTINGS = {
    "Codex": {"label": "ChatGPT", "discovery": "chatgpt", "surface": "chatgpt-desktop"},
    "Claude Code": {"label": "Claude", "discovery": "claude", "surface": "claude-code"},
    "Gemini CLI": {"label": "Gemini", "discovery": "gemini", "surface": "gemini-cli"},
    "Grok Build": {"label": "Grok", "discovery": "grok", "surface": "grok-local"},
    "MiniMax": {"label": "MiniMax", "discovery": "minimax", "surface": "minimax-agent"},
    "Kimi": {"label": "Kimi", "discovery": "kimi", "surface": "kimi-code"},
    "GLM": {"label": "GLM", "discovery": "glm", "surface": "glm-local"},
    "Bailian": {"label": "阿里百炼", "discovery": "bailian", "surface": "bailian-local"},
}
SETTINGS_GEAR = "⚙️" if sys.platform == "darwin" else "⚙"
DEFAULT_PROVIDER_SELECTION = ("Codex", "Claude Code", "Gemini CLI", "Grok Build")


if sys.platform == "darwin":
    class AppLifecycleDelegate(AppKit.NSObject):
        """Finder reopens an existing bundle without launching another process."""

        def applicationShouldHandleReopen_hasVisibleWindows_(self, application, visible):
            threading.Thread(target=self.owner.open_report, name="finder-open-report", daemon=True).start()
            return False

        def applicationWillTerminate_(self, notification):
            self.owner.stop()

    class MacTrayIcon(pystray.Icon):
        """Use left click for the default action and right click for the menu."""

        def _update_menu(self) -> None:
            callbacks = []
            menu = self._create_menu(self.menu, callbacks)
            self._menu_handle = (menu, callbacks) if menu else None
            self._status_item.setMenu_(None)
            self._status_item.button().sendActionOn_(
                AppKit.NSEventMaskLeftMouseUp | AppKit.NSEventMaskRightMouseUp
            )

        def __call__(self) -> None:
            event = AppKit.NSApp.currentEvent()
            if event is not None and event.type() == AppKit.NSEventTypeRightMouseUp:
                if self._menu_handle:
                    self._status_item.popUpStatusItemMenu_(self._menu_handle[0])
                return
            super().__call__()
else:
    MacTrayIcon = pystray.Icon


def load_settings() -> dict:
    defaults = {"language": system_language(), "display_currency": "USD", "telemetry_consent": False, "telemetry_endpoint": "", "price_manifest_url": "https://raw.githubusercontent.com/billwonghk/ai-subscription-usage/main/config/pricing-manifest.json", "releases_url": "https://api.github.com/repos/billwonghk/ai-subscription-usage/releases/latest", "update_check_hours": 24, "onboarding_complete": False, "enabled_providers": list(DEFAULT_PROVIDER_SELECTION), "last_successful_refresh_day": ""}
    try:
        loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    if not isinstance(loaded, dict):
        return defaults
    settings = {**defaults, **loaded}
    configured = settings.get("enabled_providers")
    if not isinstance(configured, list):
        configured = list(DEFAULT_PROVIDER_SELECTION)
    settings["enabled_providers"] = [provider for provider in PROVIDER_SETTINGS if provider in configured]
    if settings.get("display_currency") not in {"USD", "CNY"}:
        settings["display_currency"] = "USD"
    return settings


def provider_states(settings: dict) -> list[dict]:
    enabled = set(settings.get("enabled_providers", PROVIDER_SETTINGS))
    detection = doctor_report()
    discovered = detection["discovered_sources"]
    statuses: dict[tuple[str, str], str] = {}
    for source in discovered:
        statuses[(source["provider"], source["surface"])] = source["status"]
    result = []
    for provider, meta in PROVIDER_SETTINGS.items():
        status = statuses.get((meta["discovery"], meta["surface"]), "not_found")
        if any(source["provider"] == meta["discovery"] for source in detection["configured_sources"]):
            status = "ready"
        result.append({"id": provider, "label": meta["label"], "enabled": provider in enabled, "status": status, "color": ai_usage_report.PROVIDER_META[provider]["color"]})
    return result


def save_settings(settings: dict) -> None:
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_runtime_files() -> None:
    initialize_user_data(RESOURCE_ROOT)


def load_runtime_pricing() -> dict:
    pricing = ai_usage_report.load_pricing(PRICING_PATH)
    pricing["subscriptions"] = load_subscriptions(SUBSCRIPTIONS_PATH)
    return pricing


def load_deepseek_tiers() -> dict[str, str]:
    try:
        raw = json.loads((RESOURCE_ROOT / "config" / "deepseek_tier_map.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {key: value for key, value in raw.items() if not key.startswith("_")}


def write_help_page(language: str) -> None:
    write_help(HELP_PATH, language, APP_VERSION, load_runtime_pricing(), load_deepseek_tiers())


def save_subscription_plan(plan: dict) -> list[dict]:
    provider, cycle = plan.get("provider"), plan.get("cycle")
    start_date, amount = plan.get("start_date"), plan.get("amount")
    currency = str(plan.get("currency", "USD")).upper()
    if provider not in PLAN_PROVIDERS or cycle not in {"month", "year"} or currency not in {"USD", "CNY"}:
        raise ValueError("unsupported plan")
    try:
        dt.date.fromisoformat(start_date)
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValueError("invalid plan") from None
    if not 0 < amount <= 1_000_000:
        raise ValueError("invalid amount")
    pricing = load_runtime_pricing()
    subscriptions = pricing.setdefault("subscriptions", {})
    key = PLAN_PROVIDERS[provider]
    subscription = subscriptions.setdefault(key, {"label": f"{provider} subscription", "plans": []})
    entries = subscription.setdefault("plans", [])
    entries[:] = [entry for entry in entries if not (isinstance(entry, dict) and entry.get("start_date") == start_date)]
    entries.append({"start_date": start_date, "amount": amount, "currency": currency, "cycle": cycle})
    entries.sort(key=lambda entry: str(entry.get("start_date", "")))
    save_subscriptions(SUBSCRIPTIONS_PATH, subscriptions)
    return ai_usage_report.subscription_plan_data(pricing)


def delete_subscription_plan(plan: dict) -> list[dict]:
    provider = plan.get("provider")
    start_date = plan.get("start_date")
    if provider not in PLAN_PROVIDERS or not isinstance(start_date, str):
        raise ValueError("unsupported plan")
    try:
        dt.date.fromisoformat(start_date)
    except ValueError:
        raise ValueError("invalid plan") from None
    pricing = load_runtime_pricing()
    subscriptions = pricing.setdefault("subscriptions", {})
    subscription = subscriptions.get(PLAN_PROVIDERS[provider])
    entries = subscription.get("plans") if isinstance(subscription, dict) else None
    if not isinstance(entries, list):
        raise ValueError("plan not found")
    remaining = [entry for entry in entries if not (isinstance(entry, dict) and entry.get("start_date") == start_date)]
    if len(remaining) == len(entries):
        raise ValueError("plan not found")
    subscription["plans"] = remaining
    save_subscriptions(SUBSCRIPTIONS_PATH, subscriptions)
    return ai_usage_report.subscription_plan_data(pricing)


def notify(title: str, message: str) -> None:
    if sys.platform == "darwin":
        script = "on run argv\n display notification (item 2 of argv) with title (item 1 of argv)\nend run"
        subprocess.run(["osascript", "-e", script, title, message], check=False)
    elif sys.platform == "win32":
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")
        command = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "Add-Type -AssemblyName System.Drawing;"
            "$n=New-Object System.Windows.Forms.NotifyIcon;"
            "$n.Icon=[System.Drawing.SystemIcons]::Information;"
            "$n.Visible=$true;"
            f"$n.ShowBalloonTip(4000,'{safe_title}','{safe_message}',[System.Windows.Forms.ToolTipIcon]::Info);"
            "Start-Sleep -Milliseconds 4200;"
            "$n.Dispose()"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", command], check=False)


def _run_on_main_thread(callback) -> None:
    """Marshal a pystray icon/menu update onto the main thread.

    pystray's macOS backend calls AppKit directly with no thread marshaling
    of its own (see pystray/_darwin.py: _update_title/_update_menu). That is
    safe when pystray itself invokes a menu callback, since AppKit delivers
    those on the main thread, but our settings page triggers changes from
    the local HTTP server's request-handler thread instead, and mutating
    NSStatusItem/NSMenu off the main thread crashes the whole process.
    Windows' pystray backend has not shown the same failure, so it is
    called directly there.
    """
    if sys.platform == "darwin":
        AppHelper.callAfter(callback)
    else:
        callback()


class DesktopApp:
    def __init__(self, instance_token: str = "") -> None:
        ensure_runtime_files()
        self.settings = load_settings()
        self.messages = load_messages(self.settings["language"])
        self.server: ThreadingHTTPServer | None = None
        self.icon: pystray.Icon | None = None
        self._daily_refresh_timer: threading.Timer | None = None
        self._startup_refresh_timer: threading.Timer | None = None
        self._refresh_lock = threading.Lock()
        self._presentation_lock = threading.RLock()
        self._lifecycle_lock = threading.RLock()
        self._stopping = threading.Event()
        self._timers: set[threading.Timer] = set()
        self._instance_token = instance_token
        self._http_thread: threading.Thread | None = None
        self._report_open_lock = threading.Lock()
        self._last_report_view = 0.0

    @staticmethod
    def _icon_image() -> Image.Image:
        asset_name = "tray-icon.ico" if sys.platform == "win32" else "tray-icon-64.png"
        asset = RESOURCE_ROOT / "assets" / asset_name
        try:
            return Image.open(asset).convert("RGBA")
        except OSError:
            image = Image.new("RGBA", (64, 64), (8, 13, 24, 255))
            draw = ImageDraw.Draw(image)
            draw.line((12, 47, 25, 31, 36, 39, 52, 14), fill=(97, 168, 255, 255), width=7, joint="curve")
            return image

    def refresh(self, notify_result: bool = True) -> list[str]:
        with self._refresh_lock:
            return self._refresh_locked(notify_result=notify_result)

    def _refresh_locked(self, notify_result: bool = True) -> list[str]:
        try:
            pricing = load_runtime_pricing()
            fx_cache = fx_rates.refresh_if_due(FX_RATES_PATH)
            enabled_providers = self.settings.get("enabled_providers", list(PROVIDER_SETTINGS))
            usages, source_files = ai_usage_report.collect_usages(30, enabled_providers=enabled_providers)
            unknown = sorted({item.model for item in usages if ai_usage_report.api_equivalent_cost(item, pricing) is None})
            newly_found = unknown
            auto_updated_version = None
            if unknown and self.settings.get("price_manifest_url"):
                try:
                    auto_updated_version = update_pricing(self.settings["price_manifest_url"], PRICING_PATH)
                    pricing = load_runtime_pricing()
                    unknown = sorted({item.model for item in usages if ai_usage_report.api_equivalent_cost(item, pricing) is None})
                except Exception:
                    auto_updated_version = None
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            base_report = ai_usage_report.render_dashboard(usages, 30, source_files, pricing, app_version=APP_VERSION, deepseek_tiers=load_deepseek_tiers(), enabled_providers=enabled_providers, display_currency=self.settings["display_currency"], fx_cache=fx_cache)
            with self._presentation_lock:
                BASE_REPORT_PATH.write_text(base_report, encoding="utf-8")
                REPORT_PATH.write_text(localize_html(base_report, self.settings["language"]), encoding="utf-8")
                write_help_page(self.settings["language"])
            self.settings["last_successful_refresh_day"] = refresh_schedule.local_day()
            save_settings(self.settings)
            if auto_updated_version and notify_result:
                notify(self.messages["app_name"], self.messages["auto_price_update_message"].format(model=", ".join(newly_found), version=auto_updated_version))
            if unknown and notify_result:
                notify(self.messages["new_model_title"], self.messages["new_model_message"].format(model=", ".join(unknown)))
            if notify_result:
                notify(self.messages["app_name"], self.messages["refresh_done"])
            return unknown
        except Exception as error:
            payload = diagnostic_payload(error, app_version=APP_VERSION, language=self.settings["language"], module="refresh")
            save_pending(payload, PENDING_DIAGNOSTIC)
            try:
                send_diagnostic(payload, self.settings["telemetry_endpoint"], self.settings["telemetry_consent"])
            except Exception:
                pass
            if notify_result:
                notify(self.messages["error_title"], self.messages["refresh_failed"])
            raise

    def update_prices(self) -> None:
        try:
            version = update_pricing(self.settings["price_manifest_url"], PRICING_PATH)
            notify(self.messages["app_name"], self.messages["price_updated"].format(version=version))
            self.refresh()
        except Exception as error:
            payload = diagnostic_payload(error, app_version=APP_VERSION, language=self.settings["language"], module="price_update")
            save_pending(payload, PENDING_DIAGNOSTIC)
            notify(self.messages["error_title"], self.messages["price_update_failed"])

    def check_app_update(self, open_page: bool = False) -> None:
        try:
            release = latest_release(self.settings["releases_url"], APP_VERSION)
            if release:
                notify(self.messages["app_name"], self.messages["app_update_available"].format(version=release["version"]))
                if open_page:
                    webbrowser.open(release["url"])
            else:
                notify(self.messages["app_name"], self.messages["app_up_to_date"])
        except Exception as error:
            save_pending(diagnostic_payload(error, app_version=APP_VERSION, language=self.settings["language"], module="app_update"), PENDING_DIAGNOSTIC)
            notify(self.messages["error_title"], self.messages["app_update_failed"])

    def set_language(self, language: str) -> None:
        if language not in SUPPORTED:
            raise ValueError("unsupported language")
        # Do not wait for log scanning/network requests to switch presentation.
        # The refresh writer takes this same short lock and uses the new language.
        with self._presentation_lock:
            self.settings["language"] = language
            save_settings(self.settings)
            self.messages = load_messages(language)
            if BASE_REPORT_PATH.exists():
                REPORT_PATH.write_text(localize_html(BASE_REPORT_PATH.read_text(encoding="utf-8"), language), encoding="utf-8")
            write_help_page(language)
        if self.icon is not None:
            _run_on_main_thread(self._refresh_icon_menu)

    def _refresh_icon_menu(self) -> None:
        self.icon.title = self.messages["app_name"]
        self.icon.menu = self._menu()
        self.icon.update_menu()

    def toggle_telemetry(self) -> None:
        self.settings["telemetry_consent"] = not self.settings["telemetry_consent"]
        save_settings(self.settings)

    def open_data_folder(self) -> None:
        if sys.platform == "darwin":
            subprocess.run(["open", str(CONFIG_ROOT)], check=False)
        elif sys.platform == "win32":
            os.startfile(str(CONFIG_ROOT))  # noqa: S606

    def toggle_provider(self, provider: str) -> bool:
        if provider not in PROVIDER_SETTINGS:
            raise ValueError("unsupported provider")
        enabled = list(self.settings.get("enabled_providers", PROVIDER_SETTINGS))
        if provider in enabled:
            enabled.remove(provider)
        else:
            enabled.append(provider)
        self.settings["enabled_providers"] = [item for item in PROVIDER_SETTINGS if item in enabled]
        save_settings(self.settings)
        threading.Thread(target=self.refresh, name="provider-refresh", daemon=True).start()
        return provider in self.settings["enabled_providers"]

    def clear_diagnostics(self) -> None:
        if PENDING_DIAGNOSTIC.exists():
            PENDING_DIAGNOSTIC.unlink()
        notify(self.messages["app_name"], self.messages["diagnostics_cleared"])

    def open_report(self) -> None:
        with self._report_open_lock:
            self._open_report_locked()

    def _open_report_locked(self) -> None:
        if self._stopping.is_set():
            return
        if not REPORT_PATH.exists():
            self.refresh()
        if should_open_new_report(self._last_report_view):
            self._last_report_view = time.monotonic()
            webbrowser.open(f"http://127.0.0.1:{LOCAL_PORT}/report")

    def open_help(self) -> None:
        write_help_page(self.settings["language"])
        webbrowser.open(f"http://127.0.0.1:{LOCAL_PORT}/help")

    def open_settings(self) -> None:
        webbrowser.open(f"http://127.0.0.1:{LOCAL_PORT}/settings")

    def _start_http(self) -> None:
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path.startswith("/state"):
                    if "page=report" in self.path:
                        app._last_report_view = time.monotonic()
                    body = json.dumps({
                        "language": app.settings["language"],
                        "report_version": REPORT_PATH.stat().st_mtime_ns if REPORT_PATH.exists() else 0,
                    }).encode()
                    self.send_response(200)
                    self._cors()
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if self.path.startswith("/help"):
                    write_help_page(app.settings["language"])
                    body = HELP_PATH.read_bytes()
                    self.send_response(200)
                    self._cors()
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if self.path.startswith("/settings"):
                    plans = ai_usage_report.subscription_plan_data(load_runtime_pricing())
                    body = render_settings(app.settings["language"], app.settings, autostart.is_enabled(), autostart.is_supported(), APP_VERSION, provider_states(app.settings), AI_PROMPT, plans).encode()
                    self.send_response(200)
                    self._cors()
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if not self.path.startswith("/report") or not REPORT_PATH.exists():
                    self.send_error(404)
                    return
                app._last_report_view = time.monotonic()
                body = REPORT_PATH.read_bytes()
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self) -> None:
                self.send_response(204)
                self._cors()
                self.end_headers()

            def do_POST(self) -> None:
                if self.path in {"/instance/activate", "/instance/quit"}:
                    supplied = self.headers.get("X-App-Instance", "")
                    if not app._instance_token or not secrets.compare_digest(supplied.encode(), app._instance_token.encode()):
                        self.send_error(403)
                        return
                    self.send_response(200)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    if self.path.endswith("/quit"):
                        _run_on_main_thread(app.stop)
                    else:
                        threading.Thread(target=app.open_report, name="activate-report", daemon=True).start()
                    return
                if self.path not in {"/refresh", "/plans", "/settings"}:
                    self.send_error(404)
                    return
                if self.headers.get("Origin", "") not in ALLOWED_ORIGINS:
                    self.send_error(403)
                    return
                try:
                    payload = None
                    if self.path in {"/plans", "/settings"}:
                        length = int(self.headers.get("Content-Length", "0"))
                        if not 0 < length <= 4096:
                            raise ValueError("invalid request size")
                        payload = json.loads(self.rfile.read(length))
                        if not isinstance(payload, dict):
                            raise ValueError("request must be an object")
                    if self.path == "/plans":
                        saved_plans = save_subscription_plan(payload)
                        app.refresh()
                        body = json.dumps({"ok": True, "plans": saved_plans}).encode()
                    elif self.path == "/settings":
                        action, value = payload.get("action"), payload.get("value")
                        if action == "set_language" and isinstance(value, str) and value in SUPPORTED:
                            app.set_language(value)
                        elif action == "set_autostart" and isinstance(value, bool) and autostart.is_supported():
                            autostart.set_enabled(bool(value), Path(sys.executable))
                        elif action == "set_telemetry" and isinstance(value, bool):
                            app.settings["telemetry_consent"] = bool(value)
                            save_settings(app.settings)
                        elif action == "set_display_currency" and isinstance(value, str) and value in {"USD", "CNY"}:
                            app.settings["display_currency"] = value
                            save_settings(app.settings)
                        elif action == "toggle_provider" and isinstance(value, str):
                            enabled = app.toggle_provider(value)
                            body = json.dumps({"ok": True, "provider": value, "enabled": enabled}).encode()
                        elif action == "open_data_folder":
                            app.open_data_folder()
                        elif action == "clear_diagnostics":
                            app.clear_diagnostics()
                        elif action == "delete_plan" and isinstance(value, dict):
                            delete_subscription_plan(value)
                            app.refresh()
                        else:
                            raise ValueError("unsupported settings action or value")
                        if action != "toggle_provider":
                            body = json.dumps({"ok": True}).encode()
                    else:
                        unknown = app.refresh()
                        body = json.dumps({"ok": True, "unpriced_models": unknown}).encode()
                    self.send_response(200)
                except (OSError, ValueError, json.JSONDecodeError):
                    body = json.dumps({"ok": False}).encode()
                    self.send_response(400)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _cors(self) -> None:
                origin = self.headers.get("Origin", "")
                if origin in ALLOWED_ORIGINS:
                    self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

            def log_message(self, *_args) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", LOCAL_PORT), Handler)
        self._http_thread = threading.Thread(target=self.server.serve_forever, name="local-report", daemon=True)
        self._http_thread.start()

    def _start_timer(self, delay: float, callback) -> threading.Timer | None:
        with self._lifecycle_lock:
            if self._stopping.is_set():
                return None
            def invoke() -> None:
                try:
                    if not self._stopping.is_set():
                        callback()
                finally:
                    with self._lifecycle_lock:
                        self._timers.discard(timer)
            timer = threading.Timer(delay, invoke)
            timer.daemon = True
            self._timers.add(timer)
            timer.start()
            return timer

    def _schedule(self, callback, hours: int) -> None:
        def run_again() -> None:
            try:
                callback()
            finally:
                self._schedule(callback, hours)
        self._start_timer(max(1, hours) * 3600, run_again)

    def _refresh_if_due(self) -> None:
        with self._refresh_lock:
            if self._stopping.is_set():
                return
            if refresh_schedule.refreshed_today(self.settings.get("last_successful_refresh_day")):
                return
            self._refresh_locked(notify_result=False)

    def _schedule_daily_refresh(self) -> None:
        def run_again() -> None:
            try:
                self._refresh_if_due()
            finally:
                self._schedule_daily_refresh()
        self._daily_refresh_timer = self._start_timer(refresh_schedule.seconds_until_daily_refresh(), run_again)

    def _schedule_startup_refresh(self) -> None:
        self._startup_refresh_timer = self._start_timer(refresh_schedule.STARTUP_REFRESH_DELAY_SECONDS, self._refresh_if_due)

    def _menu(self):
        return pystray.Menu(
            pystray.MenuItem(f"{self.messages['app_name']} Ver {APP_VERSION}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.messages["open_report"], lambda: self.open_report(), default=True),
            pystray.MenuItem(self.messages["refresh_now"], lambda: self.refresh()),
            pystray.MenuItem(self.messages["update_prices"], lambda: self.update_prices()),
            pystray.MenuItem(self.messages["check_app_update"], lambda: self.check_app_update(open_page=True)),
            pystray.MenuItem(f"{self.messages['settings']} {SETTINGS_GEAR}", lambda: self.open_settings()),
            pystray.MenuItem(self.messages.get("help", "Configuration and user guide"), lambda: self.open_help()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.messages["quit"], lambda: self.stop()),
        )

    def run(self) -> None:
        self.icon = MacTrayIcon("ai-subscription-usage", self._icon_image(), self.messages["app_name"])
        try:
            if sys.platform == "darwin":
                self._app_delegate = AppLifecycleDelegate.alloc().init()
                self._app_delegate.owner = self
                AppKit.NSApplication.sharedApplication().setDelegate_(self._app_delegate)
            self._start_http()
            if not self.settings.get("onboarding_complete"):
                self.settings["onboarding_complete"] = True
                save_settings(self.settings)
                self.open_report()
            self._schedule_daily_refresh()
            self._schedule_startup_refresh()
            self._schedule(self.check_app_update, int(self.settings.get("update_check_hours", 24)))
            self.icon.menu = self._menu()
            self.icon.run()
        finally:
            self.stop()

    def stop(self) -> None:
        with self._lifecycle_lock:
            if self._stopping.is_set():
                return
            self._stopping.set()
            for timer in self._timers:
                timer.cancel()
            self._timers.clear()
        try:
            if self.server:
                try:
                    if self._http_thread and self._http_thread.is_alive():
                        self.server.shutdown()
                        self._http_thread.join(timeout=2)
                finally:
                    self.server.server_close()
                    self.server = None
        finally:
            if self.icon:
                self.icon.stop()


def launch_desktop(quit_running: bool = False) -> int:
    instance = AppInstance(CONFIG_ROOT, LOCAL_PORT)
    try:
        if not instance.acquire():
            if instance.signal_existing('quit' if quit_running else 'activate'):
                return 0
            notify('AI Subscription Usage', '已有应用正在启动或退出，请稍后重试。 / The application is starting or exiting. Please retry shortly.')
            return 1
        if quit_running:
            return 0
        DesktopApp(instance.token).run()
        return 0
    except OSError as error:
        import errno
        if error.errno == errno.EADDRINUSE or getattr(error, 'winerror', None) == 10048:
            notify('AI Subscription Usage', '本机报表入口被其他程序或旧版应用占用，本次未启动第二个应用。请退出旧版应用后重试。 / The local report address is occupied by another program or an older app. No second instance was started. Quit the older app and retry.')
            return 1
        raise
    finally:
        instance.close()


def command_line() -> bool:
    if "--refresh" in sys.argv:
        DesktopApp().refresh()
        print(json.dumps({"ok": True, "report": str(REPORT_PATH), "version": APP_VERSION}, ensure_ascii=True))
        return True
    if "--doctor" in sys.argv or "--verify-sources" in sys.argv:
        ensure_runtime_files()
        report = doctor_report()
        if "--verify-sources" in sys.argv:
            report = {"schema_version": 1, "configured_sources": load_configured_sources(), "discovered_sources": report["discovered_sources"]}
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return True
    if "--configure-source" in sys.argv:
        ensure_runtime_files()
        parser = argparse.ArgumentParser(prog="AI Subscription Usage --configure-source")
        parser.add_argument("--configure-source", action="store_true")
        parser.add_argument("--provider", required=True)
        parser.add_argument("--surface", required=True)
        parser.add_argument("--format", required=True, dest="format_name")
        parser.add_argument("--path", required=True)
        args = parser.parse_args()
        print(json.dumps(configure_source(args.provider, args.surface, args.format_name, args.path), ensure_ascii=True, indent=2))
        return True
    return False


if __name__ == "__main__":
    if "--quit-running" in sys.argv:
        sys.exit(launch_desktop(quit_running=True))
    elif command_line():
        pass
    elif "--self-test" in sys.argv:
        ensure_runtime_files()
        load_runtime_pricing()
        load_messages("en")
        print(f"AI Subscription Usage {APP_VERSION}: self-test passed")
    else:
        sys.exit(launch_desktop())
