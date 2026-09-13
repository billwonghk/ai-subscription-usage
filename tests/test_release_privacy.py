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
        ):
            self.assertIn(value, workflow if 'MyAppVersion' not in value else (Path(__file__).resolve().parents[1] / 'installer/windows.iss').read_text(encoding='utf-8'))
        self.assertNotIn('AI-Subscription-Usage-macOS.zip', workflow)
