import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from updater import latest_release


class AppUpdateTests(unittest.TestCase):
    def test_only_newer_stable_release_is_offered(self):
        for version, expected in [("v0.4.1", False), ("v0.4.2", False),
                                  ("v0.5.0", True), ("v0.10.0", True),
                                  ("v0.5.0-rc.1", False), ("invalid", False)]:
            with self.subTest(version=version), patch("updater.download_json", return_value={
                "tag_name": version, "html_url": "https://github.com/example/releases"
            }):
                self.assertEqual(latest_release("https://example.test", "0.4.2") is not None, expected)

    def test_draft_and_prerelease_are_not_offered(self):
        for flag in ("draft", "prerelease"):
            with self.subTest(flag=flag), patch("updater.download_json", return_value={
                "tag_name": "v0.5.0", "html_url": "https://example.test", flag: True
            }):
                self.assertIsNone(latest_release("https://example.test", "0.4.2"))
