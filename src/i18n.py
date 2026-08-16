"""Small dependency-free locale loader for the desktop shell."""

from __future__ import annotations

import json
import locale
import sys
from pathlib import Path


RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
LOCALE_ROOT = RESOURCE_ROOT / "locales"
SUPPORTED = {"zh-CN", "en", "ja", "ko", "fr", "de", "es"}
MODEL_PRICING_LABELS = {
    "zh-CN": "更新模型价格",
    "en": "Update model pricing",
    "ja": "モデル価格を更新",
    "ko": "모델 가격 업데이트",
    "fr": "Mettre à jour les tarifs des modèles",
    "de": "Modellpreise aktualisieren",
    "es": "Actualizar precios de modelos",
}
HELP_LABELS = {
    "zh-CN": "配置及使用说明", "en": "Configuration and user guide", "ja": "設定・使用ガイド",
    "ko": "구성 및 사용 안내", "fr": "Configuration et guide", "de": "Konfiguration und Anleitung",
    "es": "Configuración y guía",
}


def system_language() -> str:
    language = (locale.getlocale()[0] or "en").replace("_", "-")
    if language.lower().startswith("zh"):
        return "zh-CN"
    short = language.split("-")[0]
    return short if short in SUPPORTED else "en"


def load_messages(language: str | None = None) -> dict[str, str]:
    selected = language if language in SUPPORTED else system_language()
    path = LOCALE_ROOT / f"{selected}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = json.loads((LOCALE_ROOT / "en.json").read_text(encoding="utf-8"))
    messages = {str(key): str(value) for key, value in data.items()}
    messages["update_prices"] = MODEL_PRICING_LABELS[selected]
    messages["help"] = HELP_LABELS[selected]
    return messages
