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
import webbrowser
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

import ai_usage_report
from diagnostics import diagnostic_payload, save_pending, send_diagnostic
from i18n import SUPPORTED, load_messages, system_language
from report_i18n import localize_html
from updater import latest_release, update_pricing
from help_page import write_help
from source_discovery import configure_source, doctor_report, load_configured_sources
from runtime_data import app_data_root, initialize_user_data, load_subscriptions, save_subscriptions


APP_VERSION = "0.4.0"
CONFIG_ROOT = app_data_root()
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
REPORT_PATH = CONFIG_ROOT / "ai-usage-report.html"
BASE_REPORT_PATH = CONFIG_ROOT / "ai-usage-report.base.html"
HELP_PATH = CONFIG_ROOT / "help.html"
PRICING_PATH = CONFIG_ROOT / "pricing.json"
SETTINGS_PATH = CONFIG_ROOT / "settings.json"
SUBSCRIPTIONS_PATH = CONFIG_ROOT / "subscriptions.json"
PENDING_DIAGNOSTIC = CONFIG_ROOT / "pending-diagnostic.json"
LOCAL_PORT = 17653
LANGUAGE_NAMES = {"zh-CN": "中文", "en": "English", "ja": "日本語", "ko": "한국어", "fr": "Français", "de": "Deutsch", "es": "Español"}
PLAN_PROVIDERS = {"ChatGPT": "Codex", "Claude": "Claude", "Gemini": "Gemini", "Grok": "Grok"}


def load_settings() -> dict:
    defaults = {"language": system_language(), "telemetry_consent": False, "telemetry_endpoint": "", "price_manifest_url": "", "releases_url": "", "refresh_hours": 24, "update_check_hours": 24, "onboarding_complete": False}
    try:
        loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    return {**defaults, **loaded} if isinstance(loaded, dict) else defaults


def save_settings(settings: dict) -> None:
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_runtime_files() -> None:
    initialize_user_data(RESOURCE_ROOT)


def load_runtime_pricing() -> dict:
    pricing = ai_usage_report.load_pricing(PRICING_PATH)
    pricing["subscriptions"] = load_subscriptions(SUBSCRIPTIONS_PATH)
    return pricing


def save_subscription_plan(plan: dict) -> list[dict]:
    provider, cycle = plan.get("provider"), plan.get("cycle")
    start_date, amount = plan.get("start_date"), plan.get("amount")
    if provider not in PLAN_PROVIDERS or cycle not in {"month", "year"}:
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
    field = "monthly_usd" if cycle == "month" else "annual_usd"
    entries[:] = [entry for entry in entries if not (isinstance(entry, dict) and entry.get("start_date") == start_date)]
    entries.append({"start_date": start_date, field: amount})
    entries.sort(key=lambda entry: str(entry.get("start_date", "")))
    save_subscriptions(SUBSCRIPTIONS_PATH, subscriptions)
    return ai_usage_report.subscription_plan_data(pricing)


def notify(title: str, message: str) -> None:
    if sys.platform == "darwin":
        script = "on run argv\n display notification (item 2 of argv) with title (item 1 of argv)\nend run"
        subprocess.run(["osascript", "-e", script, title, message], check=False)
    elif sys.platform == "win32":
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")
        command = f"Add-Type -AssemblyName PresentationFramework;[System.Windows.MessageBox]::Show('{safe_message}','{safe_title}')"
        subprocess.run(["powershell", "-NoProfile", "-Command", command], check=False)


class DesktopApp:
    def __init__(self) -> None:
        ensure_runtime_files()
        self.settings = load_settings()
        self.messages = load_messages(self.settings["language"])
        self.server: ThreadingHTTPServer | None = None
        self.icon: pystray.Icon | None = None

    @staticmethod
    def _icon_image() -> Image.Image:
        image = Image.new("RGBA", (64, 64), (8, 13, 24, 255))
        draw = ImageDraw.Draw(image)
        draw.line((12, 47, 25, 31, 36, 39, 52, 14), fill=(97, 168, 255, 255), width=7, joint="curve")
        return image

    def refresh(self) -> list[str]:
        try:
            pricing = load_runtime_pricing()
            usages, source_files = ai_usage_report.collect_usages(30)
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            base_report = ai_usage_report.render_dashboard(usages, 30, source_files, pricing, app_version=APP_VERSION)
            BASE_REPORT_PATH.write_text(base_report, encoding="utf-8")
            REPORT_PATH.write_text(localize_html(base_report, self.settings["language"]), encoding="utf-8")
            write_help(HELP_PATH, self.settings["language"], APP_VERSION)
            unknown = sorted({item.model for item in usages if ai_usage_report.api_equivalent_cost(item, pricing) is None})
            if unknown:
                notify(self.messages["new_model_title"], self.messages["new_model_message"].format(model=", ".join(unknown)))
            notify(self.messages["app_name"], self.messages["refresh_done"])
            return unknown
        except Exception as error:
            payload = diagnostic_payload(error, app_version=APP_VERSION, language=self.settings["language"], module="refresh")
            save_pending(payload, PENDING_DIAGNOSTIC)
            try:
                send_diagnostic(payload, self.settings["telemetry_endpoint"], self.settings["telemetry_consent"])
            except Exception:
                pass
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
        self.settings["language"] = language
        save_settings(self.settings)
        self.messages = load_messages(language)
        self.icon.title = self.messages["app_name"]
        self.icon.menu = self._menu()
        self.icon.update_menu()
        if BASE_REPORT_PATH.exists():
            REPORT_PATH.write_text(localize_html(BASE_REPORT_PATH.read_text(encoding="utf-8"), language), encoding="utf-8")
        else:
            self.refresh()
        write_help(HELP_PATH, language, APP_VERSION)

    def toggle_telemetry(self) -> None:
        self.settings["telemetry_consent"] = not self.settings["telemetry_consent"]
        save_settings(self.settings)

    def open_report(self) -> None:
        if not REPORT_PATH.exists():
            self.refresh()
        webbrowser.open(REPORT_PATH.as_uri())

    def open_help(self) -> None:
        write_help(HELP_PATH, self.settings["language"], APP_VERSION)
        webbrowser.open(f"http://127.0.0.1:{LOCAL_PORT}/help")

    def _start_http(self) -> None:
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path.startswith("/state"):
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
                    write_help(HELP_PATH, app.settings["language"], APP_VERSION)
                    body = HELP_PATH.read_bytes()
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
                if self.path not in {"/refresh", "/plans"}:
                    self.send_error(404)
                    return
                if self.headers.get("Origin", "") not in {"null", "https://token.report.test.apeai.online"}:
                    self.send_error(403)
                    return
                try:
                    if self.path == "/plans":
                        length = min(int(self.headers.get("Content-Length", "0")), 4096)
                        plan = json.loads(self.rfile.read(length))
                        body = json.dumps({"ok": True, "plans": save_subscription_plan(plan)}).encode()
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
                allowed = origin == "null" or origin == "https://token.report.test.apeai.online"
                if allowed:
                    self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

            def log_message(self, *_args) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", LOCAL_PORT), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def _schedule(self, callback, hours: int) -> None:
        def run_again() -> None:
            try:
                callback()
            finally:
                self._schedule(callback, hours)
        timer = threading.Timer(max(1, hours) * 3600, run_again)
        timer.daemon = True
        timer.start()

    def _menu(self):
        def language_item(language: str):
            return pystray.MenuItem(
                LANGUAGE_NAMES[language],
                lambda _icon, _item: self.set_language(language),
                checked=lambda _item: self.settings["language"] == language,
                radio=True,
            )
        return pystray.Menu(
            pystray.MenuItem(f"{self.messages['app_name']} Ver {APP_VERSION}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.messages["open_report"], lambda: self.open_report(), default=True),
            pystray.MenuItem(self.messages["refresh_now"], lambda: self.refresh()),
            pystray.MenuItem(self.messages["update_prices"], lambda: self.update_prices()),
            pystray.MenuItem(self.messages["check_app_update"], lambda: self.check_app_update(open_page=True)),
            pystray.MenuItem(self.messages["language"], pystray.Menu(*[language_item(language) for language in sorted(SUPPORTED)])),
            pystray.MenuItem(self.messages.get("help", "Configuration and user guide"), lambda: self.open_help()),
            pystray.MenuItem(self.messages["telemetry"], lambda: self.toggle_telemetry(), checked=lambda _item: self.settings["telemetry_consent"]),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.messages["quit"], lambda: self.stop()),
        )

    def run(self) -> None:
        self.icon = pystray.Icon("ai-subscription-usage", self._icon_image(), self.messages["app_name"])
        self._start_http()
        if not self.settings.get("onboarding_complete"):
            self.settings["onboarding_complete"] = True
            save_settings(self.settings)
            self.open_help()
        self._schedule(self.refresh, int(self.settings.get("refresh_hours", 24)))
        self._schedule(self.check_app_update, int(self.settings.get("update_check_hours", 24)))
        self.icon.menu = self._menu()
        self.icon.run()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
        self.icon.stop()


def command_line() -> bool:
    if "--refresh" in sys.argv:
        DesktopApp().refresh()
        print(json.dumps({"ok": True, "report": str(REPORT_PATH), "version": APP_VERSION}, ensure_ascii=False))
        return True
    if "--doctor" in sys.argv or "--verify-sources" in sys.argv:
        ensure_runtime_files()
        report = doctor_report()
        if "--verify-sources" in sys.argv:
            report = {"schema_version": 1, "configured_sources": load_configured_sources(), "discovered_sources": report["discovered_sources"]}
        print(json.dumps(report, ensure_ascii=False, indent=2))
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
        print(json.dumps(configure_source(args.provider, args.surface, args.format_name, args.path), ensure_ascii=False, indent=2))
        return True
    return False


if __name__ == "__main__":
    if command_line():
        pass
    elif "--self-test" in sys.argv:
        ensure_runtime_files()
        load_runtime_pricing()
        load_messages("en")
        print(f"AI Subscription Usage {APP_VERSION}: self-test passed")
    else:
        DesktopApp().run()
