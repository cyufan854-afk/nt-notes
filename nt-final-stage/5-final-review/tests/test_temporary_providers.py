"""Extra capacity: the Muse Code provider (Muse Wonder Full on a Muse Code subscription) and handing a role to another
provider mid-session (`edit resume --use ROLE=PROVIDER`), e.g. Muse or Kimi credits while one subscription's quota is
exhausted. (The Grok provider of v0.4.2 was removed in v0.4.4.)"""
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
from coop.access import MUSE_WONDER_FULL, argv_prompt_limit, classify_error, parse_muse
from coop.core import default_config, dumps
from coop.protocol import encode
from coop.providers import invoke
from test_editloop import EditBase, NEW, agreeing, kind_of

ROOT = Path(__file__).resolve().parents[1]
ANSWER = encode({'kind': 'analysis', 'assessment': 'unknown', 'check': False}, 'MUSE-BODY with $\\nu$')

# A stand-in for `muse exec --json`, shaped like the stream observed from Muse Code 1.4.11: one {"payload_type",
# "payload"} record per line; the prompt is echoed back (turn.input.user), so it can hold numbers like 429 or 401.
FAKE_MUSE = r"""#!{python}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
prompt = Path(args[args.index('--prompt-file') + 1]).read_text(encoding='utf-8') if '--prompt-file' in args else ''
with Path(os.environ['FAKE_MUSE_LOG']).open('a') as f:
    f.write(json.dumps({'argv': args, 'cwd': os.getcwd(), 'files': sorted(os.listdir('.')), 'prompt': prompt,
                        'stdin': sys.stdin.read(), 'api_key': 'META_API_KEY' in os.environ}) + '\n')
scenario = os.environ.get('FAKE_MUSE_SCENARIO', 'ok')
model = args[args.index('--model') + 1] if '--model' in args else 'muse-spark-1.3'
def emit(kind, **payload):
    print(json.dumps({'payload_type': kind, 'payload': payload}), flush=True)
if scenario == 'login':
    print('error: not signed in; run muse to sign in at dev.meta.ai', file=sys.stderr); sys.exit(1)
print('Muse Code 1.4.11')
emit('run.started')
emit('turn.input.user', text=prompt)
if scenario != 'no_model_event':
    emit('run.model.configured', model_id={'other_model': 'muse-spark-1.3', 'tagged': 'meta/' + model + '#high'}.get(scenario, model),
         provider_id='meta')
if scenario == 'quota':
    emit('run.terminal.failed', terminal='failed', error='usage limit reached for your plan; resets in 3h'); sys.exit(1)
if scenario == 'internal':
    emit('run.terminal.failed', terminal='failed', error='internal server error'); sys.exit(1)
if scenario == 'cancelled':
    emit('run.terminal.cancelled', terminal='cancelled'); sys.exit(0)
emit('run.output.delta', text=os.environ['FAKE_MUSE_ANSWER'])
emit('run.usage', models={model: {'input_tokens': 3, 'output_tokens': 5}}, allowance={'window': {'used_percent': 12}})
if scenario == 'deltas_only':
    emit('run.terminal.completed', terminal='completed'); sys.exit(0)
emit('run.terminal.completed', terminal='completed', text=os.environ['FAKE_MUSE_ANSWER'])
"""


class MuseTransport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.exe = self.root / 'muse'
        self.exe.write_text(FAKE_MUSE.replace('{python}', sys.executable))
        self.exe.chmod(self.exe.stat().st_mode | stat.S_IEXEC)
        self.log = self.root / 'calls.jsonl'
        self.spec = {'kind': 'muse', 'executable': str(self.exe), 'model': MUSE_WONDER_FULL, 'auth_mode': 'subscription'}

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, scenario='ok'):
        return patch.dict(os.environ, {'FAKE_MUSE_LOG': str(self.log), 'FAKE_MUSE_SCENARIO': scenario, 'FAKE_MUSE_ANSWER': ANSWER,
                                       'META_API_KEY': 'LLM_would-bill-the-api'})

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()]

    def call(self, scenario='ok', spec=None, prompt='the whole prompt'):
        with self.env(scenario), tempfile.TemporaryDirectory() as d:
            out = invoke(spec or self.spec, prompt, 'analysis0', Path(d), 600)
            transport = json.loads((Path(d) / 'transport.json').read_text())
        return out, transport

    def test_headless_call_in_a_fresh_session(self):
        long_prompt = 'p' * 200000                       # coop prompts reach 180k characters: through a file, not argv
        out, transport = self.call(prompt=long_prompt)
        self.assertEqual(out, ANSWER)
        call = self.calls()[0]
        argv = call['argv']
        self.assertEqual(argv[:3], ['exec', '--json', '--prompt-file'])
        self.assertEqual(Path(argv[3]).name, 'muse-prompt.txt')
        self.assertEqual(call['prompt'], long_prompt)
        self.assertEqual(argv[4:], ['--workspace', call['cwd'], '--no-session-log', '--contributor-mode', 'off', '--model', MUSE_WONDER_FULL])
        self.assertEqual(Path(call['cwd']).name, 'muse-workspace')
        self.assertEqual(call['files'], [])
        self.assertFalse(call['api_key'])          # subscription mode: the Model API key never reaches muse
        for flag in ('--yolo', '--disable-approval', '--disable-sandbox', '--approval-mode', '--session-id'):
            self.assertNotIn(flag, argv)
        self.assertEqual(transport['model'], MUSE_WONDER_FULL)
        self.assertEqual(transport['usage']['allowance']['window']['used_percent'], 12)
        self.assertEqual(transport['text_source'], 'run.terminal')

    def test_arguments(self):
        argv = access.muse_argv('muse', {**self.spec, 'effort': 'max', 'max_model_steps': 6, 'extra_args': ['--disable-web-tools']},
                                'f.txt', 'ws')
        self.assertEqual(argv[-5:], ['--reasoning-effort', 'max', '--max-model-steps', '6', '--disable-web-tools'])
        for bad in (['--yolo'], ['--disable-approval'], ['--approval-mode', 'never'], ['--approval-mode=never'], ['--session-id', 'x'],
                    ['--contributor-mode', 'on'], ['--model', 'muse-spark-1.3']):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'extra_args'):
                access.muse_argv('muse', {**self.spec, 'extra_args': bad}, 'f.txt', 'ws')
        with self.assertRaisesRegex(ValueError, 'effort'):
            access.muse_argv('muse', {**self.spec, 'effort': 'none'}, 'f.txt', 'ws')       # the Meta provider has no 'none'
        with self.assertRaisesRegex(ValueError, 'model'):
            access.muse_argv('muse', {**self.spec, 'model': None}, 'f.txt', 'ws')          # never Muse Code's default model

    def test_the_model_is_checked_on_every_call_and_never_falls_back(self):
        with self.assertRaises(RuntimeError) as cm:
            self.call('other_model')
        self.assertIn('muse-spark-1.3', str(cm.exception))
        self.assertTrue(any(h in str(cm.exception) for h in editloop.FATAL_HINTS))       # stops the whole run
        out, transport = self.call('tagged')                                             # meta/…#high is the same model
        self.assertEqual(out, ANSWER)
        out, transport = self.call('no_model_event')                                     # not reported: recorded as None
        self.assertEqual(out, ANSWER)
        self.assertIsNone(transport['model'])

    def test_errors(self):
        for scenario, category, fatal in (('login', 'authentication', True), ('quota', 'rate_limit', True),
                                          ('internal', 'provider_error', False), ('cancelled', 'provider_error', False)):
            with self.subTest(scenario=scenario), self.assertRaises(RuntimeError) as cm:
                # the echoed prompt holds 429 and 401: they must not be read as a quota or login error
                self.call(scenario, prompt='Show that 429 and 401 are ... timeout ... login')
            self.assertIn(category + ':', str(cm.exception))
            self.assertEqual(any(h in str(cm.exception) for h in editloop.FATAL_HINTS), fatal)

    def test_parser(self):
        out, transport = self.call('deltas_only')
        self.assertEqual(out, ANSWER)
        self.assertEqual(transport['text_source'], 'run.output.delta')
        with self.assertRaisesRegex(ValueError, 'JSON'):
            parse_muse('plain text only')
        self.assertFalse(parse_muse('{"payload_type": "run.started", "payload": {}}')['ok'])          # never finished
        self.assertEqual(parse_muse('{"payload_type": "run.terminal", "payload": {"terminal": "completed", "text": "A"}}')['response'], 'A')
        self.assertEqual(parse_muse('{"payload_type": "something.new", "payload": {}}\n'
                                    '{"payload_type": "run.terminal.completed", "payload": {"text": "A"}}')['response'], 'A')
        self.assertTrue(access.muse_model_matches('muse/meta/muse-wonder-full-1.0#xhigh', 'muse-wonder-full-1.0'))
        self.assertFalse(access.muse_model_matches('muse-wonder-1.0', 'muse-wonder-full-1.0'))
        with patch.object(sys, 'platform', 'linux'):
            self.assertEqual(argv_prompt_limit({}, 60000), 60000)                    # Kimi on Linux: unchanged
        with patch.object(sys, 'platform', 'darwin'), patch.object(os, 'sysconf', return_value=1048576, create=True):
            self.assertGreater(argv_prompt_limit({}, 60000), 500000)                # macOS: edit prompts fit as an argument

    def test_default_config_has_muse_and_kimi_but_no_role_uses_them_and_no_grok(self):
        cfg = default_config()
        self.assertNotIn('grok', cfg['providers'])
        self.assertEqual(cfg['providers']['muse']['kind'], 'muse')
        self.assertEqual(cfg['providers']['muse']['model'], MUSE_WONDER_FULL)
        self.assertEqual(cfg['providers']['kimi']['kind'], 'kimi')
        used = editloop.role_providers(editloop.edit_config(cfg)) + [cfg['roles']['planner'], *cfg['roles']['analysts'], cfg['roles']['reviewer']]
        self.assertNotIn('muse', used)
        self.assertNotIn('kimi', used)
        self.assertEqual(editloop.vendor(cfg['providers']['muse']), 'meta')
        self.assertEqual(len(default_config(True)['providers']), 5)                  # the demo is unchanged

    def test_doctor_notes_and_leftover_grok(self):
        with patch.dict(os.environ, {'META_API_KEY': 'secret-value'}):
            info = access.inspect_provider('muse', self.spec)
        self.assertIn('META_API_KEY', info['warning'])
        self.assertNotIn('secret-value', json.dumps(info, ensure_ascii=False))
        self.assertTrue(any('Active Memory' in n for n in info['notes']))
        self.assertIn('移除', access.inspect_provider('grok', {'kind': 'grok', 'model': None})['warning'])
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(Exception, '移除'):
            invoke({'kind': 'grok', 'model': None}, 'p', 'analysis0', Path(d), 60)


class Independence(unittest.TestCase):
    def cfg(self):
        cfg = default_config()
        cfg['providers']['claude-2'] = {'kind': 'claude', 'model': None, 'auth_mode': 'subscription'}
        return cfg

    def test_rules(self):
        cfg = self.cfg()
        roles = cfg['edit']['roles']
        editloop.check_roles(cfg, roles)                                             # the default line-up
        editloop.check_roles(cfg, {**roles, 'analysts': ['muse', 'gemini']})        # Muse Wonder Full for Codex
        editloop.check_roles(cfg, {**roles, 'analysts': ['codex', 'kimi']})          # Kimi for Argon (if ever wanted)
        for bad, word in (({'analysts': ['claude-2', 'gemini']}, '三家不同'), ({'analysts': ['codex', 'codex']}, '四个不同'),
                          ({'planner': 'codex'}, '四个不同'), ({'arbiter': 'claude'}, '仲裁'),
                          ({'reviewer': 'muse', 'analysts': ['muse', 'gemini']}, '四个不同')):
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
        self.add_workspace_provider('muse', {'kind': 'demo', 'model': 'tag-muse'})   # added after the session was created
        state['fixed'] = True
        sid, st = self.run_capturing(script, sid, uses=['analysts.0=muse'])
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn(NEW, self.text())
        self.assertEqual(self.specs['edit-r1-analysis0'][-1], 'tag-muse')            # the failed call went to Muse
        resumed = self.seen[len(done_before) + 1:]
        for stage in done_before:
            self.assertEqual(resumed.count(stage), 0, stage)                          # finished calls were not repeated
        S = editloop.Session(self.store, sid)
        self.assertEqual(S.e['roles']['analysts'], ['muse', 'gemini'])
        change = S.e['role_changes'][0]
        self.assertEqual(change['changes'], [{'role': 'analysts.0', 'from': 'codex', 'to': 'muse'}])
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('分析者 A codex → muse', report)
        # and back again once the quota has recovered
        editloop.use_providers(self.store, sid, ['analysts.0=codex'])
        self.assertEqual(editloop.Session(self.store, sid).e['roles']['analysts'], ['codex', 'gemini'])
        self.assertEqual(len(editloop.Session(self.store, sid).e['role_changes']), 2)

    def test_bad_swaps_change_nothing(self):
        script, _ = quota_on('edit-r1-analysis0', 'codex')
        sid, _ = self.run_capturing(script)
        self.add_workspace_provider('grok', {'kind': 'grok', 'model': None})          # left over from v0.4.2
        for bad, word in ((['analysts.0'], '写法'), (['author=muse'], '写法'), (['analysts.0=nobody'], '不在'),
                          (['analysts.0=gemini'], '四个不同'), (['analysts.0=grok'], '移除')):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, word):
                editloop.use_providers(self.store, sid, bad)
        self.assertNotIn('role_changes', editloop.Session(self.store, sid).e)

    def test_cli_flag_is_wired(self):
        out = subprocess.run([sys.executable, '-m', 'coop', '--workspace', str(self.store.root), 'edit', 'resume', '--help'],
                             cwd=ROOT, capture_output=True, text=True)
        self.assertIn('--use', out.stdout)


if __name__ == '__main__':
    unittest.main()
