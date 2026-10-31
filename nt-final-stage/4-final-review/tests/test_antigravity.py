"""Antigravity CLI (agy) provider and automatic Argon arbitration, with a fake agy program."""
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
from coop.access import (antigravity_argv, antigravity_billing, check_antigravity_model, classify_error, inspect_provider,
                         model_listed, parse_antigravity, preflight)
from coop.core import ARGON_SLUG, Store, default_config, dumps
from coop.protocol import encode
from coop.providers import invoke
from test_editloop import EditBase, NOTE, OLD, NEW, BLOCK, agreeing, edit, frame, kind_of
from test_web import FIXED, rejecting

ROOT = Path(__file__).resolve().parents[1]
ANSWER = encode({'kind': 'analysis', 'assessment': 'unknown', 'check': False}, 'ANSWER-BODY with $\\nu$ and \\frac{a}{b}')

FAKE = r'''#!{python}
import json, os, sys
from pathlib import Path
log = Path(os.environ.get('FAKE_AGY_LOG', os.devnull))
scenario = os.environ.get('FAKE_AGY_SCENARIO', 'ok')
args = sys.argv[1:]
if args[:1] == ['models']:
    rows = ['SLUG                 NAME', 'gemini-3.8-flash     Gemini 3.8 Flash']
    if scenario != 'no_argon':
        rows.insert(1, '{slug}       Gemini 4 Argon')
    print('\n'.join(rows))
    sys.exit(0)
if args[:1] == ['--version']:
    print('agy 1.0.0-test'); sys.exit(0)
stdin = sys.stdin.read()
with log.open('a') as f:
    f.write(json.dumps({'argv': args, 'stdin': stdin, 'cwd': os.getcwd(), 'cwd_files': sorted(os.listdir('.')),
                        'has_api_key': 'GEMINI_API_KEY' in os.environ}) + '\n')
if scenario == 'auth':
    print('Error: authentication required. Run agy once interactively to sign in.', file=sys.stderr); sys.exit(1)
if scenario == 'unknown_model':
    print('ERROR: unknown model "' + args[args.index('--model') + 1] + '"', file=sys.stderr); sys.exit(1)
answer = os.environ.get('FAKE_AGY_ANSWER', '')
if '--input-format' in args:
    content = json.loads(stdin.splitlines()[0])['message']['content']
    events = [{'event': 'init', 'session': 'x'},
              {'event': 'step_update', 'text': 'TOOL-OUTPUT-MUST-NOT-BE-USED'}]
    if scenario == 'quota':
        events.append({'event': 'result', 'status': 'ERROR', 'error': 'RESOURCE_EXHAUSTED: you have reached your quota'})
    elif scenario != 'no_result':
        events.append({'event': 'result', 'status': 'SUCCESS', 'response': answer or ('echo:' + content[:20]),
                       'usage': {'input_tokens': 10}})
    print('\n'.join(json.dumps(e) for e in events))
else:
    content = args[args.index('-p') + 1]
    print(json.dumps({'status': 'SUCCESS', 'response': answer or ('echo:' + content[:20]), 'error': None, 'usage': {}}))
'''


class FakeAgy:
    def __init__(self, root, slug=ARGON_SLUG):
        self.root = Path(root)
        self.exe = self.root / 'agy'
        self.exe.write_text(FAKE.replace('{python}', sys.executable).replace('{slug}', slug))
        self.exe.chmod(self.exe.stat().st_mode | stat.S_IEXEC)
        self.log = self.root / 'agy-calls.jsonl'
        self.settings = self.root / 'settings.json'
        access._MODEL_LISTS.clear()

    def spec(self, **kw):
        return {'kind': 'antigravity', 'executable': str(self.exe), 'model': ARGON_SLUG, 'auth_mode': 'subscription',
                'settings_path': str(self.settings), **kw}

    def env(self, scenario='ok', answer=''):
        return patch.dict(os.environ, {'FAKE_AGY_LOG': str(self.log), 'FAKE_AGY_SCENARIO': scenario, 'FAKE_AGY_ANSWER': answer})

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agy = FakeAgy(self.root)
        self.call_dir = self.root / 'call'
        self.call_dir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_stream_json_over_stdin_returns_the_result_text_only(self):
        prompt = 'x' * 200_000   # coop prompts reach 180k characters: never an argument
        with self.agy.env(answer=ANSWER):
            out = invoke(self.agy.spec(), prompt, 'analysis1', self.call_dir, 1200)
        self.assertEqual(out, ANSWER)
        call = self.agy.calls()[0]
        argv = call['argv']
        self.assertEqual(argv[:6], ['-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--model'])
        self.assertEqual(argv[argv.index('--model') + 1], ARGON_SLUG)
        self.assertEqual(argv[argv.index('--print-timeout') + 1], '1185')   # the role timeout, not agy's 5 minutes
        self.assertIn('--disable-slash-commands', argv)
        self.assertNotIn('--dangerously-skip-permissions', argv)
        self.assertNotIn(prompt, ' '.join(argv))
        event = json.loads(call['stdin'].splitlines()[0])
        self.assertEqual(event, {'event': 'user', 'message': {'content': prompt}})
        self.assertEqual(Path(call['cwd']).name, 'agy-workspace')     # an empty directory of its own
        self.assertEqual(call['cwd_files'], [])
        self.assertNotIn('TOOL-OUTPUT', out)

    def test_argv_mode_uses_the_json_envelope(self):
        with self.agy.env(answer=ANSWER):
            out = invoke(self.agy.spec(input='argv', effort='high'), 'short prompt', 'review', self.call_dir, 600)
        self.assertEqual(out, ANSWER)
        argv = self.agy.calls()[0]['argv']
        self.assertEqual(argv[:4], ['-p', 'short prompt', '--output-format', 'json'])
        self.assertEqual(argv[argv.index('--effort') + 1], 'high')

    def test_errors_are_classified(self):
        for scenario, category in (('quota', 'rate_limit'), ('auth', 'authentication'), ('unknown_model', 'model'),
                                   ('no_result', 'protocol')):
            with self.subTest(scenario=scenario), self.agy.env(scenario), tempfile.TemporaryDirectory() as d:
                with self.assertRaises(RuntimeError) as cm:
                    invoke(self.agy.spec(), 'p', 'analysis1', Path(d), 600)
                message = str(cm.exception)
                self.assertTrue(f'{category}:' in message or classify_error(message)['category'] == category, message)
                if category in ('rate_limit', 'authentication', 'model'):
                    self.assertTrue(any(h in message for h in editloop.FATAL_HINTS), message)  # stops the run, resume later

    def test_api_billing_in_settings_is_refused_in_subscription_mode(self):
        self.agy.settings.write_text(json.dumps({'modelProvider': 'gemini', 'env': {'GEMINI_API_KEY': 'secret-value'}}))
        report = antigravity_billing(self.agy.spec())
        self.assertEqual(report['billing'], 'api')
        self.assertNotIn('secret-value', json.dumps(report))
        with self.agy.env(answer=ANSWER), self.assertRaisesRegex(RuntimeError, 'billing'):
            invoke(self.agy.spec(), 'p', 'analysis1', self.call_dir, 600)
        self.assertEqual(self.agy.calls(), [])              # agy was never started
        doctor = inspect_provider('gemini', self.agy.spec())
        self.assertIn('API', doctor['warning'])
        self.assertNotIn('secret-value', json.dumps(doctor))
        self.agy.settings.write_text(json.dumps({'theme': 'dark'}))
        self.assertEqual(antigravity_billing(self.agy.spec())['billing'], 'subscription')

    def test_subscription_mode_hides_gemini_api_key_from_agy(self):
        with self.agy.env(answer=ANSWER), patch.dict(os.environ, {'GEMINI_API_KEY': 'k'}):
            invoke(self.agy.spec(), 'p', 'analysis1', self.call_dir, 600)
        self.assertFalse(self.agy.calls()[0]['has_api_key'])

    def test_model_slug_must_be_listed_and_never_falls_back(self):
        self.assertTrue(check_antigravity_model(self.agy.spec())['listed'])
        other = self.root / 'other'
        other.mkdir()
        agy = FakeAgy(other, slug='gemini-4-argon-latest')   # the list has only a longer slug: no prefix matching
        with self.assertRaisesRegex(RuntimeError, 'gemini-4-argon-latest'):
            check_antigravity_model(agy.spec())
        self.assertFalse(model_listed('gemini-4-argon', 'gemini-4-argon-latest  Gemini 4 Argon'))
        self.assertTrue(model_listed('gemini-4-argon', '[{"slug": "gemini-4-argon"}]'))
        with self.assertRaisesRegex(RuntimeError, 'slug'):
            check_antigravity_model({**self.agy.spec(), 'model': None})

    def test_preflight_names_the_provider(self):
        cfg = default_config()
        cfg['providers']['gemini'] = self.agy.spec(model='gemini-9-unknown')
        with self.assertRaisesRegex(ValueError, 'gemini.*gemini-9-unknown'):
            preflight(cfg, ['codex', 'gemini'])
        cfg['providers']['gemini'] = self.agy.spec()
        self.assertIn('gemini', preflight(cfg, ['gemini']))

    def test_check_command_runs_models_then_the_probe(self):
        ws = self.root / 'ws'
        cfg = default_config()
        cfg['providers']['gemini'] = self.agy.spec()
        ws.mkdir()
        (ws / 'config.json').write_text(json.dumps(cfg))
        env = {**os.environ, 'FAKE_AGY_LOG': str(self.agy.log), 'FAKE_AGY_SCENARIO': 'ok', 'FAKE_AGY_ANSWER': '{"ok":true}'}
        proc = subprocess.run([sys.executable, '-m', 'coop', '--workspace', str(ws), 'check', 'gemini'], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=60)
        result = json.loads(proc.stdout)[0]
        self.assertEqual(result['state'], 'passed', proc.stdout + proc.stderr)
        self.assertTrue(result['model_listed'])
        cfg['providers']['gemini']['model'] = 'gemini-4-argon-typo'
        (ws / 'config.json').write_text(json.dumps(cfg))
        before = len(self.agy.calls())
        proc = subprocess.run([sys.executable, '-m', 'coop', '--workspace', str(ws), 'check', 'gemini'], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=60)
        result = json.loads(proc.stdout)[0]
        self.assertEqual((result['state'], result['category']), ('failed', 'model'))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(len(self.agy.calls()), before)       # no request was sent with the wrong slug


class ParserTests(unittest.TestCase):
    def test_variants_of_the_result_event(self):
        ok = parse_antigravity('{"type":"result","result":{"status":"success","response":"A"}}\n')
        self.assertEqual((ok['ok'], ok['response']), (True, 'A'))
        ok = parse_antigravity('noise\n{"event":"result","status":"SUCCESS","response":{"content":[{"type":"text","text":"B"}]}}')
        self.assertEqual(ok['response'], 'B')
        bad = parse_antigravity('{"event":"result","status":"ERROR","message":"rate limit exceeded"}')
        self.assertFalse(bad['ok'])
        self.assertEqual(classify_error(bad['error'])['category'], 'rate_limit')
        bad = parse_antigravity('{"event":"result","status":"SUCCESS","response":""}')
        self.assertFalse(bad['ok'])
        self.assertEqual(parse_antigravity('log line\n{"status":"SUCCESS","response":"C"}', 'argv')['response'], 'C')
        with self.assertRaises(ValueError):
            parse_antigravity('{"event":"step_update","text":"partial"}')

    def test_agy_error_texts(self):
        for text, category in (('authentication required', 'authentication'), ('RESOURCE_EXHAUSTED', 'rate_limit'),
                               ('Quota exceeded for this model', 'rate_limit'), ('unknown model "x"', 'model'),
                               ('context deadline exceeded', 'timeout'), ('billing: settings.json', 'billing')):
            self.assertEqual(classify_error(text)['category'], category, text)

    def test_print_timeout_formats(self):
        spec = {'model': 'm'}
        self.assertIn('1185', antigravity_argv('agy', spec, 'p', 1200))
        self.assertIn('1185000', antigravity_argv('agy', {**spec, 'print_timeout_unit': 'ms'}, 'p', 1200))
        self.assertIn('1185s', antigravity_argv('agy', {**spec, 'print_timeout_unit': 'duration'}, 'p', 1200))
        with self.assertRaises(ValueError):
            antigravity_argv('agy', {**spec, 'extra_args': ['--dangerously-skip-permissions']}, 'p', 600)


class ConfigTests(unittest.TestCase):
    def test_default_config_uses_argon_through_agy_everywhere(self):
        cfg = default_config()
        g = cfg['providers']['gemini']
        self.assertEqual((g['kind'], g['executable'], g['model'], g['auth_mode']), ('antigravity', 'agy', ARGON_SLUG, 'subscription'))
        self.assertEqual(cfg['edit']['roles'], {'planner': 'deepseek', 'analysts': ['codex', 'gemini'], 'reviewer': 'claude',
                                               'arbiter': 'gemini'})
        self.assertEqual(cfg['edit']['web']['mode'], 'cli')
        self.assertEqual(cfg['timeouts']['arbitration'], 1200)
        used = editloop.role_providers(editloop.edit_config(cfg))
        self.assertNotIn('kimi', used + [cfg['roles']['planner'], *cfg['roles']['analysts'], cfg['roles']['reviewer']])

    def test_v041_config_without_mode_keeps_the_manual_relay(self):
        cfg = default_config()
        del cfg['edit']['web']['mode']
        self.assertEqual(editloop.edit_config(cfg)['web']['mode'], 'manual')
        with self.assertRaises(ValueError):
            editloop.edit_config({**cfg, 'edit': {**cfg['edit'], 'web': {'mode': 'auto'}}})

    def test_configure_can_switch_between_the_two_google_entries(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'config.json'
            cfg = default_config()
            cfg['providers']['gemini'] = {'kind': 'gemini', 'model': None, 'auth_mode': 'subscription'}
            path.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError):
                access.configure(path, 'gemini', kind='antigravity')
            access.configure(path, 'gemini', model='gemini-4-argon', kind='antigravity')
            self.assertEqual(json.loads(path.read_text())['providers']['gemini']['kind'], 'antigravity')
            with self.assertRaises(ValueError):
                access.configure(path, 'codex', kind='antigravity')


def arbiter_reply(new=FIXED, done=True):
    return frame('arbitration', 'ARGON-RULING：2 是偶素数，审查 R1 成立。\n' + edit('P1', OLD, new), issues=[BLOCK], done=done)


class CliArbitrationTests(EditBase):
    web = True

    def setUp(self):
        super().setUp()
        path = self.store.root / 'config.json'
        cfg = json.loads(path.read_text())
        cfg['edit']['web']['mode'] = 'cli'
        path.write_text(dumps(cfg))
        self.specs = {}

    def script(self, quota=False):
        def run(stage, prompt):
            if stage == 'edit-r1-review':
                return rejecting(stage, prompt)
            if stage.startswith('edit-r1-analysis'):
                return frame('analysis', 'SECRET-ANALYSIS\n' + edit('P1', OLD, NEW), done=True)
            if kind_of(stage) == 'arbitration':
                if quota:
                    raise RuntimeError('antigravity status=ERROR; rate_limit: 等待额度恢复后 resume')
                return arbiter_reply()
            return agreeing(stage, prompt)
        return run

    def test_unsettled_unit_is_arbitrated_automatically_in_a_fresh_call(self):
        sid, st = self.run_with(self.script())
        self.assertEqual(st['state'], 'completed', st)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn(FIXED, self.text())
        r2 = sorted(s for s in self.seen if s.startswith('edit-r2'))
        self.assertEqual(r2, ['edit-r2-arbitration', 'edit-r2-confirm0', 'edit-r2-confirm1', 'edit-r2-review'])
        self.assertEqual(st['calls'], 9)
        prompt = self.prompts['edit-r2-arbitration']
        self.assertIn('全新的对话', prompt)
        self.assertIn('不要读写文件', prompt)
        self.assertIn(OLD, prompt)                       # the editable unit
        self.assertIn('R1-OBJECTION', prompt)            # the history it has to rule on
        self.assertNotIn('<<<UNIT ', prompt)             # one plain COOP frame, not a web batch
        self.assertIn('ARGON-RULING', self.prompts['edit-r2-review'])
        self.assertNotIn('SECRET-ANALYSIS', self.prompts['edit-r2-review'])
        rec = editloop.Session(self.store, sid).records('thm:1.2')[1]
        self.assertEqual((rec['web'], rec['via']), (True, 'cli'))
        self.assertFalse((self.store.root / sid / 'web').exists())     # nothing to paste by hand
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('第 2 轮（仲裁）', report)
        self.assertIn('自动调用 gemini', report)

    def test_arbiter_is_the_configured_provider(self):
        seen = {}
        from coop import providers
        real = providers.invoke

        def fake(spec, prompt, stage, folder, timeout):
            seen[stage] = (spec, timeout)
            out = self.script()(stage, prompt)
            return real(spec, prompt, stage, folder, timeout) if out is None else out
        cfg = json.loads((self.store.root / 'config.json').read_text())
        cfg['providers']['argon'] = {'kind': 'demo', 'model': 'tag-argon'}
        cfg['edit']['roles']['arbiter'] = 'argon'
        (self.store.root / 'config.json').write_text(dumps(cfg))
        with patch('coop.core.invoke', side_effect=fake):
            sid = editloop.create(self.store, self.src, ('thm:1.2',))
            editloop.execute(self.store, sid)
        spec, timeout = seen['edit-r2-arbitration']
        self.assertEqual(spec['model'], 'tag-argon')
        self.assertEqual(timeout, 1200)

    def test_quota_pauses_then_resume_or_manual_fallback(self):
        sid, st = self.run_with(self.script(quota=True))
        self.assertEqual(st['state'], 'paused')
        self.assertIn('rate_limit', st['error'])
        self.assertEqual(self.text(), NOTE)
        before = len([s for s in self.seen if s != 'edit-r2-arbitration'])
        # Option 1: the quota is back -> resume; nothing before the arbitration is asked again.
        st = self.resume(sid, self.script())
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertEqual(len([s for s in self.seen if not s.startswith('edit-r2')]), before)

    def test_manual_web_relay_as_fallback(self):
        sid, st = self.run_with(self.script(quota=True))
        st = self.resume(sid, self.script(quota=True), arbiter_mode='manual')
        self.assertEqual(st['state'], 'awaiting_web')
        self.assertEqual(len(st['web_batches']), 1)
        from test_web import reply
        result = editloop.web_import(self.store, sid, [reply(('thm:1.2', arbiter_reply()))])
        self.assertEqual(result['imported'], ['thm:1.2'])
        st = self.resume(sid, self.script(quota=True))
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn(FIXED, self.text())
        self.assertEqual(editloop.Session(self.store, sid).e['web']['mode'], 'manual')

    def test_preview_counts_the_arbitration_round(self):
        path = self.store.root / 'config.json'
        cfg = json.loads(path.read_text())
        cfg['edit']['max_calls_per_unit'] = 40
        path.write_text(dumps(cfg))
        preview = editloop.preview(self.store, self.src, only=('thm:1.2',))
        self.assertEqual(preview['calls_upper_bound'], 9 * 3 + 4)   # 3 rounds + arbiter, review, 2 confirmations


class BatchSelection(unittest.TestCase):
    def test_changed_and_unchanged_from_split_the_units_in_two(self):
        cfg = editloop.edit_defaults()
        old = NOTE.replace('Every prime is odd.', 'Every odd prime is odd.')
        units = editloop.split_units(NOTE, cfg)
        first = {u['id'] for u in editloop.select_units([dict(u) for u in units], changed_from=old) if u['selected']}
        second = {u['id'] for u in editloop.select_units([dict(u) for u in units], unchanged_from=old) if u['selected']}
        self.assertEqual(first, {'thm:1.2'})
        self.assertEqual(first | second, {u['id'] for u in units})
        self.assertEqual(first & second, set())


class PreflightBlocksSession(unittest.TestCase):
    def test_unlisted_slug_stops_before_anything_is_created(self):
        with tempfile.TemporaryDirectory() as d:
            agy = FakeAgy(d, slug='gemini-4-argon-x')
            store = Store(Path(d) / 'ws')
            cfg = default_config(True)
            cfg['providers']['gemini'] = agy.spec()
            cfg['edit']['check_command'] = []
            (store.root / 'config.json').write_text(dumps(cfg))
            src = Path(d) / 'note.tex'
            src.write_text(NOTE)
            with self.assertRaisesRegex(ValueError, 'agy models'):
                editloop.create(store, src, ('thm:1.2',))
            self.assertEqual(editloop.status(store), [])
            self.assertEqual(agy.calls(), [])


if __name__ == '__main__':
    unittest.main()
