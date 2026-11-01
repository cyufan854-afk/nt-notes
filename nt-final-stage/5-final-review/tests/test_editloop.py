import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from coop.core import Store, default_config, dumps
from coop.protocol import encode
from coop.providers import invoke
from coop import editloop

NOTE = r'''\documentclass{article}
\usepackage{amsthm,amssymb}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{definition}{Definition}[section]
\begin{document}
\section*{Notation and Conventions}
We write $\mathbb{Z}$ for the integers, and all letters denote integers unless stated otherwise in the text.

\section{Divisibility}
\begin{definition}[divisibility]\label{def:1.1}
	Let $d,n$ be integers. We say $d$ divides $n$ if $n=dk$ for some integer $k$.
\end{definition}
\begin{theorem}\label{thm:1.1}
	If $a\mid b$ and $b\neq 0$, then $|a|\le|b|$.
\end{theorem}
\begin{proof}
	Write $b=ak$ with $k\ne0$, so $|b|=|a||k|\ge|a|$ by Definition~\ref{def:1.1}.
\end{proof}
\begin{theorem}\label{thm:1.2}
	Every prime is odd.
\end{theorem}
\begin{proof}
	By Theorem~\ref{thm:1.1}.
\end{proof}
\end{document}
'''
OLD = 'Every prime is odd.'
NEW = 'Every prime $p>2$ is odd.'
BLOCK = {'id': 'P1', 'severity': 'blocking', 'category': 'math_error', 'location': 'statement'}


def edit(issue, old, new):
    return f'<<<COOP_EDIT {issue}>>>\n<<<COOP_OLD>>>\n{old}\n<<<COOP_NEW>>>\n{new}\n<<<COOP_EDIT_END>>>'


def frame(kind, body='说明', **meta):
    meta.setdefault('issues', [])
    return encode({'kind': kind, **meta}, body)


def kind_of(stage):
    import re
    return re.sub(r'\d+$', '', stage.split('-')[2])


class EditBase(unittest.TestCase):
    compile_cmd = []
    web = False  # these tests pin the v0.4 loop; web arbitration has its own tests

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.store = Store(root / 'ws')
        cfg = default_config(True)
        cfg['edit']['check_command'] = self.compile_cmd
        cfg['edit']['web']['enabled'] = self.web
        (self.store.root / 'config.json').write_text(dumps(cfg))
        self.src = root / 'note.tex'
        self.src.write_text(NOTE, encoding='utf-8')
        self.seen, self.prompts = [], {}

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, script, only=('thm:1.2',), **kw):
        """script(stage, prompt) -> raw response or None for the demo default."""
        def fake(spec, prompt, stage, folder, timeout):
            self.seen.append(stage)
            self.prompts[stage] = prompt
            out = script(stage, prompt)
            return invoke(spec, prompt, stage, folder, timeout) if out is None else out
        with patch('coop.core.invoke', side_effect=fake):
            sid = editloop.create(self.store, self.src, only, **kw)
            return sid, editloop.execute(self.store, sid)

    def resume(self, sid, script, **kw):
        def fake(spec, prompt, stage, folder, timeout):
            self.seen.append(stage)
            self.prompts[stage] = prompt
            out = script(stage, prompt)
            return invoke(spec, prompt, stage, folder, timeout) if out is None else out
        with patch('coop.core.invoke', side_effect=fake):
            return editloop.execute(self.store, sid, **kw)

    def text(self):
        return self.src.read_text(encoding='utf-8')

    def commits(self, sid):
        return editloop.Session.git(self.store.root / sid / 'backup', 'log', '--oneline').splitlines()


def agreeing(stage, prompt, old=OLD, new=NEW):
    k = kind_of(stage)
    if k == 'plan':
        return frame('plan', issues=[BLOCK], done=False)
    if k in ('analysis', 'merge'):
        return frame(k, '修正：2 是偶素数。\n' + edit('P1', old, new), done=True)
    if k == 'review':
        return frame('review', '补丁正确。', verdict='approve', done=True)
    return None


class EditLoopTests(EditBase):
    def test_clean_units_cost_four_calls_and_leave_source(self):
        sid, st = self.run_with(lambda s, p: None, only=())
        self.assertEqual(st['state'], 'completed')
        self.assertEqual(st['units'], {'done_unchanged': 4})
        self.assertEqual(st['calls'], 16)
        self.assertEqual(self.text(), NOTE)
        self.assertEqual(len(self.commits(sid)), 1)

    def test_identical_proposals_skip_exchange_and_are_applied_with_backup(self):
        sid, st = self.run_with(agreeing)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn(NEW, self.text())
        self.assertNotIn(OLD, self.text())
        self.assertFalse(any('exchange' in s or 'confirm' in s for s in self.seen))
        self.assertEqual(st['calls'], 5)
        log = self.commits(sid)
        self.assertEqual(len(log), 2)
        original = editloop.Session.git(self.store.root / sid / 'backup', 'show', 'HEAD~1:note.tex')
        self.assertEqual(original + '\n', NOTE)

    def test_disagreement_runs_exchange_merge_and_confirm(self):
        other = 'Every prime other than $2$ is odd.'

        def script(stage, prompt):
            k = kind_of(stage)
            if stage.endswith('analysis1') or stage.endswith('exchange1'):
                return frame(k, '另一种写法。\n' + edit('P1', OLD, other), done=True)
            if k == 'exchange':
                self.assertIn(other, prompt)  # each analyst sees the other's blind answer
                return frame(k, '坚持原方案。\n' + edit('P1', OLD, NEW), done=True)
            if k == 'confirm':
                return frame('confirm', '可以接受。', done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn('edit-r1-exchange0', self.seen)
        self.assertIn('edit-r1-confirm1', self.seen)
        self.assertNotIn('edit-r1-confirm0', self.seen)
        self.assertEqual(st['calls'], 8)

    def test_reviewer_never_sees_the_debate(self):
        def script(stage, prompt):
            k = kind_of(stage)
            if k == 'analysis':
                return frame(k, 'SECRET-ANALYSIS-TEXT\n' + edit('P1', OLD, NEW), done=True)
            if k == 'merge':
                return frame(k, 'MERGE-JUSTIFICATION\n' + edit('P1', OLD, NEW), done=True)
            return agreeing(stage, prompt)
        self.run_with(script)
        review_prompt = self.prompts['edit-r1-review']
        self.assertNotIn('SECRET-ANALYSIS-TEXT', review_prompt)
        self.assertIn('MERGE-JUSTIFICATION', review_prompt)
        self.assertIn('SECRET-ANALYSIS-TEXT', self.prompts['edit-r1-merge'])

    def test_rejection_then_second_round(self):
        def script(stage, prompt):
            if stage == 'edit-r1-review':
                return frame('review', 'R1：这样改丢了 p=2 的说明。', verdict='revise',
                             issues=[{'id': 'R1', 'severity': 'blocking', 'category': 'math_error', 'location': 'statement'}], done=False)
            if stage.startswith('edit-r2') and kind_of(stage) in ('analysis', 'merge'):
                self.assertIn('R1：这样改丢了', prompt)  # history carries the reviewer's objection
                return frame(kind_of(stage), '按审查意见修改。\n' + edit('P1', OLD, 'Every prime other than $2$ is odd.'), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn('Every prime other than $2$ is odd.', self.text())
        self.assertEqual(len(self.commits(sid)), 2)  # round 1 was never written
        self.assertIn('审查：revise', self.prompts['edit-r2-plan'])

    def test_unqualified_objections_are_counted_as_done(self):
        def script(stage, prompt):
            k = kind_of(stage)
            if k == 'plan':
                return frame('plan', '想改措辞。', issues=[{'id': 'P1', 'severity': 'note', 'category': 'style'}], done=False)
            if k == 'analysis':
                return frame(k, '我觉得不够好。', issues=[{'id': 'A1', 'severity': 'blocking', 'category': 'math_error'}], done=False)
            if k == 'review':
                return frame('review', '换个说法更好。', verdict='revise',
                             issues=[{'id': 'R1', 'severity': 'blocking', 'category': 'style', 'location': 'statement'}], done=False)
            return None
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'done_unchanged': 1})
        self.assertEqual(st['calls'], 4)
        report = (self.store.root / sid / 'report.md').read_text(encoding='utf-8')
        self.assertIn('按 done=true 计', report)
        self.assertIn('按 approve_with_notes 计', report)
        self.assertIn('已降为 note', report)

    def test_precheck_failure_skips_review_and_feeds_next_round(self):
        def script(stage, prompt):
            if stage == 'edit-r1-merge':
                return frame('merge', '抄错了。\n' + edit('P1', 'Every prime is even.', NEW), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertNotIn('edit-r1-review', self.seen)
        self.assertIn('未通过', self.prompts['edit-r2-plan'])
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn(NEW, self.text())

    def test_math_scope_drops_style_edits(self):
        def script(stage, prompt):
            k = kind_of(stage)
            if k == 'plan':
                return frame('plan', issues=[{'id': 'P1', 'severity': 'note', 'category': 'style'}], done=True)
            if k in ('analysis', 'merge'):
                return frame(k, '润色。\n' + edit('P1', OLD, 'All primes are odd.'), done=True)
            return None
        sid, st = self.run_with(script)
        self.assertEqual(self.text(), NOTE)
        self.assertEqual(st['units'], {'done_unchanged': 1})
        self.assertIn('不是 blocking', (self.store.root / sid / 'report.md').read_text(encoding='utf-8'))

    def test_oscillation_detected_after_written_round(self):
        def script(stage, prompt):
            k = kind_of(stage)
            if stage == 'edit-r1-confirm1' or stage == 'edit-r1-confirm0':
                return None
            if stage.startswith('edit-r1') and k == 'analysis' and stage.endswith('1'):
                # analyst B accepts the patch in principle but still has a real objection afterwards
                return frame(k, '同意改，但证明还缺一步。\n' + edit('P1', OLD, NEW),
                             issues=[{'id': 'B1', 'severity': 'blocking', 'category': 'missing_step', 'location': 'proof'}], done=False)
            if stage.startswith('edit-r2') and k in ('analysis', 'merge'):
                return frame(k, '改回去。\n' + edit('P1', NEW, OLD), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'needs_review': 1})
        self.assertIn(NEW, self.text())  # round 1 stays; the revert was refused
        self.assertEqual(len(self.commits(sid)), 2)
        self.assertIn('震荡', st['needs_review'][0]['reason'])

    def test_max_rounds_hands_over_to_human(self):
        def script(stage, prompt):
            if kind_of(stage) == 'review':
                return frame('review', '不对。', verdict='revise',
                             issues=[{'id': 'R1', 'severity': 'blocking', 'category': 'math_error', 'location': 'statement'}], done=False)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'needs_review': 1})
        self.assertEqual(self.text(), NOTE)
        self.assertIn('edit-r3-review', self.seen)
        self.assertNotIn('edit-r4-plan', self.seen)
        self.assertEqual(st['state'], 'needs_review')

    def test_resume_reuses_calls_and_never_double_applies(self):
        fail = {'review': True}

        def flaky(stage, prompt):
            if stage == 'edit-r1-review' and fail['review']:
                fail['review'] = False
                raise RuntimeError('网络错误')
            return agreeing(stage, prompt)
        sid, st = self.run_with(flaky)
        self.assertEqual(st['state'], 'paused')
        self.assertEqual(self.text(), NOTE)
        st = self.resume(sid, flaky)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertEqual(self.text().count(NEW), 1)
        self.assertEqual(self.seen.count('edit-r1-plan'), 1)
        self.assertEqual(st['calls'], 6)  # 5 successful + 1 failed attempt
        again = self.resume(sid, flaky)
        self.assertEqual(again['calls'], 6)
        self.assertEqual(self.text().count(NEW), 1)

    def test_crash_between_write_and_backup_commit_is_recovered(self):
        real = editloop.Session.backup_commit
        state = {'n': 0}

        def boom(self_, data, message):
            state['n'] += 1
            if state['n'] == 1 and '第 1 轮' in message:
                raise KeyboardInterrupt
            return real(self_, data, message)
        with patch.object(editloop.Session, 'backup_commit', boom):
            sid, st = self.run_with(agreeing)
        self.assertEqual(st['state'], 'paused')
        self.assertIn(NEW, self.text())  # the write happened, the commit did not
        st = self.resume(sid, agreeing)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertEqual(self.text().count(NEW), 1)
        self.assertEqual(len(self.commits(sid)), 2)

    def test_interrupted_write_plus_external_edit_can_be_accepted(self):
        real = editloop.Session.backup_commit

        def boom(self_, data, message):
            if '第 1 轮' in message:
                raise KeyboardInterrupt
            return real(self_, data, message)
        with patch.object(editloop.Session, 'backup_commit', boom):
            sid, st = self.run_with(agreeing)
        self.src.write_text(self.text().replace('integers unless', 'whole numbers unless'), encoding='utf-8')
        st = self.resume(sid, agreeing)
        self.assertEqual(st['state'], 'paused')
        st = self.resume(sid, agreeing, accept_external=True)
        self.assertEqual(st['units'], {'needs_review': 1})  # its text changed under it; a human decides
        self.assertIn('whole numbers', self.text())

    def test_old_workspace_config_gets_role_timeouts(self):
        cfg = json.loads((self.store.root / 'config.json').read_text())
        for k in ('exchange0', 'exchange1', 'merge', 'confirm0', 'confirm1'):
            cfg['timeouts'].pop(k)
        cfg.pop('edit')
        (self.store.root / 'config.json').write_text(dumps(cfg))
        loaded = editloop.load_config(self.store)
        self.assertEqual(loaded['timeouts']['exchange1'], 1200)
        self.assertEqual(loaded['edit']['roles']['reviewer'], 'claude')

    def test_external_change_pauses_until_accepted(self):
        sid = editloop.create(self.store, self.src, ['thm:1.2'])
        self.src.write_text(NOTE.replace('integers unless', 'whole numbers unless'), encoding='utf-8')
        st = self.resume(sid, agreeing)
        self.assertEqual(st['state'], 'paused')
        self.assertIn('coop 之外', st['error'])
        self.assertNotIn(NEW, self.text())
        st = self.resume(sid, agreeing, accept_external=True)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn('whole numbers', self.text())
        self.assertEqual(len(self.commits(sid)), 3)

    def test_whitespace_tolerant_match_handles_tabs(self):
        old = '\tWrite $b=ak$ with $k\\ne0$, so'
        typed = '    Write $b=ak$ with $k\\ne0$, so'
        self.assertIn(old, NOTE)

        def script(stage, prompt):
            k = kind_of(stage)
            if k in ('analysis', 'merge'):
                return frame(k, '补引用。\n' + edit('P1', typed, '\tWrite $b=ak$ with $k\\ne0$ (as $b\\ne0$), so'), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script, only=('thm:1.1',))
        self.assertIn('(as $b\\ne0$)', self.text())
        self.assertNotIn('\t\tWrite', self.text())
        rec = editloop.Session(self.store, sid).records('thm:1.1')[0]
        self.assertEqual(rec['precheck']['matches'], ['whitespace'])

    def test_label_change_is_rejected_before_review(self):
        def script(stage, prompt):
            if stage == 'edit-r1-merge':
                return frame('merge', '\n' + edit('P1', '\\label{thm:1.2}', '\\label{thm:odd}'), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        rec = editloop.Session(self.store, sid).records('thm:1.2')[0]
        self.assertIn('label', rec['precheck']['reason'])
        self.assertNotIn('edit-r1-review', self.seen)

    def test_format_error_gets_one_retry(self):
        bad = {'left': 1}

        def script(stage, prompt):
            if stage == 'edit-r1-analysis0' and bad['left']:
                bad['left'] -= 1
                return frame('analysis', '<<<COOP_EDIT P1>>>\n<<<COOP_OLD>>>\nEvery prime is odd.\n<<<COOP_EDIT_END>>>', done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        self.assertEqual(st['units'], {'done_edited': 1})
        self.assertIn('格式校验', self.prompts['edit-r1-analysis0'])
        self.assertEqual(st['calls'], 6)

    def test_restore_original_and_refuse_resume(self):
        sid, st = self.run_with(agreeing)
        self.assertIn(NEW, self.text())
        out = editloop.restore(self.store, sid)
        self.assertEqual(self.text(), NOTE)
        self.assertEqual(len(self.commits(sid)), 3)
        with self.assertRaises(ValueError):
            editloop.execute(self.store, sid)
        self.assertEqual(out['source'], str(self.src.resolve()))

    def test_second_session_on_same_source_is_refused_while_open(self):
        sid = editloop.create(self.store, self.src, ['thm:1.2'])
        with self.assertRaises(ValueError):
            editloop.create(self.store, self.src, ['thm:1.1'])


class UnitTests(unittest.TestCase):
    def test_split_and_select(self):
        e = editloop.edit_defaults()
        units = editloop.split_units(NOTE, e)
        self.assertEqual([u['id'] for u in units], ['sec:notation-and-conventions', 'def:1.1', 'thm:1.1', 'thm:1.2'])
        self.assertIn('\\section{Divisibility}', units[1]['text'])  # headings travel with the next unit
        self.assertIn('\\begin{proof}', units[2]['text'])
        self.assertEqual(''.join(u['text'] for u in units),
                         NOTE[NOTE.index('\\begin{document}') + len('\\begin{document}'):NOTE.rindex('\\end{document}')])
        changed = NOTE.replace(OLD, NEW)
        sel = editloop.select_units(editloop.split_units(changed, e), changed_from=NOTE)
        self.assertEqual([u['id'] for u in sel if u['selected']], ['thm:1.2'])

    def test_parse_edits_rejects_broken_blocks(self):
        good = editloop.parse_edits('x\n' + edit('P1', 'a\n\tb', '') + '\ny')
        self.assertEqual(good, [{'issue': 'P1', 'old': 'a\n\tb', 'new': ''}])
        for bad in ('<<<COOP_OLD>>>\nx', '<<<COOP_EDIT P1>>>\nx', '<<<COOP_EDIT>>>\n<<<COOP_OLD>>>\n\n<<<COOP_NEW>>>\ny\n<<<COOP_EDIT_END>>>'):
            with self.assertRaises(ValueError):
                editloop.parse_edits(bad)

    def test_context_lists_users_and_cited_statements(self):
        e = editloop.edit_defaults()
        unit = editloop.split_units(NOTE, e)[2]
        ctx = editloop.build_context(NOTE, unit['text'], e)
        self.assertTrue(any('def:1.1' in c and 'divides' in c for c in ctx['referenced']))
        self.assertTrue(any('thm:1.1' in c for c in ctx['cited_by']))
        self.assertIn('Notation', ctx['background'])
        self.assertIn('\\newtheorem{theorem}', ctx['macros'])


@unittest.skipUnless(shutil.which('latexmk') and shutil.which('pdflatex'), 'needs latexmk')
class CompileTests(EditBase):
    compile_cmd = editloop.edit_defaults()['check_command']

    def test_compile_failure_blocks_the_write(self):
        def script(stage, prompt):
            if stage == 'edit-r1-merge':
                return frame('merge', '\n' + edit('P1', OLD, 'Every prime \\undefinedmacro is odd.'), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        rec = editloop.Session(self.store, sid).records('thm:1.2')[0]
        self.assertIn('编译失败', rec['precheck']['reason'])
        self.assertIn(NEW, self.text())  # round 2 applied the clean patch
        self.assertNotIn('undefinedmacro', self.text())

    def test_new_undefined_reference_blocks_the_write(self):
        def script(stage, prompt):
            if kind_of(stage) == 'merge':
                return frame('merge', '\n' + edit('P1', 'By Theorem~\\ref{thm:1.1}.', 'By Theorem~\\ref{thm:9.9}.'), done=True)
            return agreeing(stage, prompt)
        sid, st = self.run_with(script)
        rec = editloop.Session(self.store, sid).records('thm:1.2')[0]
        self.assertIn('未定义引用', rec['precheck']['reason'])
        self.assertEqual(self.text(), NOTE)


if __name__ == '__main__':
    unittest.main()
