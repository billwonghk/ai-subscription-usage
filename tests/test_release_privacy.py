import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from release_privacy import scan_bytes, source_files


class ReleasePrivacyTests(unittest.TestCase):
    def test_secret_patterns_are_detected_without_returning_values(self):
        for secret in (b'sk-' + b'A' * 40, b'ghp_' + b'B' * 40,
                       b'-----BEGIN ' + b'PRIVATE KEY-----',
                       b'https://' + b'person:password@private.invalid'):
            findings = scan_bytes(secret)
            self.assertTrue(findings)
            self.assertNotIn(secret.decode(), str(findings))

    def test_personal_paths_and_placeholders(self):
        self.assertIn('personal-path', scan_bytes(b'/Users/' + b'privateperson/project'))
        self.assertFalse(scan_bytes(b'/Users/USER/project'))

    def test_runtime_files_are_excluded_from_source_selection(self):
        selected = [str(p) for p in source_files()]
        self.assertFalse(any('/private/' in p or '/assets/screenshots/' in p for p in selected))

    def test_release_builds_independent_native_packages(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/release.yml').read_text(encoding='utf-8')
        for value in (
            'runner: macos-15',
            'runner: macos-15-intel',
            'mac_arch: arm64',
            'mac_arch: x86_64',
            'AI-Subscription-Usage-macOS-Apple-Silicon.zip',
            'AI-Subscription-Usage-macOS-Intel.zip',
            'AI-Subscription-Usage-Windows-Portable.zip',
            'AI-Subscription-Usage-{#MyAppVersion}-Windows-Setup',
            'lipo -archs',
            'Windows tray lifecycle and UTF-8 UI smoke test',
            'windows-settings-smoke.png',
            'pattern: ai-subscription-usage-*',
            'body_path: docs/release-v0.5.1.md',
        ):
            self.assertIn(value, workflow if 'MyAppVersion' not in value else (Path(__file__).resolve().parents[1] / 'installer/windows.iss').read_text(encoding='utf-8'))
        self.assertNotIn('AI-Subscription-Usage-macOS.zip', workflow)

    def test_v051_version_and_release_notes_are_synchronized(self):
        root = Path(__file__).resolve().parents[1]
        desktop = (root / 'src/desktop_app.py').read_text(encoding='utf-8')
        spec = (root / 'ai-subscription-usage.spec').read_text(encoding='utf-8')
        workflow = (root / '.github/workflows/release.yml').read_text(encoding='utf-8')
        notes = (root / 'docs/release-v0.5.1.md').read_text(encoding='utf-8')
        self.assertIn('APP_VERSION = "0.5.1"', desktop)
        self.assertIn('CFBundleShortVersionString": "0.5.1"', spec)
        self.assertIn('body_path: docs/release-v0.5.1.md', workflow)
        self.assertIn('# AI Subscription Usage v0.5.1', notes)
