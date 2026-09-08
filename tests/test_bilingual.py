import json
import ast
import threading
import tempfile
from types import SimpleNamespace
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_usage_report import render_dashboard
from report_i18n import localize_html
from settings_page import render_settings
from help_page import render_help
from updater import validate_pricing


class BilingualTests(unittest.TestCase):
    def test_switch_saves_without_scanning_or_waiting_for_refresh(self):
        # Exercise the production method without loading a native tray backend.
        source = Path(__file__).resolve().parents[1] / 'src/desktop_app.py'
        tree = ast.parse(source.read_text())
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'set_language')
        with tempfile.TemporaryDirectory() as directory:
            base, target = Path(directory) / 'base.html', Path(directory) / 'report.html'
            base.write_text('<html lang="zh-CN">订阅 AI 用量报表</html>')
            scope = {'SUPPORTED': {'en', 'zh-CN'}, 'save_settings': Mock(), 'load_messages': lambda lang: {'language': lang},
                     'BASE_REPORT_PATH': base, 'REPORT_PATH': target, 'localize_html': localize_html, 'write_help_page': Mock()}
            exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), scope)
            app = SimpleNamespace(settings={}, _presentation_lock=threading.RLock(), icon=None, refresh=Mock())
            for language in ('en', 'zh-CN'):
                scope['set_language'](app, language)
                self.assertIn('lang="' + language + '"', target.read_text())
                self.assertEqual(app.settings['language'], language)
            base.unlink()
            scope['set_language'](app, 'en')
            app.refresh.assert_not_called()
            with self.assertRaises(ValueError):
                scope['set_language'](app, 'invalid')

    def test_report_translates_presentation_not_identifiers(self):
        base = render_dashboard([], 1, {}, {'models': {}, 'subscriptions': {}}, enabled_providers=[])
        en = localize_html(base, 'en')
        self.assertIn('Display currency', en)
        self.assertIn('Exchange rate source: ECB', en)
        self.assertIn('priced portion only', en)
        self.assertEqual(localize_html(base, 'zh-CN'), base)
        payload = {'providers': [{'id': '百炼', 'plan': '阿里百炼', 'label': '阿里百炼'}],
                   'plans': [{'provider': '阿里百炼'}], 'model': '模型未计价'}
        translated = localize_html('const DATA=' + json.dumps(payload, ensure_ascii=False) + ';const $=x;', 'en')
        actual = json.loads(re.search(r'const DATA=(.*?);const \$=', translated).group(1))
        self.assertEqual(actual['providers'][0]['label'], 'Alibaba Bailian')
        actual['providers'][0]['label'] = '阿里百炼'
        self.assertEqual(actual, payload)

    def test_settings_switches_and_preserves_delete_key(self):
        plan = {'provider': '阿里百炼', 'start_date': '2026-09-01', 'amount': 40, 'currency': 'CNY', 'cycle': 'month'}
        en = render_settings('en', {}, False, False, subscription_plans=[plan])
        self.assertIn('aria-pressed="true" data-action="set_language" data-value="en"', en)
        self.assertIn('<strong>Alibaba Bailian</strong>', en)
        self.assertIn('data-provider="阿里百炼"', en)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for JavaScript syntax checks')
    def test_rendered_scripts_compile_in_both_languages(self):
        for language in ('zh-CN', 'en'):
            with patch('help_page.doctor_report', return_value={'discovered_sources': []}):
                pages = [localize_html(render_dashboard([], 1, {}, {'models': {}, 'subscriptions': {}}, enabled_providers=[]), language),
                         render_settings(language, {}, False, False),
                         render_help(language, pricing={'models': {}}, deepseek_tiers={})]
            for page in pages:
                for script in re.findall(r'<script>(.*?)</script>', page, re.S):
                    result = subprocess.run(['node', '--check'], input=script, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


class PricingValidationTests(unittest.TestCase):
    def rate(self, **changes):
        return dict(input_per_million=1, cached_input_per_million=.1, output_per_million=3, **changes)

    def test_rejects_nonfinite_boolean_and_negative_cache_prices(self):
        for value in (True, float('inf'), float('nan'), -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_pricing({'price_version': 'test', 'models': {'x': self.rate(cache_write_input_per_million=value)}})

    def test_rejects_overlapping_or_invalid_periods(self):
        for periods in ([self.rate(start_date='bad')],
                        [self.rate(start_date='2026-09-01'), self.rate(start_date='2026-09-02')],
                        [self.rate(start_date='2026-09-02', end_date='2026-09-01')]):
            with self.subTest(periods=periods), self.assertRaises(ValueError):
                validate_pricing({'price_version': 'test', 'models': {'x': {'periods': periods}}})

    def test_current_database_passes(self):
        path = Path(__file__).resolve().parents[1] / 'config/pricing.json'
        validate_pricing(json.loads(path.read_text()))
