import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ai_usage_report as report


class CodingSourceTests(unittest.TestCase):
    def test_kimi_step_tokens_not_context_snapshot_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timestamp = dt.datetime(2026, 9, 7, 12, tzinfo=dt.timezone.utc).timestamp()
            row = {"timestamp": timestamp, "message": {"type": "StatusUpdate", "payload": {
                "message_id": "response-1", "context_tokens": 999999,
                "token_usage": {"input_other": 100, "output": 20,
                                "input_cache_read": 80, "input_cache_creation": 10}}}}
            (root / "wire.jsonl").write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
            usage, files = report.parse_kimi_wire(root, dt.date(2026, 9, 1))
            self.assertEqual(files, 1)
            self.assertEqual(len(usage), 1)
            self.assertEqual(usage[0].total_tokens, 210)
            self.assertEqual(usage[0].model, "未记录模型")

    def test_bound_claude_log_belongs_only_to_subscription(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bound = root / "bailian"
            bound.mkdir()
            row = {"type": "assistant", "timestamp": "2026-09-07T12:00:00Z", "message": {
                "id": "response-1", "model": "glm-5.2", "usage": {
                    "input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 80}}}
            (bound / "session.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            configured = [{"provider": "bailian", "surface": "claude-code", "path": str(bound)}]
            with patch.object(report, "load_configured_sources", return_value=configured), patch.object(report, "report_today", return_value=dt.date(2026, 9, 7)):
                usage, counts = report.collect_usages(30, claude_projects=root, enabled_providers=["Claude Code", "Bailian"])
                self.assertEqual(len(usage), 1)
                self.assertEqual(usage[0].provider, "Bailian")
                self.assertEqual(usage[0].total_tokens, 200)
                self.assertEqual(counts["Claude Code"], 0)
                usage, _ = report.collect_usages(30, claude_projects=root, enabled_providers=["Claude Code"])
                self.assertEqual(usage, [])

    def test_explicit_provider_keeps_model_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = {"type": "assistant", "timestamp": "2026-09-07T12:00:00Z", "message": {
                "id": "response-1", "model": "glm-5.2", "usage": {
                    "input_tokens": 100, "output_tokens": 20, "cache_creation_input_tokens": 10}}}
            (root / "session.jsonl").write_text(json.dumps(row), encoding="utf-8")
            for provider in ("Kimi", "GLM", "Bailian"):
                usage, _ = report.parse_claude_code(root, dt.date(2026, 9, 1), provider=provider)
                self.assertEqual(usage[0].provider, provider)
                self.assertEqual(usage[0].model, "glm-5.2")
                self.assertEqual(usage[0].total_tokens, 130)
