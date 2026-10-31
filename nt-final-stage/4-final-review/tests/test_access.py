import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from coop.access import environment_for, parse_kimi, classify_error, inspect_provider, configure
from coop.core import default_config


class AccessTests(unittest.TestCase):
    def test_subscription_scrubs_gateway_env_without_changing_parent(self):
        env = {'PATH': '/usr/bin', 'ANTHROPIC_AUTH_TOKEN': 'private', 'ANTHROPIC_BASE_URL': 'https://other', 'OPENAI_API_KEY': 'private', 'DEEPSEEK_API_KEY': 'keep'}
        cleaned = environment_for({'kind': 'claude', 'auth_mode': 'subscription'}, env)
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN', cleaned)
        self.assertNotIn('ANTHROPIC_BASE_URL', cleaned)
        self.assertEqual(env['ANTHROPIC_AUTH_TOKEN'], 'private')
        self.assertEqual(cleaned['DEEPSEEK_API_KEY'], 'keep')
        self.assertEqual(environment_for({'kind': 'claude', 'auth_mode': 'native'}, env), env)
    def test_kimi_stream_selects_last_complete_assistant(self):
        text = '\n'.join(json.dumps(x) for x in [
            {'role': 'assistant', 'content': 'planning', 'tool_calls': [{'id': 'a'}]},
            {'role': 'tool', 'content': 'ignored'},
            {'role': 'assistant', 'content': [{'type': 'text', 'text': '{"ok":true}'}]},
        ])
        self.assertEqual(json.loads(parse_kimi(text)), {'ok': True})
        with self.assertRaises(ValueError):
            parse_kimi('{"role":"tool","content":"hello"}')
    def test_categories(self):
        self.assertEqual(classify_error('HTTP 429')['category'], 'rate_limit')
        self.assertEqual(classify_error('HTTP 401')['category'], 'authentication')
        self.assertEqual(classify_error('unknown option --agent-file')['category'], 'cli_version')
        self.assertEqual(classify_error('model not found')['category'], 'model')
    def test_diagnostics_never_print_environment_values(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'super-secret'}):
            result = inspect_provider('deepseek', default_config()['providers']['deepseek'])
        self.assertTrue(result['key_present'])
        self.assertNotIn('super-secret', json.dumps(result))
    def test_configure_is_validated_and_preserves_existing_roles(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'config.json'; path.write_text(json.dumps(default_config()))
            configure(path, 'codex', model='new-model', executable='/usr/local/bin/codex')
            cfg = json.loads(path.read_text())
            self.assertEqual(cfg['providers']['codex']['model'], 'new-model')
            self.assertEqual(cfg['roles'], default_config()['roles'])
            with self.assertRaises(ValueError):
                configure(path, 'deepseek', auth_mode='subscription')

class EntryIntegration(unittest.TestCase):
    def test_subscription_status_guards_api_route(self):
        from coop.providers import invoke
        for kind in ('codex', 'claude'):
            for accepted in (True, False):
                with self.subTest(kind=kind, accepted=accepted), tempfile.TemporaryDirectory() as d:
                    root = Path(d)
                    exe = root / 'fake-cli'
                    status = ('Logged in using ChatGPT' if accepted else 'Logged in using an API key') if kind == 'codex' else json.dumps({'authMethod': 'claude.ai' if accepted else 'api_key'})
                    script = '#!' + sys.executable + '\nimport sys,json,os\nfrom pathlib import Path\n'
                    script += 'if "status" in sys.argv:\n print(' + repr(status) + '); raise SystemExit(0)\n'
                    if kind == 'codex':
                        script += 'Path(sys.argv[sys.argv.index("-o")+1]).write_text(\'{"ok":true}\')\n'
                    else:
                        script += 'assert "ANTHROPIC_AUTH_TOKEN" not in os.environ\nprint(json.dumps({"result": \'{"ok":true}\'}))\n'
                    exe.write_text(script); exe.chmod(0o755)
                    spec = {'kind': kind, 'executable': str(exe), 'auth_mode': 'subscription'}
                    with patch.dict(os.environ, {'ANTHROPIC_AUTH_TOKEN': 'unused-test'}):
                        if accepted:
                            self.assertEqual(json.loads(invoke(spec, 'probe', '__probe__', root, 3)), {'ok': True})
                        else:
                            with self.assertRaisesRegex(RuntimeError, '未确认'):
                                invoke(spec, 'probe', '__probe__', root, 3)
    def test_api_request_and_model_listing_without_network(self):
        from coop.providers import _invoke
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'TEST_API_KEY': 'test-only'}):
            spec = {'kind': 'api', 'key_env': 'TEST_API_KEY', 'url': 'https://example.test/v1/chat/completions', 'model': 'test-model'}
            def response(payload):
                obj = MagicMock()
                obj.__enter__.return_value.read.return_value = json.dumps(payload).encode()
                return obj
            with patch('coop.providers.urllib.request.build_opener') as opener:
                opener.return_value.open.return_value = response({'choices': [{'finish_reason': 'stop', 'message': {'content': '{"ok":true}'}}]})
                self.assertEqual(json.loads(_invoke(spec, 'ping', '__probe__', Path(d), 2)), {'ok': True})
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(json.loads(request.data)['model'], 'test-model')
                opener.return_value.open.return_value = response({'data': [{'id': 'test-model'}]})
                self.assertEqual(json.loads(_invoke(spec, '', '__models__', Path(d), 2))['data'][0]['id'], 'test-model')
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(request.full_url, 'https://example.test/v1/models')
                self.assertEqual(request.get_method(), 'GET')
                opener.return_value.open.return_value = response({'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]})
                with self.assertRaisesRegex(ValueError, '截断'):
                    _invoke(spec, 'ping', '__probe__', Path(d), 2)
    def test_demo_check_all_and_missing_provider(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(__file__).resolve().parents[1]
            def cli(*args):
                return subprocess.run([sys.executable, '-m', 'coop', '--workspace', d, *args], cwd=root, capture_output=True, text=True)
            self.assertEqual(cli('init', '--demo').returncode, 0)
            check = cli('check', 'all')
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertEqual([x['state'] for x in json.loads(check.stdout)], ['demo'] * 5)
            self.assertEqual(cli('check', 'missing').returncode, 1)
