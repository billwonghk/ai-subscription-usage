import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ai_usage_report as report
import fx_rates
from report_i18n import localize_html
from help_page import render_help
from settings_page import render_settings
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
        self.assertIn("(DATA.days.length-1-i)%3===0", page)
        self.assertIn("（今日）", page)
        self.assertIn("focusProvider", page)
        self.assertIn("hit-area", page)
        self.assertIn("summary-api", page)
        self.assertIn("summary-sub", page)
        self.assertIn("summary-ratio", page)
        self.assertIn("refresh-local", page)
        self.assertIn('href="http://127.0.0.1:17653/help"', page)
        self.assertIn("Ver development", page)
        self.assertNotIn("读取文件</div>", page)

    def test_dashboard_only_serializes_enabled_providers(self):
        usages = [
            report.Usage("Codex", "gpt-test", "2026-08-10", 100, 20),
            report.Usage("Claude Code", "claude-test", "2026-08-10", 50, 10),
        ]
        page = report.render_dashboard(
            usages,
            30,
            {"Codex": 1, "Claude Code": 1},
            {"models": {}, "subscriptions": {}},
            enabled_providers=["Codex"],
        )
        self.assertIn('"id": "Codex"', page)
        self.assertNotIn('"id": "Claude Code"', page)
        self.assertNotIn("claude-test", page)
        self.assertIn("gridTemplateColumns", page)

    def test_collect_usages_skips_every_parser_when_no_provider_is_enabled(self):
        usages, source_files = report.collect_usages(30, enabled_providers=[])
        self.assertEqual(usages, [])
        self.assertEqual(source_files, {
            "Codex": 0, "Claude Code": 0, "Gemini CLI": 0, "Grok Build": 0,
            "MiniMax": 0, "Kimi": 0, "GLM": 0, "Bailian": 0,
        })

    def test_minimax_reads_only_accounting_table(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "sqlite.db"
            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE token_usage (model TEXT, ts INTEGER, input_tokens INTEGER, "
                "output_tokens INTEGER, reasoning_tokens INTEGER, cache_read_tokens INTEGER, "
                "cache_write_tokens INTEGER, raw TEXT)"
            )
            timestamp = int(dt.datetime(2026, 8, 10, 12).timestamp() * 1000)
            connection.execute(
                "INSERT INTO token_usage VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("minimax/MiniMax-M3", timestamp, 100, 20, 5, 60, 10, "private conversation content"),
            )
            connection.commit()
            connection.close()
            usages, files_read = report.parse_minimax(database, self.since)
        self.assertEqual(files_read, 1)
        self.assertEqual(len(usages), 1)
        self.assertEqual(usages[0].input_tokens, 100)
        self.assertEqual(usages[0].output_tokens, 25)
        self.assertEqual(usages[0].cached_input_tokens, 60)
        self.assertEqual(usages[0].cache_write_input_tokens, 10)
        self.assertEqual(usages[0].total_tokens, 195)

    def test_settings_page_lists_provider_controls_and_safe_ai_prompt(self):
        page = render_settings(
            "zh-CN",
            {"refresh_hours": 24, "telemetry_consent": False},
            False,
            True,
            provider_states=[{"id": "Codex", "label": "ChatGPT", "enabled": True, "status": "ready"}],
            setup_prompt="Do not read OAuth or conversation content.",
            subscription_plans=[{"provider": "MiniMax", "start_date": "2026-04-23", "amount": 431.0, "currency": "CNY", "cycle": "year"}],
        )
        self.assertIn("监控平台", page)
        self.assertIn('data-action="toggle_provider"', page)
        self.assertIn("Do not read OAuth or conversation content.", page)
        self.assertIn("已添加 · 本机记录将纳入统计", page)
        self.assertIn("sessionStorage.setItem('settingsNotice'", page)
        self.assertIn("document.execCommand('copy')", page)
        self.assertIn("订阅计划管理", page)
        self.assertIn("MiniMax", page)
        self.assertIn("431.0 CNY / 年", page)
        self.assertIn('class="danger delete-plan"', page)
        self.assertIn("delete_plan", page)

        available_page = render_settings(
            "zh-CN",
            {"refresh_hours": 24, "telemetry_consent": False},
            False,
            True,
            provider_states=[{"id": "MiniMax", "label": "MiniMax", "enabled": False, "status": "ready"}],
            setup_prompt="Configure only this provider.",
        )
        self.assertIn("已找到本机记录 · 添加后才会纳入统计", available_page)
        self.assertNotIn("<span class=\"provider-badge\">已添加</span>", available_page)

    def test_dashboard_includes_cache_hit_rate_and_deepseek_comparison(self):
        usages = [report.Usage("Codex", "gpt-test", "2026-08-10", 100, 20, 60, True)]
        pricing = {"models": {"deepseek-v4-flash": {
            "input_per_million": 1, "cached_input_per_million": 0.1, "output_per_million": 5,
        }}, "subscriptions": {}}
        page = report.render_dashboard(usages, 30, {"Codex": 1}, pricing, deepseek_tiers={"gpt-test": "flash"})
        self.assertIn('"cache_hit_rate": 0.6', page)
        self.assertIn('"deepseek_cost": 0.000146', page)
        self.assertIn("缓存命中率", page)
        self.assertIn("对应 DeepSeek 成本", page)
        self.assertIn("对应 DeepSeek", page)  # per-model table column header
        self.assertIn('"deepseek_tier": "flash"', page)

    def test_model_has_tier_but_no_deepseek_price_shows_unpriced_not_zero(self):
        # Regression: a model can have a DeepSeek tier mapping while the local pricing
        # file is stale and lacks the deepseek-v4-* rate. That must show as unpriced
        # (null / dash in the UI), not silently as a real-looking $0.00.
        usages = [report.Usage("Codex", "gpt-test", "2026-08-10", 100, 20, 60, True)]
        pricing = {"models": {}, "subscriptions": {}}
        page = report.render_dashboard(usages, 30, {"Codex": 1}, pricing, deepseek_tiers={"gpt-test": "flash"})
        self.assertIn('"deepseek_cost": null', page)
        self.assertIn('"deepseek_tier": null', page)


    def test_cache_hit_stats_handles_subset_and_additive_providers(self):
        codex_item = report.Usage("Codex", "gpt-test", "2026-08-10", 100, 20, 60, True)
        claude_item = report.Usage("Claude Code", "claude-test", "2026-08-10", 40, 20, 100, False, cache_write_input_tokens=10)
        hit, total = report.cache_hit_stats([codex_item, claude_item])
        # Codex: fresh=100-60=40, hit=60. Claude: fresh=40, hit=100, cache_write=10.
        self.assertEqual(hit, 160)
        self.assertEqual(total, 40 + 60 + 40 + 100 + 10)

    def test_deepseek_equivalent_cost_uses_tier_map_and_real_cache_split(self):
        usage = report.Usage("Codex", "gpt-test", "2026-08-10", 100, 20, 60, True)
        pricing = {"models": {"deepseek-v4-flash": {
            "input_per_million": 1, "cached_input_per_million": 0.1, "output_per_million": 5,
        }}}
        tiers = {"gpt-test": "flash"}
        # fresh=40, hit=60, output=20 -> (40*1 + 60*0.1 + 20*5) / 1e6
        self.assertAlmostEqual(report.deepseek_equivalent_cost(usage, pricing, tiers), (40 + 6 + 100) / 1_000_000)

    def test_deepseek_equivalent_cost_is_none_when_model_not_in_tier_map(self):
        usage = report.Usage("Codex", "gpt-unmapped", "2026-08-10", 100, 20, 60, True)
        pricing = {"models": {"deepseek-v4-flash": {"input_per_million": 1, "cached_input_per_million": 0.1, "output_per_million": 5}}}
        self.assertIsNone(report.deepseek_equivalent_cost(usage, pricing, {}))

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
            {"provider": "ChatGPT", "start_date": "2026-07-12", "amount": 20.0, "currency": "USD", "cycle": "month"},
            {"provider": "Claude", "start_date": "2026-03-13", "amount": 215.0, "currency": "USD", "cycle": "year"},
        ])

    def test_subscription_plans_preserve_original_currency(self):
        pricing = {"subscriptions": {"MiniMax": {"plans": [{
            "start_date": "2026-08-29", "amount": 430, "currency": "CNY", "cycle": "month",
        }]}}}
        self.assertEqual(report.subscription_plan_data(pricing), [{
            "provider": "MiniMax", "start_date": "2026-08-29", "amount": 430.0,
            "currency": "CNY", "cycle": "month",
        }])

    def test_ecb_cross_rate_and_weekend_carry_forward(self):
        xml = b'''<Envelope><Cube><Cube time="2026-08-28"><Cube currency="USD" rate="1.20"/><Cube currency="CNY" rate="8.40"/></Cube></Cube></Envelope>'''
        rates = fx_rates.parse_ecb_xml(xml)
        self.assertAlmostEqual(rates["2026-08-28"], 7.0)
        payload = fx_rates.browser_payload({"fetched_at": "2026-08-29T10:00:00-04:00", "rates": rates}, ["2026-08-28", "2026-08-29"])
        self.assertAlmostEqual(payload["usd_cny_by_date"]["2026-08-29"], 7.0)
        self.assertEqual(payload["latest_rate_date"], "2026-08-28")

    def test_dashboard_contains_currency_switch_and_daily_fx(self):
        usage = report.Usage("MiniMax", "minimax/MiniMax-M3", "2026-08-29", input_tokens=1_000_000)
        pricing = {"models": {"minimax/MiniMax-M3": {"input_per_million": 1, "cached_input_per_million": 1, "output_per_million": 1}}, "subscriptions": {}}
        page = report.render_dashboard([usage], 1, {"MiniMax": 1}, pricing, enabled_providers=["MiniMax"], display_currency="CNY", fx_cache={"rates": {"2026-08-29": 7.0}})
        self.assertIn('data-currency="USD"', page)
        self.assertIn('data-currency="CNY"', page)
        self.assertIn('"cost_cny": 7.0', page)

    def test_pricing_alias_and_auto_fallback_are_narrow_and_explicit(self):
        pricing = {
            "models": {
                "qwen3.8-max": {
                    "input_per_million": 1.0, "cached_input_per_million": 0.1,
                    "output_per_million": 2.0,
                },
                "gpt-low": {
                    "input_per_million": 0.5, "cached_input_per_million": 0.05,
                    "output_per_million": 1.0,
                },
            },
            "model_aliases": {"Qwen3.8-Max-Preview": "qwen3.8-max"},
            "auto_fallbacks": {"Codex": "gpt-low"},
        }
        alias_usage = report.Usage("Bailian", "Qwen3.8-Max-Preview", "2026-08-29", input_tokens=1_000_000)
        auto_usage = report.Usage("Codex", "Auto", "2026-08-29", input_tokens=1_000_000)
        unknown_usage = report.Usage("Codex", "unknown-model", "2026-08-29", input_tokens=1_000_000)
        self.assertEqual(report.api_equivalent_cost(alias_usage, pricing), 1.0)
        self.assertEqual(report.api_equivalent_cost(auto_usage, pricing), 0.5)
        self.assertIsNone(report.api_equivalent_cost(unknown_usage, pricing))
        self.assertEqual(report.pricing_model_for_usage(auto_usage, pricing), ("gpt-low", True))

    def test_codex_auto_review_uses_date_appropriate_lowest_public_model(self):
        pricing = {
            "models": {
                "gpt-5.4-mini": {"input_per_million": 0.75, "cached_input_per_million": 0.075, "output_per_million": 4.5},
                "gpt-5.6-luna": {"input_per_million": 0.1, "cached_input_per_million": 0.01, "output_per_million": 0.6},
            },
            "auto_fallbacks": {"Codex": {"periods": [
                {"start_date": "2000-01-01", "end_date": "2026-08-30", "model": "gpt-5.4-mini"},
                {"start_date": "2026-08-31", "model": "gpt-5.6-luna"},
            ]}},
        }
        before_retirement = report.Usage("Codex", "codex-auto-review", "2026-08-29", input_tokens=1_000_000)
        after_retirement = report.Usage("Codex", "codex-auto-review", "2026-08-31", input_tokens=1_000_000)
        self.assertEqual(report.pricing_model_for_usage(before_retirement, pricing), ("gpt-5.4-mini", True))
        self.assertEqual(report.pricing_model_for_usage(after_retirement, pricing), ("gpt-5.6-luna", True))
        self.assertEqual(report.api_equivalent_cost(before_retirement, pricing), 0.75)
        self.assertEqual(report.api_equivalent_cost(after_retirement, pricing), 0.1)

    def test_auto_always_uses_deepseek_flash_and_peak_time_doubles_cost(self):
        pricing = {
            "models": {
                "gpt-pro-fallback": {"input_per_million": 1, "cached_input_per_million": 1, "output_per_million": 1},
                "deepseek-v4-flash": {"input_per_million": 2, "cached_input_per_million": 1, "output_per_million": 4},
                "deepseek-v4-pro": {"input_per_million": 20, "cached_input_per_million": 10, "output_per_million": 40},
            },
            "auto_fallbacks": {"Codex": "gpt-pro-fallback"},
        }
        tiers = {"gpt-pro-fallback": "pro"}
        off_peak = report.Usage("Codex", "codex-auto-review", "2026-08-29", input_tokens=1_000_000)
        peak = report.Usage("Codex", "codex-auto-review", "2026-08-29", input_tokens=1_000_000, deepseek_rate_band="peak")
        self.assertEqual(report.deepseek_tier_for_usage(off_peak, pricing, tiers), "flash")
        self.assertEqual(report.deepseek_equivalent_cost(off_peak, pricing, tiers), 2.0)
        self.assertEqual(report.deepseek_equivalent_cost(peak, pricing, tiers), 4.0)

    def test_deepseek_peak_windows_use_beijing_time_and_unknown_is_off_peak(self):
        self.assertEqual(report.deepseek_rate_band(None), "off_peak")
        self.assertEqual(report.deepseek_rate_band(dt.datetime(2026, 8, 29, 1, 0, tzinfo=dt.timezone.utc)), "peak")
        self.assertEqual(report.deepseek_rate_band(dt.datetime(2026, 8, 29, 5, 0, tzinfo=dt.timezone.utc)), "off_peak")

    def test_minimax_current_models_produce_expected_deepseek_tiers_and_costs(self):
        pricing = {
            "models": {
                "minimax/MiniMax-M3": {"input_per_million": 1, "cached_input_per_million": 1, "output_per_million": 1},
                "minimax/MiniMax-M2.7": {"input_per_million": 1, "cached_input_per_million": 1, "output_per_million": 1},
                "deepseek-v4-flash": {"input_per_million": 2, "cached_input_per_million": 1, "output_per_million": 4},
                "deepseek-v4-pro": {"input_per_million": 6, "cached_input_per_million": 3, "output_per_million": 12},
            },
        }
        tiers = {"minimax/MiniMax-M3": "pro", "minimax/MiniMax-M2.7": "flash"}
        m3 = report.Usage("MiniMax", "minimax/MiniMax-M3", "2026-08-29", input_tokens=1_000_000)
        m27 = report.Usage("MiniMax", "minimax/MiniMax-M2.7", "2026-08-29", input_tokens=1_000_000)
        self.assertEqual(report.deepseek_tier_for_usage(m3, pricing, tiers), "pro")
        self.assertEqual(report.deepseek_tier_for_usage(m27, pricing, tiers), "flash")
        self.assertEqual(report.deepseek_equivalent_cost(m3, pricing, tiers), 6.0)
        self.assertEqual(report.deepseek_equivalent_cost(m27, pricing, tiers), 2.0)

    def test_latest_confirmed_models_have_deepseek_tiers(self):
        tiers = report.load_deepseek_tier_map(report.DEFAULT_DEEPSEEK_TIER_MAP)
        self.assertEqual(tiers["minimax/MiniMax-M3"], "pro")
        self.assertEqual(tiers["moonshotai/kimi-k3"], "pro")
        self.assertEqual(tiers["z-ai/glm-5.3"], "pro")
        self.assertEqual(tiers["qwen3.8-max"], "pro")
        self.assertEqual(tiers["qwen/qwen3.8-flash"], "flash")

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
        self.assertIn('data-set="pricing"', render_help("zh-CN"))
        self.assertIn('data-set="mapping"', render_help("zh-CN"))
        self.assertIn("現在の検出結果", render_help("ja"))
        self.assertIn("현재 감지 결과", render_help("ko"))
        self.assertIn("Détection actuelle", render_help("fr"))
        self.assertIn("Aktuelle Erkennung", render_help("de"))
        self.assertIn("Detección actual", render_help("es"))


if __name__ == "__main__":
    unittest.main()
