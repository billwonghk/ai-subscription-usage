"""One-shot ownership tests and isolated lifecycle tests; no listening server."""
import ast
import json
import io
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from app_instance import AppInstance


def production_definitions(*names, **scope):
    tree = ast.parse((ROOT / 'src/desktop_app.py').read_text())
    nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'desktop_app.py', 'exec'), scope)
    return scope


class InstanceTests(unittest.TestCase):
    def test_one_owner_and_reacquire_after_close(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = AppInstance(Path(directory), 17653), AppInstance(Path(directory), 17653)
            try:
                self.assertTrue(first.acquire())
                token = first.token
                self.assertFalse(second.acquire())
                first.close()
                self.assertTrue(second.acquire())
                self.assertNotEqual(token, second.token)
                if os.name != 'nt':
                    self.assertEqual(second.path.stat().st_mode & 0o777, 0o600)
            finally:
                first.close()
                second.close()

    def test_process_exit_does_not_leave_stale_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            script = 'from app_instance import AppInstance; from pathlib import Path; import sys,os; a=AppInstance(Path(sys.argv[1]),17653); assert a.acquire(); os._exit(0)'
            result = subprocess.run([sys.executable, '-c', script, directory], env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')}, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            instance = AppInstance(Path(directory), 17653)
            try:
                self.assertTrue(instance.acquire())
            finally:
                instance.close()

    def test_activation_uses_owner_secret_without_proxy(self):
        with tempfile.TemporaryDirectory() as directory:
            owner = AppInstance(Path(directory), 17653)
            try:
                owner.acquire()
                opener = Mock()
                opener.open.return_value.__enter__ = Mock(return_value=SimpleNamespace(status=200))
                opener.open.return_value.__exit__ = Mock(return_value=False)
                with patch('app_instance.urllib.request.build_opener', return_value=opener):
                    self.assertTrue(owner.signal_existing())
                request = opener.open.call_args.args[0]
                self.assertEqual(request.full_url, 'http://127.0.0.1:17653/instance/activate')
                self.assertEqual(request.get_header('X-app-instance'), owner.token)
            finally:
                owner.close()

    def test_second_launch_never_constructs_another_app(self):
        instance = Mock(token='secret')
        instance.acquire.return_value = False
        instance.signal_existing.return_value = True
        constructor = Mock(return_value=instance)
        app = Mock()
        scope = production_definitions('launch_desktop', AppInstance=constructor, CONFIG_ROOT=Path('.'), LOCAL_PORT=17653, DesktopApp=app, notify=Mock())
        self.assertEqual(scope['launch_desktop'](), 0)
        app.assert_not_called()
        instance.signal_existing.assert_called_once_with('activate')
        instance.close.assert_called_once()

    def test_port_conflict_reports_error_and_releases_ownership(self):
        import errno
        instance = Mock(token='secret')
        instance.acquire.return_value = True
        app = Mock()
        app.return_value.run.side_effect = OSError(errno.EADDRINUSE, 'occupied')
        notice = Mock()
        scope = production_definitions('launch_desktop', AppInstance=Mock(return_value=instance), CONFIG_ROOT=Path('.'), LOCAL_PORT=17653, DesktopApp=app, notify=notice)
        self.assertEqual(scope['launch_desktop'](), 1)
        instance.close.assert_called_once()
        notice.assert_called_once()

    def test_quit_when_not_running_does_not_launch_an_app(self):
        instance = Mock()
        instance.acquire.return_value = True
        app = Mock()
        scope = production_definitions('launch_desktop', AppInstance=Mock(return_value=instance), CONFIG_ROOT=Path('.'), LOCAL_PORT=17653, DesktopApp=app, notify=Mock())
        self.assertEqual(scope['launch_desktop'](quit_running=True), 0)
        app.assert_not_called()
        instance.close.assert_called_once()


class CleanupTests(unittest.TestCase):
    def test_diagnostic_json_works_with_windows_legacy_encoding(self):
        data = {'schema_version': 1, 'provider': '\u963f\u91cc\u767e\u70bc'}
        scope = production_definitions('command_line', sys=SimpleNamespace(argv=['app', '--doctor']),
                                       json=json, ensure_runtime_files=Mock(), doctor_report=Mock(return_value=data))
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding='cp1252')
        with patch('sys.stdout', stream):
            self.assertTrue(scope['command_line']())
        stream.flush()
        self.assertEqual(json.loads(buffer.getvalue()), data)

    def app(self):
        server, icon, http_thread = Mock(), Mock(), Mock()
        http_thread.is_alive.return_value = True
        return SimpleNamespace(_lifecycle_lock=threading.RLock(), _stopping=threading.Event(), _timers={Mock(), Mock()}, server=server, icon=icon, _http_thread=http_thread)

    def test_stop_closes_listener_and_cancels_all_timers_once(self):
        stop = production_definitions('stop')['stop']
        app = self.app()
        server, timers = app.server, list(app._timers)
        stop(app)
        stop(app)
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()
        app.icon.stop.assert_called_once()
        for timer in timers:
            timer.cancel.assert_called_once()
        self.assertFalse(app._timers)

    def test_shutdown_exception_still_closes_socket_and_icon(self):
        stop = production_definitions('stop')['stop']
        app = self.app()
        server = app.server
        server.shutdown.side_effect = RuntimeError('shutdown failed')
        with self.assertRaises(RuntimeError):
            stop(app)
        server.server_close.assert_called_once()
        app.icon.stop.assert_called_once()

    def test_failed_server_start_does_not_wait_for_shutdown(self):
        stop = production_definitions('stop')['stop']
        app = self.app()
        server = app.server
        app._http_thread.is_alive.return_value = False
        stop(app)
        server.shutdown.assert_not_called()
        server.server_close.assert_called_once()

    def test_stopped_app_cannot_schedule_another_timer(self):
        start = production_definitions('_start_timer', threading=threading)['_start_timer']
        app = self.app()
        app._stopping.set()
        with patch('threading.Timer') as timer:
            self.assertIsNone(start(app, 10, Mock()))
            timer.assert_not_called()
