"""v0.4.3: planner small-case checks, the cross-unit decision ledger, the generic CLI provider, roster and fallbacks."""
import datetime
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
from coop.core import default_config, dumps
from coop.protocol import encode
from coop.providers import invoke
from test_editloop import EditBase, NOTE, OLD, NEW, BLOCK, agreeing, edit, frame, kind_of

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = 'for n in range(3, 50, 2):\n    assert n % 2 == 1\nprint("odd primes: no counterexample up to 49")\n'
CHECKED_PLAN = frame('plan', '清单如下。\n```python coop-check\n' + SCRIPT + '```', issues=[BLOCK], done=False, check=True)


def fake_run(output='odd primes: no counterexample up to 49'):
    calls = []

    def run_check(script, folder, cfg):
        calls.append(script)
        return {'id': 'x' * 16, 'code_sha256': 'c', 'status': 'completed', 'stdout': output, 'stderr': '', 'returncode': 0}
    return run_check, calls


class PlannerChecks(EditBase):
    def script(self, plan=CHECKED_PLAN):
        def run(stage, prompt):
            if kind_of(stage) == 'plan':
                return plan
            return agreeing(stage, prompt)
        return run

    def test_output_reaches_analysts_and_reviewer_and_runs_once(self):
        run_check, calls = fake_run()
        with patch('coop.core.executor.run_check', side_effect=run_check):
            sid, st = self.run_with(self.script())
            self.assertEqual(st['units'], {'done_edited': 1})
            st = self.resume(sid, self.script())
        self.assertEqual(len(calls), 1)                                    # cached, not re-run on resume
        self.assertIn('小规模计算检查', self.prompts['edit-r1-plan'])        # the planner is asked for it
        for stage in ('edit-r1-analysis0', 'edit-r1-analysis1', 'edit-r1-review'):
            self.assertIn('no counterexample up to 49', self.prompts[stage], stage)
        rec = editloop.Session(self.store, sid).records('thm:1.2')[0]
        self.assertEqual(rec['plan_execution']['status'], 'completed')
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('计算检查：completed', report)

    def test_without_docker_the_check_is_skipped_not_paused(self):
        sid, st = self.run_with(self.script())                             # no Docker in the test environment
        self.assertEqual(st['units'], {'done_edited': 1})
        rec = editloop.Session(self.store, sid).records('thm:1.2')[0]
        self.assertIn(rec['plan_execution']['status'], ('unavailable',))

    def test_on_unavailable_pause(self):
        path = self.store.root / 'config.json'
        cfg = json.loads(path.read_text())
        cfg['edit']['checks'] = {'planner': True, 'on_unavailable': 'pause'}
        path.write_text(dumps(cfg))
        sid, st = self.run_with(self.script())
        self.assertEqual(st['units'], {'paused': 1})

    def test_check_without_code_block_gets_a_format_retry(self):
        bad = frame('plan', '没有代码块', issues=[BLOCK], done=False, check=True)
        calls = []

        def run(stage, prompt):
            if kind_of(stage) == 'plan':
                calls.append(prompt)
                return bad if len(calls) == 1 else frame('plan', 'ok', issues=[BLOCK], done=False, check=False)
            return agreeing(stage, prompt)
        sid, st = self.run_with(run)
        self.assertEqual(len(calls), 2)
        self.assertIn('格式校验', calls[1])

    def test_disabled_checks_and_old_sessions(self):
        cfg = default_config(True)
        cfg['edit']['checks'] = {'planner': False}
        self.assertFalse(editloop.edit_config(cfg)['checks']['planner'])
        with self.assertRaises(ValueError):
            editloop.edit_config({**cfg, 'edit': {**cfg['edit'], 'checks': {'on_unavailable': 'ignore'}}})


class Ledger(EditBase):
    def script(self, ledger_lines=('记号：素数集合统一写作 $\\Primes$。',), reject=False):
        def run(stage, prompt):
            k = kind_of(stage)
            if 'thm:1.1（当前原文' in prompt or '可编辑单元 thm:1.1' in prompt:
                if k == 'merge':
                    block = '\n'.join(['<<<COOP_LEDGER>>>', *[f'- {x}' for x in ledger_lines], '<<<COOP_LEDGER_END>>>'])
                    return frame('merge', '合并。\n' + edit('P1', '|a|\\le|b|', '|a| \\le |b|') + '\n' + block, done=True)
                if k == 'analysis':
                    return frame('analysis', '改写。\n' + edit('P1', '|a|\\le|b|', '|a| \\le |b|'), done=True)
                if k == 'plan':
                    return frame('plan', '清单', issues=[BLOCK], done=False)
                if k == 'review':
                    if reject:
                        return frame('review', '不同意', verdict='revise', done=False,
                                     issues=[{'id': 'R1', 'severity': 'blocking', 'category': 'math_error', 'location': 'x'}])
                    return frame('review', '可以', verdict='approve', done=True)
                return None
            return agreeing(stage, prompt)
        return run

    def test_approved_decisions_reach_later_units_and_sessions(self):
        sid, st = self.run_with(self.script(), only=('thm:1.1', 'thm:1.2'))
        self.assertIn('LEDGER', self.prompts['edit-r1-merge'])           # the merge step is asked for decisions
        later = [p for s, p in self.prompts.items() if '可编辑单元 thm:1.2' in p and s.endswith('plan')]
        self.assertTrue(later and '素数集合统一写作' in later[0])
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('跨单元决定台账', report)
        entries = editloop.ledger(self.store, self.src)['entries']
        self.assertEqual([e['unit'] for e in entries], ['thm:1.1'])
        editloop.ledger(self.store, self.src, add='全书用 $\\mid$ 表示整除。')
        self.assertEqual(len(editloop.ledger(self.store, self.src)['entries']), 2)
        # a later session on the same source sees both
        self.src.write_text(self.text(), encoding='utf-8')
        sid2, _ = self.run_with(lambda s, p: None, only=('thm:1.2',))
        plan = [p for s, p in self.prompts.items() if s.endswith('plan')][-1]
        self.assertIn('全书用', plan)

    def test_rejected_patch_records_nothing(self):
        path = self.store.root / 'config.json'
        cfg = json.loads(path.read_text())
        cfg['edit']['max_rounds'] = 1
        path.write_text(dumps(cfg))
        self.run_with(self.script(reject=True), only=('thm:1.1',))
        self.assertEqual(editloop.ledger(self.store, self.src)['entries'], [])

    def test_parse_ledger(self):
        body = 'x\n<<<COOP_LEDGER>>>\n- a\n2. b\n\n<<<COOP_LEDGER_END>>>\n<<<COOP_EDIT P1>>>'
        self.assertEqual(editloop.parse_ledger(body), ['a', 'b'])
        self.assertEqual(len(editloop.parse_ledger('<<<COOP_LEDGER>>>\n' + '\n'.join(f'- {i}' for i in range(9)) + '\n<<<COOP_LEDGER_END>>>')), 5)
        self.assertEqual(editloop.parse_ledger('<<<COOP_LEDGER>>>\n2 是唯一的偶素数\n<<<COOP_LEDGER_END>>>'), ['2 是唯一的偶素数'])


FAKE_CLI = r'''#!{python}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
mode = os.environ['FAKE_MODE']
prompt = sys.stdin.read() if mode == 'stdin' else (args[args.index('--prompt') + 1] if mode == 'argv' else Path(args[args.index('--file') + 1]).read_text())
Path(os.environ['FAKE_LOG']).write_text(json.dumps({'args': args, 'cwd_files': os.listdir('.'), 'key': 'ACME_KEY' in os.environ}))
answer = os.environ['FAKE_ANSWER']
if os.environ.get('FAKE_FAIL'):
    print(json.dumps({'type': 'result', 'status': 'error', 'error': 'quota exceeded'})); sys.exit(0)
print(json.dumps({'type': 'progress', 'text': 'TOOL TEXT'}))
print(json.dumps({'type': 'result', 'status': 'success', 'result': {'text': answer}, 'echo': prompt[:5]}))
'''


class GenericCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.exe = self.root / 'acme'
        self.exe.write_text(FAKE_CLI.replace('{python}', sys.executable))
        self.exe.chmod(self.exe.stat().st_mode | stat.S_IEXEC)
        self.log = self.root / 'log.json'

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, mode='stdin'):
        argv = {'stdin': ['{exe}', 'run'], 'argv': ['{exe}', 'run', '--prompt', '{prompt}'], 'file': ['{exe}', 'run', '--file', '{prompt_file}']}[mode]
        return {'kind': 'cli', 'vendor': 'Acme', 'executable': str(self.exe), 'auth_mode': 'subscription', 'input': mode, 'argv': argv,
                'model': 'acme-pro', 'model_args': ['--model', '{model}'], 'timeout_args': ['--timeout', '{timeout}'],
                'output': {'format': 'jsonl', 'event_key': 'type', 'event_value': 'result', 'path': ['result.text', 'text'],
                           'ok_path': 'status', 'ok_values': ['success'], 'error_path': 'error'},
                'strip_env': ['ACME_KEY']}

    def call(self, spec, fail=False):
        env = {'FAKE_MODE': spec['input'], 'FAKE_LOG': str(self.log), 'FAKE_ANSWER': 'ANSWER {model}', 'ACME_KEY': 'secret'}
        if fail:
            env['FAKE_FAIL'] = '1'
        with patch.dict(os.environ, env), tempfile.TemporaryDirectory() as d:
            return invoke(spec, 'PROMPT text {model}', 'analysis0', Path(d), 300)

    def test_three_input_modes(self):
        for mode in ('stdin', 'argv', 'file'):
            with self.subTest(mode=mode):
                self.assertEqual(self.call(self.spec(mode)), 'ANSWER {model}')
                logged = json.loads(self.log.read_text())
                self.assertEqual(logged['args'][-4:], ['--model', 'acme-pro', '--timeout', '300'])
                self.assertEqual(logged['cwd_files'], [])
                self.assertFalse(logged['key'])                        # strip_env in subscription mode

    def test_errors_and_validation(self):
        with self.assertRaisesRegex(RuntimeError, 'rate_limit'):
            self.call(self.spec(), fail=True)
        for bad in ({'vendor': ''}, {'argv': []}, {'input': 'argv'}, {'output': {'format': 'json'}}, {'output': {'format': 'xml'}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                access.validate_cli_spec({**self.spec(), **bad})
        cfg = default_config()
        cfg['providers']['acme'] = {**self.spec(), 'vendor': ''}
        from coop.core import validate_config
        with self.assertRaisesRegex(ValueError, 'acme'):
            validate_config(cfg)

    def test_vendor_counts_for_independence(self):
        cfg = default_config()
        cfg['providers']['acme'] = self.spec()
        cfg['providers']['acme-2'] = {**self.spec(), 'vendor': 'acme'}
        roles = cfg['edit']['roles']
        editloop.check_roles(cfg, {**roles, 'analysts': ['acme', 'gemini']})
        with self.assertRaisesRegex(ValueError, '三家不同'):
            editloop.check_roles(cfg, {**roles, 'analysts': ['acme', 'acme-2']})


def quota_once(stage_prefix, word):
    state = {'hits': 0}

    def script(stage, prompt):
        if stage.startswith(stage_prefix) and state['hits'] == 0:
            state['hits'] += 1
            raise RuntimeError(f'{word} 退出码 1; rate_limit: 等待额度恢复后 resume')
        return agreeing(stage, prompt)
    return script


class Scheduling(EditBase):
    def setUp(self):
        super().setUp()
        self.models = {}
        self.workspace(providers={'muse': {'kind': 'demo', 'model': 'tag-muse'}, 'kimi': {'kind': 'demo', 'model': 'tag-kimi'}})

    def workspace(self, providers=None, **edit):
        path = self.store.root / 'config.json'
        cfg = json.loads(path.read_text())
        cfg['providers'].update(providers or {})
        cfg['edit'].update(edit)
        path.write_text(dumps(cfg))

    def go(self, script, sid=None, **kw):
        from coop import providers
        real = providers.invoke

        def fake(spec, prompt, stage, folder, timeout):
            self.models.setdefault(stage, []).append(spec.get('model'))
            out = script(stage, prompt)
            return real(spec, prompt, stage, folder, timeout) if out is None else out
        with patch('coop.core.invoke', side_effect=fake):
            if sid is None:
                sid = editloop.create(self.store, self.src, ('thm:1.2',))
            return sid, editloop.execute(self.store, sid, **kw)

    def test_roster_window(self):
        self.assertEqual(editloop.roster_targets([{'role': 'analysts.0', 'provider': 'muse', 'from': '2026-11-05', 'to': '2026-11-11'}],
                                                 '2026-11-08'), {'analysts.0': 'muse'})
        self.assertEqual(editloop.roster_targets([{'role': 'analysts.0', 'provider': 'muse', 'from': '2026-11-05', 'to': '2026-11-11'}],
                                                 '2026-11-12'), {})
        today = datetime.date.today()
        window = {'role': 'analysts.0', 'provider': 'muse', 'from': (today - datetime.timedelta(days=1)).isoformat(),
                  'to': (today + datetime.timedelta(days=5)).isoformat()}
        self.workspace(roster=[window])
        sid, st = self.go(lambda s, p: agreeing(s, p))
        self.assertEqual(self.models['edit-r1-analysis0'], ['tag-muse'])
        S = editloop.Session(self.store, sid)
        self.assertEqual(S.e['roster_state'], {'analysts.0': 'codex'})
        self.assertEqual(S.e['role_changes'][0]['reason'], '排班表')
        # the window is over: the next run gives the role back
        self.workspace(roster=[{**window, 'to': (today - datetime.timedelta(days=1)).isoformat(), 'from': (today - datetime.timedelta(days=3)).isoformat()}])
        editloop.apply_roster(S)
        self.assertEqual(S.e['roles']['analysts'][0], 'codex')
        self.assertEqual(S.e['roster_state'], {})
        with self.assertRaisesRegex(ValueError, 'roster'):
            self.workspace(roster=[{'role': 'analysts.0', 'provider': 'muse', 'from': '2026-11-11', 'to': '2026-11-05'}])
            editloop.live_edit(self.store)

    def test_manual_fallback_hint(self):
        self.workspace(fallbacks={'analysts.0': ['muse', 'kimi']})
        sid, st = self.go(quota_once('edit-r1-analysis0', 'codex'))
        self.assertEqual(st['state'], 'paused')
        self.assertIn('--use analysts.0=muse', st['next'])

    def test_automatic_fallback_finishes_the_unit_and_next_run_restores(self):
        self.workspace(fallbacks={'analysts.0': ['muse', 'kimi']}, auto_fallback=True)
        sid, st = self.go(quota_once('edit-r1-analysis0', 'codex'))
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertEqual(self.models['edit-r1-analysis0'][-1], 'tag-muse')
        S = editloop.Session(self.store, sid)
        self.assertEqual(S.e['fallback_state'], {'analysts.0': 'codex'})
        self.assertIn('自动', S.e['role_changes'][-1]['reason'])
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('codex → muse', report)
        editloop.execute(self.store, sid)                              # a new run: back to the original line-up
        S = editloop.Session(self.store, sid)
        self.assertEqual(S.e['roles']['analysts'][0], 'codex')
        self.assertEqual(S.e['fallback_state'], {})

    def test_fallback_never_breaks_independence(self):
        path = self.store.root / 'config.json'
        cfg = json.loads(path.read_text())
        cfg['providers']['claude-2'] = {'kind': 'claude', 'model': None}
        cfg['providers']['claude'] = {'kind': 'claude', 'model': None}
        cfg['providers']['codex'] = {'kind': 'codex', 'model': None}
        path.write_text(dumps(cfg))
        self.workspace(fallbacks={'analysts.0': ['claude-2']}, auto_fallback=True)
        sid = editloop.create(self.store, self.src, ('thm:1.2',))
        S = editloop.Session(self.store, sid)
        self.assertEqual(editloop.fallback_options(S, 'codex'), [])     # same company as the reviewer


class CliWiring(unittest.TestCase):
    def test_flags(self):
        with tempfile.TemporaryDirectory() as d:
            out = subprocess.run([sys.executable, '-m', 'coop', '--workspace', d, 'edit', 'ledger', '--help'], cwd=ROOT,
                                 capture_output=True, text=True)
            self.assertIn('--add', out.stdout)


if __name__ == '__main__':
    unittest.main()
