"""Web arbitration: escalation, batch export, reply import, replay as an arbitration round."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

from coop import editloop
from coop.core import dumps
from test_editloop import EditBase, frame, edit, agreeing, kind_of, NOTE, OLD, NEW, BLOCK

ROOT = Path(__file__).resolve().parents[1]
FIXED = 'Every prime other than $2$ is odd.'
R1 = {'id': 'R1', 'severity': 'blocking', 'category': 'math_error', 'location': 'statement'}


def rejecting(stage, prompt):
    """The reviewer keeps rejecting; everybody else behaves as in ``agreeing``."""
    if kind_of(stage) == 'review':
        return frame('review', 'R1-OBJECTION：漏掉了 p=2。', verdict='revise', issues=[R1], done=False)
    return agreeing(stage, prompt)


def reply(*units, received=None, wrap=True):
    """A web reply as it would be copied out of the chat app."""
    body = []
    if received is not False:
        body.append('收到：' + ', '.join(received or [u for u, _ in units]))
    for uid, text in units:
        body += [f'<<<UNIT {uid}>>>', text, f'<<<UNIT_END {uid}>>>']
    inner = '\n'.join(body)
    return f'好的，下面是裁决。\n```text\n{inner}\n```\n还有问题随时告诉我。' if wrap else inner


def arbitration(new=FIXED, body='ARBITER-REASONING：2 是偶素数，按 R1 修改。', done=True, issues=(BLOCK,)):
    return frame('arbitration', body + '\n' + edit('P1', OLD, new), issues=list(issues), done=done)


class WebBase(EditBase):
    web = True

    def set_web(self, **kw):
        path = self.store.root / 'config.json'
        cfg = json.loads(path.read_text())
        cfg['edit']['web'].update(kw)
        path.write_text(dumps(cfg))

    def batches(self, sid):
        return sorted((self.store.root / sid / 'web').glob('batch-*.md'))


class EscalationTests(WebBase):
    def test_rejection_parks_unit_and_exports_a_batch(self):
        sid, st = self.run_with(rejecting)
        self.assertEqual(st['state'], 'awaiting_web')
        self.assertEqual(st['units'], {'awaiting_web': 1})
        self.assertEqual(st['calls'], 5)  # plan, two blind answers, merge, review; no second round
        self.assertFalse(any(s.startswith('edit-r2') for s in self.seen))
        self.assertEqual(self.text(), NOTE)
        self.assertIn('审查打回', st['awaiting_web'][0]['reason'])
        files = self.batches(sid)
        self.assertEqual([Path(f).name for f in st['web_batches']], ['batch-01.md'])
        batch = files[0].read_text(encoding='utf-8')
        self.assertIn(editloop.WEB_TITLE, batch)
        self.assertIn(OLD, batch)                       # the editable unit, verbatim
        self.assertIn('R1-OBJECTION', batch)            # the history the arbiter needs
        self.assertIn('\\newtheorem{theorem}', batch)   # shared read-only material
        self.assertIn('<<<UNIT thm:1.2>>>', batch)
        self.assertIn('本批单元：thm:1.2', batch)
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('等待网页仲裁', report)

    def test_resume_without_reply_spends_nothing(self):
        sid, st = self.run_with(rejecting)
        before = list(self.seen)
        st = self.resume(sid, rejecting)
        self.assertEqual(self.seen, before)
        self.assertEqual(st['state'], 'awaiting_web')

    def test_import_and_resume_runs_a_reviewed_arbitration_round(self):
        def script(stage, prompt):
            if stage == 'edit-r1-review':
                return rejecting(stage, prompt)
            if stage.startswith('edit-r1-analysis'):
                return frame('analysis', 'SECRET-ANALYSIS\n' + edit('P1', OLD, NEW), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        result = editloop.web_import(self.store, sid, [reply(('thm:1.2', arbitration()))])
        self.assertEqual(result['imported'], ['thm:1.2'])
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['next'], f'coop edit resume {sid}')
        st = self.resume(sid, script)
        self.assertEqual(st['state'], 'completed')
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn(FIXED, self.text())
        self.assertEqual(len(self.commits(sid)), 2)
        r2 = [s for s in self.seen if s.startswith('edit-r2')]
        self.assertEqual(sorted(r2), ['edit-r2-confirm0', 'edit-r2-confirm1', 'edit-r2-review'])
        review = self.prompts['edit-r2-review']
        self.assertIn('ARBITER-REASONING', review)
        self.assertIn('仲裁说明', review)
        self.assertNotIn('SECRET-ANALYSIS', review)   # still no access to the analysts' debate
        self.assertIn('ARBITER-REASONING', self.prompts['edit-r2-confirm1'])
        rec = editloop.Session(self.store, sid).records('thm:1.2')[1]
        self.assertTrue(rec['web'])
        self.assertEqual(set(rec['votes']), {'仲裁', '分析者A', '分析者B', '审查'})
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('第 2 轮（网页仲裁）', report)
        self.assertEqual(self.batches(sid), [])
        saved = list((self.store.root / sid / 'web' / 'replies').glob('*.txt'))
        self.assertEqual(len(saved), 1)

    def test_settled_disagreement_is_not_escalated(self):
        def script(stage, prompt):
            k = kind_of(stage)
            if stage.endswith(('analysis1', 'exchange1')):
                return frame(k, '另一种写法。\n' + edit('P1', OLD, FIXED), done=True)
            if k == 'confirm':
                return frame('confirm', '可以接受。', done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertNotIn('awaiting_web', st)

    def test_unsettled_disagreement_is_escalated(self):
        def script(stage, prompt):
            k = kind_of(stage)
            if stage.endswith(('analysis1', 'exchange1')):
                return frame(k, '另一种写法。\n' + edit('P1', OLD, FIXED), done=True)
            if k == 'confirm':
                return frame('confirm', '不同意，证明仍缺一步。', done=False,
                             issues=[{'id': 'B1', 'severity': 'blocking', 'category': 'missing_step', 'location': 'proof'}])
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'awaiting_web': 1})
        self.assertIn('方案仍不同', st['awaiting_web'][0]['reason'])
        self.assertIn(NEW, self.text())  # round 1 was approved and written before escalating

    def test_oscillation_is_escalated(self):
        def script(stage, prompt):
            k = kind_of(stage)
            if stage.startswith('edit-r1') and k == 'analysis' and stage.endswith('1'):
                return frame(k, '同意改，但证明还缺一步。\n' + edit('P1', OLD, NEW),
                             issues=[{'id': 'B1', 'severity': 'blocking', 'category': 'missing_step', 'location': 'proof'}], done=False)
            if stage.startswith('edit-r2') and k in ('analysis', 'merge'):
                return frame(k, '改回去。\n' + edit('P1', NEW, OLD), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'awaiting_web': 1})
        self.assertIn('震荡', st['awaiting_web'][0]['reason'])
        self.assertIn(NEW, self.text())

    def test_rejected_arbitration_falls_back_to_ordinary_rounds_once(self):
        sid, st = self.run_with(rejecting)
        editloop.web_import(self.store, sid, [reply(('thm:1.2', arbitration()))])
        st = self.resume(sid, rejecting)
        self.assertEqual(st['units'], {'needs_review': 1})
        self.assertIn('网页仲裁后仍未', st['needs_review'][0]['reason'])
        self.assertIn('edit-r4-review', self.seen)      # rounds 1, 3, 4 ordinary; round 2 arbitration
        self.assertNotIn('edit-r5-plan', self.seen)
        self.assertNotIn('edit-r2-plan', self.seen)
        self.assertIn('仲裁者方案与理由', self.prompts['edit-r3-plan'])  # later rounds see the arbitration
        self.assertEqual(self.text(), NOTE)

    def test_arbitration_patch_still_goes_through_precheck(self):
        sid, st = self.run_with(rejecting)
        bad = frame('arbitration', '顺手改 label。\n' + edit('P1', '\\label{thm:1.2}', '\\label{thm:odd}'), issues=[BLOCK], done=True)
        editloop.web_import(self.store, sid, [reply(('thm:1.2', bad))])
        st = self.resume(sid, agreeing)
        self.assertNotIn('edit-r2-review', self.seen)   # refused before the reviewer
        self.assertIn('edit-r3-plan', self.seen)        # back to the ordinary loop, with the reason
        self.assertIn('label', self.prompts['edit-r3-plan'])
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn('\\label{thm:1.2}', self.text())

    def test_after_rounds_delays_escalation(self):
        self.set_web(after_rounds=2)
        sid, st = self.run_with(rejecting)
        self.assertEqual(st['units'], {'awaiting_web': 1})
        self.assertIn('edit-r2-review', self.seen)
        self.assertFalse(any(s.startswith('edit-r3') for s in self.seen))

    def test_precheck_failure_alone_is_not_escalated(self):
        def script(stage, prompt):
            if stage == 'edit-r1-merge':
                return frame('merge', '抄错了。\n' + edit('P1', 'Every prime is even.', NEW), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'done_edited': 1})

    def test_session_created_without_web_keeps_v04_behaviour(self):
        sid = editloop.create(self.store, self.src, ['thm:1.2'])
        with self.store.db() as db:
            cfg = json.loads(db.execute('SELECT config FROM edit_sessions WHERE id=?', (sid,)).fetchone()[0])
            cfg['edit'].pop('web')
            db.execute('UPDATE edit_sessions SET config=? WHERE id=?', (dumps(cfg), sid))
        st = self.resume(sid, rejecting)
        self.assertEqual(st['units'], {'needs_review': 1})
        self.assertIn('edit-r3-review', self.seen)

    def test_new_session_on_same_source_refused_while_awaiting(self):
        self.run_with(rejecting)
        with self.assertRaises(ValueError):
            editloop.create(self.store, self.src, ['thm:1.1'])


class ImportTests(WebBase):
    def park_two(self):
        def script(stage, prompt):
            k = kind_of(stage)
            if k == 'plan':
                return frame('plan', issues=[BLOCK], done=False)
            if k in ('analysis', 'merge'):
                return frame(k, '没有修改。', done=True)
            return rejecting(stage, prompt)
        return self.run_with(script, only=('thm:1.1', 'thm:1.2'))

    def test_batch_file_and_rendered_text_are_refused(self):
        sid, st = self.park_two()
        batch = self.batches(sid)[0].read_text(encoding='utf-8')
        with self.assertRaises(ValueError):
            editloop.web_import(self.store, sid, [batch])
        with self.assertRaises(ValueError):
            editloop.web_import(self.store, sid, ['收到：thm:1.1\n这里只有网页上渲染后的文字。'])

    def test_bad_block_is_reported_and_stays_waiting(self):
        sid, st = self.park_two()
        bad = '<<<COOP_META>>>\n{"kind": "arbitration", "done": tru}\n<<<COOP_BODY>>>\n说明\n<<<COOP_END>>>'
        out = editloop.web_import(self.store, sid, [reply(('thm:1.1', bad), ('thm:1.2', arbitration()))])
        self.assertEqual(out['imported'], ['thm:1.2'])
        self.assertEqual(out['errors'][0]['unit'], 'thm:1.1')
        self.assertIn('JSON', out['errors'][0]['error'])
        self.assertEqual(out['still_waiting'], ['thm:1.1'])
        st = self.resume(sid, rejecting)
        self.assertEqual(st['units'].get('awaiting_web'), 1)
        again = editloop.web_export(self.store, sid)
        self.assertEqual([b['units'] for b in again['batches']], [['thm:1.1']])

    def test_truncated_reply_and_missing_units_are_flagged(self):
        sid, st = self.park_two()
        cut = reply(('thm:1.1', arbitration()), received=['thm:1.1'], wrap=False)
        cut = cut.rsplit('<<<UNIT_END', 1)[0]  # reply stopped mid-unit
        out = editloop.web_import(self.store, sid, [cut])
        self.assertEqual(out['imported'], [])
        self.assertIn('没有正确结束', out['errors'][0]['error'])
        self.assertEqual(out['not_acknowledged'], ['thm:1.2'])  # the paste itself lost thm:1.2
        out = editloop.web_import(self.store, sid, [reply(('thm:1.1', arbitration()), received=['thm:1.1', 'thm:1.2'])])
        self.assertEqual(out['imported'], ['thm:1.1'])
        self.assertEqual(out['listed_but_no_block'], ['thm:1.2'])  # model stopped at 「未完」

    def test_continued_replies_can_be_imported_together(self):
        sid, st = self.park_two()
        first = reply(('thm:1.1', arbitration()), received=['thm:1.1', 'thm:1.2']) + '\n未完：thm:1.2'
        second = reply(('thm:1.2', arbitration()), received=False)
        out = editloop.web_import(self.store, sid, [first, second])
        self.assertEqual(sorted(out['imported']), ['thm:1.1', 'thm:1.2'])
        self.assertNotIn('listed_but_no_block', out)

    def test_wrong_kind_and_check_flag_are_tolerated(self):
        sid, st = self.park_two()
        odd = frame('merge', '说明\n' + edit('P1', OLD, FIXED), issues=[BLOCK], done=True, check=True)
        out = editloop.web_import(self.store, sid, [reply(('thm:1.2', odd))])
        self.assertEqual(out['imported'], ['thm:1.2'])
        answer = editloop.Session(self.store, sid).web_answer('thm:1.2', 2)
        self.assertEqual(answer['meta']['kind'], 'arbitration')
        self.assertFalse(answer['meta']['check'])

    def test_drop_hands_units_to_a_human(self):
        sid, st = self.park_two()
        st = editloop.web_drop(self.store, sid, ['thm:1.1'])
        self.assertEqual(st['units'], {'awaiting_web': 1, 'needs_review': 1})
        self.assertIn('放弃网页仲裁', st['needs_review'][0]['reason'])
        st = editloop.web_drop(self.store, sid, all_units=True)
        self.assertEqual(st['state'], 'needs_review')
        self.assertEqual(self.batches(sid), [])
        with self.assertRaises(ValueError):
            editloop.web_drop(self.store, sid, ['thm:1.1'])

    def test_batches_are_split_by_count_and_size(self):
        sid, st = self.park_two()
        self.assertEqual(len(self.batches(sid)), 1)
        out = editloop.web_export(self.store, sid, batch_units=1)
        self.assertEqual([b['units'] for b in out['batches']], [['thm:1.1'], ['thm:1.2']])
        self.assertIn('第 2/2 批', Path(out['batches'][1]['file']).read_text(encoding='utf-8'))
        out = editloop.web_export(self.store, sid, batch_chars=100)
        self.assertEqual(len(out['batches']), 2)
        self.assertIn('warning', out['batches'][0])
        out = editloop.web_import(self.store, sid, [reply(('thm:1.2', arbitration()), received=['thm:1.2'])])
        self.assertNotIn('not_acknowledged', out)  # thm:1.1 sits in another batch now


class ConfigTests(unittest.TestCase):
    def test_web_settings_are_validated(self):
        from coop.core import default_config
        cfg = default_config(True)
        self.assertTrue(editloop.edit_config(cfg)['web']['enabled'])
        for bad in ({'enabled': 'yes'}, {'after_rounds': 4}, {'batch_units': 0}, {'label': ''}):
            cfg['edit']['web'] = {**editloop.edit_defaults()['web'], **bad}
            with self.assertRaises(ValueError):
                editloop.edit_config(cfg)
        cfg['edit'].pop('web')
        self.assertEqual(editloop.edit_config(cfg)['web']['max_per_unit'], 1)


class WebCLI(unittest.TestCase):
    def test_commands_are_wired(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ws, src = Path(tmp) / 'ws', Path(tmp) / 'note.tex'
            src.write_text(NOTE, encoding='utf-8')

            def cli(*args, code=0, stdin=None):
                p = subprocess.run([sys.executable, '-m', 'coop', '--workspace', str(ws), *args], cwd=ROOT,
                                   capture_output=True, text=True, input=stdin)
                self.assertEqual(p.returncode, code, p.stdout + p.stderr)
                return json.loads(p.stdout)
            cli('init', '--demo')
            cfg = json.loads((ws / 'config.json').read_text())
            cfg['edit']['check_command'] = []
            (ws / 'config.json').write_text(json.dumps(cfg))
            st = cli('edit', 'run', str(src), '--only', 'thm:1.2')
            self.assertEqual(st['state'], 'completed')  # the demo models always agree
            self.assertEqual(cli('edit', 'web', 'export', st['id'])['batches'], [])
            out = cli('edit', 'web', 'import', st['id'], '-', code=2, stdin=reply(('thm:1.2', arbitration())))
            self.assertEqual(out['ignored_not_waiting'], ['thm:1.2'])
            self.assertIn('error', cli('edit', 'web', 'drop', st['id'], 'thm:1.2', code=1))


if __name__ == '__main__':
    unittest.main()
