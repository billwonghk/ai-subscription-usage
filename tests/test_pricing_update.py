import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_pricing


class PricingUpdateTests(unittest.TestCase):
    def test_openrouter_period_history_receives_new_current_period(self):
        models = {"model": {
            "periods": [{
                "start_date": "2026-08-01",
                "input_per_million": 1.0,
                "cached_input_per_million": 0.1,
                "output_per_million": 5.0,
            }],
            "source": "openrouter",
            "updated_at": "2026-08-01",
        }}
        changed = fetch_pricing.update_model(models, "model", {
            "input_per_million": 2.0,
            "cached_input_per_million": 0.2,
            "output_per_million": 10.0,
        }, "2026-09-03")
        self.assertTrue(changed)
        self.assertEqual(models["model"]["periods"][0]["end_date"], "2026-09-02")
        self.assertEqual(models["model"]["periods"][1]["start_date"], "2026-09-03")
        self.assertEqual(models["model"]["periods"][1]["output_per_million"], 10.0)

    def test_same_day_price_change_replaces_current_period(self):
        models = {"model": {
            "periods": [{
                "start_date": "2026-09-03",
                "input_per_million": 1.0,
                "cached_input_per_million": 0.1,
                "output_per_million": 5.0,
            }],
            "source": "openrouter",
        }}
        fetch_pricing.update_model(models, "model", {
            "input_per_million": 2.0,
            "cached_input_per_million": 0.2,
            "output_per_million": 10.0,
        }, "2026-09-03")
        self.assertEqual(len(models["model"]["periods"]), 1)
        self.assertEqual(models["model"]["periods"][0]["input_per_million"], 2.0)
        self.assertNotIn("end_date", models["model"]["periods"][0])

    def test_non_openrouter_period_history_is_not_changed(self):
        original = {
            "periods": [{
                "start_date": "2026-08-01",
                "input_per_million": 1.0,
                "cached_input_per_million": 0.1,
                "output_per_million": 5.0,
            }],
            "source": "alibaba-cloud-cn",
        }
        models = {"model": original.copy()}
        changed = fetch_pricing.update_model(models, "model", {
            "input_per_million": 2.0,
            "cached_input_per_million": 0.2,
            "output_per_million": 10.0,
        }, "2026-09-03")
        self.assertFalse(changed)
        self.assertEqual(len(models["model"]["periods"]), 1)

    def test_removed_cache_write_rate_is_removed_from_active_period(self):
        models = {"model": {
            "periods": [{
                "start_date": "2026-08-01",
                "input_per_million": 1.0,
                "cached_input_per_million": 0.1,
                "cache_write_input_per_million": 1.25,
                "output_per_million": 5.0,
            }],
            "source": "openrouter",
        }}
        changed = fetch_pricing.update_model(models, "model", {
            "input_per_million": 1.0,
            "cached_input_per_million": 0.1,
            "output_per_million": 5.0,
        }, "2026-09-03")
        self.assertTrue(changed)
        self.assertEqual(models["model"]["periods"][0]["cache_write_input_per_million"], 1.25)
        self.assertEqual(models["model"]["periods"][0]["end_date"], "2026-09-02")
        self.assertNotIn("cache_write_input_per_million", models["model"]["periods"][1])
