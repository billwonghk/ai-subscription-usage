"""Exercise production request handling without opening a listening socket."""
import ast
import io
import json
import secrets
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


class ControlRequestTests(unittest.TestCase):
    def request(self, origin, payload=None, length=None):
        source = Path(__file__).resolve().parents[1] / 'src/desktop_app.py'
        tree = ast.parse(source.read_text())
        handler = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == 'Handler')
        method = next(n for n in handler.body if isinstance(n, ast.FunctionDef) and n.name == 'do_POST')
        app = Mock(settings={})
        scope = {'app': app, 'json': json, 'ALLOWED_ORIGINS': {'http://127.0.0.1:17653'}, 'SUPPORTED': {'en', 'zh-CN'}}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), scope)
        raw = json.dumps(payload).encode()
        headers = {'Content-Length': str(len(raw) if length is None else length)}
        if origin is not None:
            headers['Origin'] = origin
        request = SimpleNamespace(path='/settings', headers=headers, rfile=io.BytesIO(raw), wfile=io.BytesIO(),
                                  send_response=Mock(), send_error=Mock(), send_header=Mock(), end_headers=Mock(), _cors=Mock())
        scope['do_POST'](request)
        return request, app

    def test_rejects_foreign_null_and_missing_origins_before_actions(self):
        for origin in (None, 'null', 'https://example.com', 'http://127.0.0.1:8501'):
            request, app = self.request(origin, {'action': 'set_language', 'value': 'en'})
            request.send_error.assert_called_once_with(403)
            self.assertFalse(app.mock_calls)

    def test_allowed_origin_can_switch_language(self):
        request, app = self.request('http://127.0.0.1:17653', {'action': 'set_language', 'value': 'en'})
        request.send_response.assert_called_once_with(200)
        app.set_language.assert_called_once_with('en')

    def test_invalid_payloads_are_not_reported_as_success(self):
        for payload in ([], None, {'action': 'unknown'}, {'action': 'set_language', 'value': []}, {'action': 'set_telemetry', 'value': 'false'}):
            request, app = self.request('http://127.0.0.1:17653', payload)
            request.send_response.assert_called_once_with(400)
            self.assertFalse(app.mock_calls)

    def test_invalid_sizes_are_rejected_before_read(self):
        for length in (-1, 0, 4097, 'invalid'):
            request, app = self.request('http://127.0.0.1:17653', {}, length)
            request.send_response.assert_called_once_with(400)
            self.assertEqual(request.rfile.tell(), 0)

    def test_instance_control_requires_owner_secret(self):
        source = Path(__file__).resolve().parents[1] / 'src/desktop_app.py'
        tree = ast.parse(source.read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'do_POST')
        app = Mock(_instance_token='owner-secret')
        main_thread = Mock()
        scope = {'app': app, 'secrets': secrets, '_run_on_main_thread': main_thread}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), scope)
        for token in ('', 'wrong', '非ASCII'):
            request = SimpleNamespace(path='/instance/quit', headers={'X-App-Instance': token}, send_error=Mock())
            scope['do_POST'](request)
            request.send_error.assert_called_once_with(403)
        main_thread.assert_not_called()
        request = SimpleNamespace(path='/instance/quit', headers={'X-App-Instance': 'owner-secret'}, send_response=Mock(), send_header=Mock(), end_headers=Mock())
        scope['do_POST'](request)
        request.send_response.assert_called_once_with(200)
        main_thread.assert_called_once_with(app.stop)
