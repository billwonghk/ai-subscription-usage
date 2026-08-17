import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ai_usage_report as report
from report_i18n import localize_html
from help_page import render_help
from source_discovery import validate_source


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.since = dt.date(2026, 8, 1)

    def test_gemini_cli_message_tokens(self):
        with tempfile.TemporaryDirectory() as temporary:
            chats = Path(temporary) / "project" / "chats"
            chats.mkdir(parents=True)
            (chats / "session.json").write_text(json.dumps({
                "messages": [{
                    "type": "gemini",
                    "model": "gemini-test",
                    "timestamp": "2026-08-10T12:00:00Z",
                    "tokens": {"input": 100, "output": 20, "cached": 60, "thoughts": 5}
                }]
            }), encoding="utf-8")
            usages, files_read = report.parse_gemini_cli(Path(temporary), self.since)
        self.assertEqual(files_read, 1)
        self.assertEqual(len(usages), 1)
        self.assertEqual(usages[0].input_tokens, 100)
        self.assertEqual(usages[0].output_tokens, 25)
        self.assertEqual(usages[0].cached_input_tokens, 60)
        self.assertEqual(usages[0].total_tokens, 125)

    def test_grok_context_snapshot_is_estimate(self):
        with tempfile.TemporaryDirectory() as temporary:
            session = Path(temporary) / "cwd" / "session"
            session.mkdir(parents=True)
            (session / "summary.json").write_text(json.dumps({
                "updated_at": "2026-08-11T12:00:00Z",
                "current_model_id": "grok-build"
            }), encoding="utf-8")
            (session / "signals.json").write_text(json.dumps({
                "contextTokensUsed": 5120,
                "primaryModelId": "grok-build"
            }), encoding="utf-8")
            usages, files_read = report.parse_grok_build(Path(temporary), self.since)
        self.assertEqual(files_read, 1)
        self.assertEqual(len(usages), 1)
        self.assertTrue(usages[0].is_estimate)
        self.assertEqual(usages[0].input_tokens, 5120)

    def test_grok_reasoning_tokens_are_not_double_counted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "logs" / "unified.jsonl"
            path.parent.mkdir(parents=True)
            record = {
                "ts": "2026-08-10T12:00:00Z",
                "msg": "shell.turn.inference_done",
                "model": "grok-4.5",
                "ctx": {
                    "prompt_tokens": 349041,
                    "cached_prompt_tokens": 348160,
                    "completion_tokens": 2807,
                    "reasoning_tokens": 2804,
                },
            }
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            usages, files_read = report.parse_grok_build(Path(temporary), self.since)
        self.assertEqual(files_read, 1)
        self.assertEqual(len(usages), 1)
        self.assertEqual(usages[0].output_tokens, 2807)
        self.assertEqual(usages[0].input_tokens, 349041)
        self.assertEqual(usages[0].cached_input_tokens, 348160)

    def test_grok_updates_jsonl_is_preferred_over_unified_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "logs").mkdir(parents=True)
            (root / "logs" / "unified.jsonl").write_text(json.dumps({
                "ts": "2026-08-10T12:00:00Z",
                "msg": "shell.turn.inference_done",
                "ctx": {"prompt_tokens": 999, "completion_tokens": 999},
            }) + "\n", encoding="utf-8")
            session = root / "sessions" / "cwd" / "session-id"
            session.mkdir(parents=True)
            (session / "updates.jsonl").write_text(json.dumps({
                "sessionUpdate": "turn_completed",
                "ts": "2026-08-10T12:00:00Z",
                "usage": {
                    "inputTokens": 100,
                    "outputTokens": 20,
                    "cachedReadTokens": 10,
                    "reasoningTokens": 18,
                    "modelUsage": {"grok-4.5": {}},
                },
            }) + "\n", encoding="utf-8")
            usages, files_read = report.parse_grok_build(root, self.since)
        self.assertEqual(files_read, 1)
        self.assertEqual(len(usages), 1)
        self.assertEqual(usages[0].model, "grok-4.5")
        self.assertEqual(usages[0].input_tokens, 100)
        self.assertEqual(usages[0].output_tokens, 20)
        self.assertEqual(usages[0].cached_input_tokens, 10)

    def test_codex_cache_is_not_added_twice(self):
        usage = report.Usage("Codex", "gpt-5.6-terra", "2026-08-10", 100, 20, 60, True)
        self.assertEqual(usage.total_tokens, 120)

    def test_dashboard_aggregates_all_providers_and_builds_provider_details(self):
        usages = [
            report.Usage("Codex", "gpt-test", "2026-08-10", 100, 20, 40, True),
            report.Usage("Claude Code", "claude-test", "2026-08-10", 50, 10, 5),
            report.Usage("Gemini CLI", "gemini-test", "2026-08-10", 30, 5, 10, True),
            report.Usage("Grok Build", "grok-test", "2026-08-10", 80, 0, 0, is_estimate=True),
        ]
        page = report.render_dashboard(
            usages,
            30,
            {"Codex": 1, "Claude Code": 1, "Gemini CLI": 1, "Grok Build": 1},
            {"models": {}, "subscriptions": {}},
        )
        self.assertIn('>300<', page)
        self.assertIn('>260<', page)
        self.assertIn('>35<', page)
        self.assertIn('"id": "Claude Code"', page)
        self.assertIn('"label": "ChatGPT"', page)
        self.assertNotIn('"label": "ChatGPT / Codex"', page)
        self.assertIn('"id": "Gemini CLI"', page)
        self.assertIn('"label": "Gemini"', page)
        self.assertNotIn('"label": "Gemini / Antigravity"', page)
        self.assertIn('"id": "Grok Build"', page)
        self.assertIn("当天 API 等价价值 ÷ 当天订阅日成本", page)
        self.assertIn("p.start_date<=date", page)
        self.assertNotIn("||same[0]", page)
        self.assertIn("i%3===0", page)
        self.assertIn("focusProvider", page)
        self.assertIn("hit-area", page)
        self.assertIn("summary-api", page)
        self.assertIn("summary-sub", page)
        self.assertIn("summary-ratio", page)
        self.assertIn("refresh-local", page)
        self.assertIn('href="http://127.0.0.1:17653/help"', page)
        self.assertIn("Ver development", page)
        self.assertNotIn("读取文件</div>", page)


    def test_non_codex_model_can_use_an_exact_price(self):
        usage = report.Usage("Claude Code", "claude-test", "2026-08-10", 100, 20, 10)
        pricing = {"models": {"claude-test": {
            "input_per_million": 2,
            "cached_input_per_million": 1,
            "output_per_million": 4,
        }}}
        self.assertAlmostEqual(report.api_equivalent_cost(usage, pricing), 0.00029)

    def test_claude_cache_reads_and_writes_use_distinct_prices(self):
        usage = report.Usage("Claude Code", "claude-test", "2026-08-10", 100, 20, 10, cache_write_input_tokens=5)
        pricing = {"models": {"claude-test": {
            "input_per_million": 2,
            "cached_input_per_million": 0.2,
            "cache_write_input_per_million": 2.5,
            "output_per_million": 10,
        }}}
        self.assertEqual(usage.total_tokens, 135)
        self.assertAlmostEqual(report.api_equivalent_cost(usage, pricing), 0.0004145)

    def test_dated_price_period_is_selected_by_usage_date(self):
        pricing = {"models": {"claude-sonnet-5": {"periods": [
            {"start_date": "2026-06-30", "end_date": "2026-08-31", "input_per_million": 2, "cached_input_per_million": .2, "output_per_million": 10},
            {"start_date": "2026-09-01", "input_per_million": 3, "cached_input_per_million": .3, "output_per_million": 15},
        ]}}}
        august = report.Usage("Claude Code", "claude-sonnet-5", "2026-08-10", 1_000_000)
        september = report.Usage("Claude Code", "claude-sonnet-5", "2026-09-10", 1_000_000)
        self.assertEqual(report.api_equivalent_cost(august, pricing), 2)
        self.assertEqual(report.api_equivalent_cost(september, pricing), 3)

    def test_subscription_plans_include_monthly_and_annual_providers(self):
        pricing = {"subscriptions": {
            "Codex": {"plans": [{"start_date": "2026-07-12", "monthly_usd": 20}]},
            "Claude": {"plans": [{"start_date": "2026-03-13", "annual_usd": 215}]},
        }}
        self.assertEqual(report.subscription_plan_data(pricing), [
            {"provider": "ChatGPT", "start_date": "2026-07-12", "amount": 20.0, "cycle": "month"},
            {"provider": "Claude", "start_date": "2026-03-13", "amount": 215.0, "cycle": "year"},
        ])

    def test_report_localization_keeps_calculations_and_translates_ui(self):
        page = localize_html('<html lang="zh-CN">最近 30 天 总 Token 更新本机数据</html>', "en")
        self.assertIn('lang="en"', page)
        self.assertIn("Last 30 days", page)
        self.assertIn("Total tokens", page)
        self.assertIn("Refresh local data", page)

    def test_claude_repeated_message_id_is_counted_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "session.jsonl"
            record = {
                "type": "assistant",
                "timestamp": "2026-08-10T12:00:00Z",
                "message": {"id": "msg_same_response", "model": "claude-test", "usage": {
                    "input_tokens": 10, "output_tokens": 20,
                    "cache_read_input_tokens": 30, "cache_creation_input_tokens": 40,
                }},
            }
            path.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n", encoding="utf-8")
            usages, files = report.parse_claude_code(Path(temporary), self.since)
        self.assertEqual(files, 1)
        self.assertEqual(len(usages), 1)
        self.assertEqual(usages[0].total_tokens, 100)

    def test_source_configuration_rejects_unknown_format(self):
        with self.assertRaises(ValueError):
            validate_source({"provider": "chatgpt", "surface": "chatgpt-desktop", "format": "shell-script", "path": str(Path.home())})

    def test_help_page_is_localized_and_contains_safe_commands(self):
        for language in ("zh-CN", "en", "ja", "ko", "fr", "de", "es"):
            page = render_help(language)
            self.assertIn(f'lang="{language}"', page)
            self.assertIn("--doctor --json", page)
            self.assertIn("--configure-source", page)
            self.assertNotIn("Auth Token</pre>", page)
            self.assertIn("development", page)
        self.assertIn("本机检测结果", render_help("zh-CN"))
        self.assertIn("現在の検出結果", render_help("ja"))
        self.assertIn("현재 감지 결과", render_help("ko"))
        self.assertIn("Détection actuelle", render_help("fr"))
        self.assertIn("Aktuelle Erkennung", render_help("de"))
        self.assertIn("Detección actual", render_help("es"))


if __name__ == "__main__":
    unittest.main()
