"""Temporary capacity: the Grok CLI provider (a SuperGrok trial) and handing a role to another provider mid-session
(`edit resume --use ROLE=PROVIDER`), e.g. Grok or Kimi credits while one subscription's quota is exhausted."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from coop import access, editloop
from coop.access import argv_prompt_limit, classify_error, parse_grok
from coop.core import default_config, dumps
from coop.protocol import encode
from coop.providers import invoke
from test_editloop import EditBase, NEW, agreeing, kind_of

ROOT = Path(__file__).resolve().parents[1]
ANSWER = encode({'kind': 'analysis', 'assessment': 'unknown', 'check': False}, 'GROK-BODY with $\\nu$')

FAKE_GROK = r'''#!{python}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ['FAKE_GROK_LOG']).open('a') as f:
    f.write(json.dumps({'argv': args, 'cwd': os.getcwd(), 'files': sorted(os.listdir('.')), 'stdin': sys.stdin.read(),
                        'api_key': 'GROK_CODE_XAI_API_KEY' in os.environ}) + '\n')
scenario = os.environ.get('FAKE_GROK_SCENARIO', 'ok')
if scenario == 'login':
    print('Error: not authenticated. Run `grok login` first, or set GROK_CODE_XAI_API_KEY.', file=sys.stderr); sys.exit(1)
if scenario == 'quota':
    print(json.dumps({'is_error': True, 'error': 'rate limit exceeded for your plan'})); sys.exit(0)
print('update check skipped')
print(json.dumps({'result': os.environ['FAKE_GROK_ANSWER'], 'usage': {'input_tokens': 3}}))
'''


class GrokTransport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.exe = self.root / 'grok'
        self.exe.write_text(FAKE_GROK.replace('{python}', sys.executable))
        self.exe.chmod(self.exe.stat().st_mode | stat.S_IEXEC)
        self.log = self.root / 'calls.jsonl'
        self.spec = {'kind': 'grok', 'executable': str(self.exe), 'model': 'grok-test', 'auth_mode': 'subscription'}

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, scenario='ok'):
        return patch.dict(os.environ, {'FAKE_GROK_LOG': str(self.log), 'FAKE_GROK_SCENARIO': scenario, 'FAKE_GROK_ANSWER': ANSWER,
                                       'GROK_CODE_XAI_API_KEY': 'would-bill-the-api'})

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()]

    def test_headless_call_in_a_fresh_session(self):
        with self.env(), tempfile.TemporaryDirectory() as d:
            out = invoke(self.spec, 'the whole prompt', 'analysis0', Path(d), 600)
        self.assertEqual(out, ANSWER)
        call = self.calls()[0]
        self.assertEqual(call['argv'], ['--no-auto-update', '-p', 'the whole prompt', '--output-format', 'json', '-m', 'grok-test'])
        self.assertEqual(Path(call['cwd']).name, 'grok-workspace')
        self.assertEqual(call['files'], [])
        self.assertFalse(call['api_key'])          # subscription mode: the xAI API key never reaches grok
        with self.assertRaisesRegex(ValueError, 'continue'):
            access.grok_argv('grok', {**self.spec, 'extra_args': ['--continue']}, 'p')

    def test_errors(self):
        for scenario, category in (('login', 'authentication'), ('quota', 'rate_limit')):
            with self.subTest(scenario=scenario), self.env(scenario), tempfile.TemporaryDirectory() as d:
                with self.assertRaises(RuntimeError) as cm:
                    invoke(self.spec, 'p', 'analysis0', Path(d), 600)
                self.assertIn(category + ':', str(cm.exception))
                self.assertTrue(any(h in str(cm.exception) for h in editloop.FATAL_HINTS))

    def test_parser_and_prompt_size(self):
        self.assertEqual(parse_grok('{"response": {"content": [{"type": "text", "text": "A"}]}}')['response'], 'A')
        self.assertFalse(parse_grok('{"result": ""}')['ok'])
        self.assertEqual(classify_error(parse_grok('{"status": "error", "message": "quota exhausted"}')['error'])['category'], 'rate_limit')
        with patch.object(sys, 'platform', 'linux'):
            self.assertEqual(argv_prompt_limit({}, 120000), 120000)
            self.assertEqual(argv_prompt_limit({}, 60000), 60000)                    # Kimi on Linux: unchanged
            with self.assertRaisesRegex(ValueError, '命令行参数'):
                access.grok_argv('grok', self.spec, 'x' * 130000)
            self.assertIn('x' * 130000, access.grok_argv('grok', {**self.spec, 'max_prompt_bytes': 200000}, 'x' * 130000))
        with patch.object(sys, 'platform', 'darwin'), patch.object(os, 'sysconf', return_value=1048576, create=True):
            self.assertGreater(argv_prompt_limit({}, 60000), 500000)                # macOS: edit prompts fit as an argument

    def test_default_config_has_grok_but_no_role_uses_it(self):
        cfg = default_config()
        self.assertEqual(cfg['providers']['grok']['kind'], 'grok')
        used = editloop.role_providers(editloop.edit_config(cfg)) + [cfg['roles']['planner'], *cfg['roles']['analysts'], cfg['roles']['reviewer']]
        self.assertNotIn('grok', used)
        self.assertNotIn('kimi', used)
        self.assertEqual(len(default_config(True)['providers']), 5)                  # the demo is unchanged


class Independence(unittest.TestCase):
    def cfg(self):
        cfg = default_config()
        cfg['providers']['claude-2'] = {'kind': 'claude', 'model': None, 'auth_mode': 'subscription'}
        return cfg

    def test_rules(self):
        cfg = self.cfg()
        roles = cfg['edit']['roles']
        editloop.check_roles(cfg, roles)                                             # the default line-up
        editloop.check_roles(cfg, {**roles, 'analysts': ['grok', 'gemini']})        # Grok for Codex
        editloop.check_roles(cfg, {**roles, 'analysts': ['codex', 'kimi']})          # Kimi for Argon (if ever wanted)
        for bad, word in (({'analysts': ['claude-2', 'gemini']}, '三家不同'), ({'analysts': ['codex', 'codex']}, '四个不同'),
                          ({'planner': 'codex'}, '四个不同'), ({'arbiter': 'claude'}, '仲裁'),
                          ({'reviewer': 'grok', 'analysts': ['grok', 'gemini']}, '四个不同')):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, word):
                editloop.check_roles(cfg, {**roles, **bad})
        self.assertEqual(editloop.vendor(cfg['providers']['deepseek']), 'deepseek')


def quota_on(stage_prefix, provider_word):
    """A script whose first call at a stage fails for quota until `fixed` is set."""
    state = {'fixed': False}

    def script(stage, prompt):
        if stage.startswith(stage_prefix) and not state['fixed']:
            raise RuntimeError(f'{provider_word} 退出码 1; rate_limit: 等待额度恢复后 resume')
        return agreeing(stage, prompt)
    return script, state


class SwapRoles(EditBase):
    def setUp(self):
        super().setUp()
        self.specs = {}

    def run_capturing(self, script, sid=None, **kw):
        from coop import providers
        real = providers.invoke

        def fake(spec, prompt, stage, folder, timeout):
            self.specs.setdefault(stage, []).append(spec.get('model'))
            self.seen.append(stage)
            out = script(stage, prompt)
            return real(spec, prompt, stage, folder, timeout) if out is None else out
        with patch('coop.core.invoke', side_effect=fake):
            if sid is None:
                sid = editloop.create(self.store, self.src, ('thm:1.2',))
                return sid, editloop.execute(self.store, sid)
            return sid, editloop.execute(self.store, sid, **kw)

    def add_workspace_provider(self, name, spec):
        path = self.store.root / 'config.json'
        cfg = json.loads(path.read_text())
        cfg['providers'][name] = spec
        path.write_text(dumps(cfg))

    def test_quota_pause_names_the_provider_and_suggests_a_swap(self):
        script, _ = quota_on('edit-r1-analysis0', 'codex')
        sid, st = self.run_capturing(script)
        self.assertEqual(st['state'], 'paused')
        self.assertTrue(st['error'].startswith('codex：'), st['error'])
        self.assertIn('--use', st['next'])
        self.assertEqual(st['roles']['analysts'], ['codex', 'gemini'])

    def test_swap_sends_only_new_calls_to_the_substitute_and_is_reported(self):
        script, state = quota_on('edit-r1-analysis0', 'codex')
        sid, st = self.run_capturing(script)
        done_before = [s for s in self.seen if s != 'edit-r1-analysis0']
        self.add_workspace_provider('grok', {'kind': 'demo', 'model': 'tag-grok'})   # added after the session was created
        state['fixed'] = True
        sid, st = self.run_capturing(script, sid, uses=['analysts.0=grok'])
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn(NEW, self.text())
        self.assertEqual(self.specs['edit-r1-analysis0'][-1], 'tag-grok')            # the failed call went to Grok
        resumed = self.seen[len(done_before) + 1:]
        for stage in done_before:
            self.assertEqual(resumed.count(stage), 0, stage)                          # finished calls were not repeated
        S = editloop.Session(self.store, sid)
        self.assertEqual(S.e['roles']['analysts'], ['grok', 'gemini'])
        change = S.e['role_changes'][0]
        self.assertEqual(change['changes'], [{'role': 'analysts.0', 'from': 'codex', 'to': 'grok'}])
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('分析者 A codex → grok', report)
        # and back again once the quota has recovered
        editloop.use_providers(self.store, sid, ['analysts.0=codex'])
        self.assertEqual(editloop.Session(self.store, sid).e['roles']['analysts'], ['codex', 'gemini'])
        self.assertEqual(len(editloop.Session(self.store, sid).e['role_changes']), 2)

    def test_bad_swaps_change_nothing(self):
        script, _ = quota_on('edit-r1-analysis0', 'codex')
        sid, _ = self.run_capturing(script)
        for bad, word in ((['analysts.0'], '写法'), (['author=grok'], '写法'), (['analysts.0=nobody'], '不在'),
                          (['analysts.0=gemini'], '四个不同')):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, word):
                editloop.use_providers(self.store, sid, bad)
        self.assertNotIn('role_changes', editloop.Session(self.store, sid).e)

    def test_cli_flag_is_wired(self):
        out = subprocess.run([sys.executable, '-m', 'coop', '--workspace', str(self.store.root), 'edit', 'resume', '--help'],
                             cwd=ROOT, capture_output=True, text=True)
        self.assertIn('--use', out.stdout)


if __name__ == '__main__':
    unittest.main()
