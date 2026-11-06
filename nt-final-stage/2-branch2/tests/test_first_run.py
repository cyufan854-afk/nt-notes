"""Lessons from the first real run (2026-11-06, A100, 3090 requests):
- evidence quotes are compared up to whitespace (the manuscript wraps and indents, a quotation joins with one space);
  triage patches stay exact;
- a polish original may differ from the source in line layout only (the author's decision after the run: 73 of the 76
  rejected originals differed only so); a blank line, a formula, a comment or anything else may not;
- one request still failing after the GPU runner's retries can be accepted explicitly (`next --accept-errors`); it stays
  in the agent's review list. Pending or stale answers can never be accepted."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import branch2 as b2
import nt27b as nt
import qwen_polish as qp
import test_pipeline


def quiet(fn, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = fn(*args)
    return code, out.getvalue()


class QuoteComparison(unittest.TestCase):
    TARGET = '\\begin{theorem}\\label{thm:2.2.10} If $b \\mid a$, $c \\mid a$, and\n\t$\\gcd(b, c)=1$, then $bc \\mid a$.\n\n\\end{theorem}'

    def test_wrapped_lines_are_the_same_quote(self):
        quote = 'If $b \\mid a$, $c \\mid a$, and $\\gcd(b, c)=1$, then $bc \\mid a$.'
        self.assertFalse(nt.found_anywhere(quote, self.TARGET))            # exact: the line break and the tab differ
        self.assertTrue(nt.found_quote(quote, self.TARGET))

    def test_anything_but_whitespace_still_differs(self):
        self.assertFalse(nt.found_quote('If $b | a$, $c | a$, and $\\gcd(b,c)=1$, then $bc | a$.', self.TARGET))
        self.assertFalse(nt.found_quote('(second law) If $b \\mid a$, $c \\mid a$', self.TARGET))
        self.assertFalse(nt.found_quote('   ', self.TARGET))
        self.assertFalse(nt.found_quote('then', self.TARGET))                 # too short to be evidence
        self.assertTrue(nt.found_quote('$bc \\mid a$', self.TARGET))           # a short formula still counts

    def test_collect_refs_uses_it(self):
        with self.subTest('refs'):
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / 'refs').mkdir()
                req = {'id': 'a', 'meta': {'target': self.TARGET, 'line': 1, 'where': 'proof', 'label': 'thm:2.2.10',
                                           'sentence': 'By Theorem 2.2.10.'}}
                answer = {'verdict': 'supports', 'cited_fact': 'If $b \\mid a$, $c \\mid a$, and $\\gcd(b, c)=1$, then $bc \\mid a$.',
                          'missing_hypotheses': [], 'note_zh': '支持'}
                _, stats = nt.collect_refs(Path(d), [req], {'a': {'answer': answer}})
                self.assertEqual((stats['supports'], stats['quote_unverified']), (1, 0))
        self.assertFalse(nt.found_anywhere('If $b \\mid a$, $c \\mid a$, and $\\gcd(b, c)=1$', self.TARGET))   # patches: exact


class PolishLayout(unittest.TestCase):
    BLOCK = ('We now show that every integer\n\t\tsatisfies the bound, and the argument\n\t\tis short.\n\n'
             'A new paragraph starts here and goes on.\n% a comment line\nMore words after the comment follow here.\n'
             'The sum $a +\n\tb$ is computed below in detail.')

    def check(self, original, revised):
        return nt.polish_checks({'original': original, 'revised': revised}, self.BLOCK)

    def test_a_wrapped_and_indented_line_is_located(self):
        old = 'We now show that every integer satisfies the bound, and the argument is short.'
        status, rejected, flagged, _ = self.check(old, old.replace('and the argument', 'and the proof'))
        self.assertEqual(status, 'clean', rejected + flagged)
        hits, tolerant = nt.find_original(self.BLOCK, old)
        self.assertTrue(tolerant)
        self.assertEqual(len(hits), 1)
        start, end = hits[0]
        self.assertEqual(self.BLOCK[start:end], 'We now show that every integer\n\t\tsatisfies the bound, and the argument\n\t\tis short.')
        exact = 'every integer\n\t\tsatisfies'
        i = self.BLOCK.index(exact)
        self.assertEqual(nt.find_original(self.BLOCK, exact), ([(i, i + len(exact))], False))   # exact matches come first

    def test_a_paragraph_break_is_not_a_space(self):
        old = 'and the argument is short. A new paragraph starts here'
        self.assertIn('original 不在本块原文中（不是原样抄写）', self.check(old, old.replace('short', 'brief'))[1])

    def test_joining_a_comment_line_is_rejected(self):
        old = 'and goes on. % a comment line More words after the comment'
        self.assertEqual(self.check(old, old.replace('goes on', 'continues'))[0], 'rejected')

    def test_a_formula_broken_over_lines_must_stay_verbatim(self):
        old = 'The sum $a + b$ is computed below in detail.'
        status, rejected, _, _ = self.check(old, 'The sum $a + b$ is computed below.')
        self.assertEqual(status, 'rejected')
        self.assertTrue(any('公式' in r for r in rejected), rejected)

    def test_two_layout_matches_are_ambiguous(self):
        block = 'one two\nthree four.\nAnd one\ttwo three four.'
        self.assertEqual(len(nt.find_original(block, 'one two three four')[0]), 2)
        self.assertIn('出现 2 次', ' '.join(nt.polish_checks({'original': 'one two three four', 'revised': 'one two three five'}, block)[1]))


class AcceptErrors(unittest.TestCase):
    setUp_book = test_pipeline.PipelineTests.setUp
    respond = test_pipeline.PipelineTests.respond
    call = test_pipeline.PipelineTests.call

    def setUp(self):
        self.setUp_book()
        self.stage_root = self.root / 'nt-final-stage'
        (self.stage_root / '2-branch2').mkdir(parents=True)
        (self.stage_root / 'baseline.tex').write_bytes(self.tex.read_bytes())
        self.job = self.stage_root / '2-branch2' / 'job-27b'
        code, _ = quiet(nt.main, ['prepare', '--tex', str(self.stage_root / 'baseline.tex'), '--out', str(self.job), '--csv', str(self.csv),
                                  '--pre-fix-tex', str(self.tex), '--list', str(self.root / 'none')])
        self.assertEqual(code, 0)
        with patch.object(qp, 'http_json', side_effect=self.respond):
            self.assertEqual(quiet(nt.main, ['ask', str(self.job), '--model', 'test', '--concurrency', '4'])[0], 0)

    def b2(self, *args):
        return quiet(b2.main, ['--root', str(self.stage_root), *args])

    def fail(self, task, index=0, drop=False):
        """Turn one finished answer into a failure (as after a reply cut off at the token limit), or drop it."""
        path = self.job / task / 'responses.jsonl'
        rows = [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines()]
        row = rows[index]
        if drop:
            del rows[index]
        else:
            row.pop('answer')
            row['error'] = 'reply cut off (finish_reason=length)'
        path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
        return row['id']

    def test_a_failed_request_is_named_and_accepted_only_on_request(self):
        rid = self.fail('refs')
        code, out = self.b2('status')
        self.assertIn('[errors]', out)
        self.assertIn(rid, out)
        code, out = self.b2('next')
        self.assertEqual(code, 2)
        self.assertIn('--accept-errors', out)
        code, out = self.b2('next', '--accept-errors')
        self.assertEqual(code, 0, out)                                           # accepted, then collected
        self.assertIn('[polish]', self.b2('status')[1])
        self.assertIn('[error]', (self.job / 'refs' / 'for-claude.md').read_text(encoding='utf-8'))
        state = json.loads((self.stage_root / '2-branch2' / 'stages' / 'state.json').read_text(encoding='utf-8'))
        self.assertEqual(state['accepted_errors'], {'refs': [rid]})
        # a different failure later is not covered by the earlier acceptance
        self.fail('triage')
        self.assertIn('[errors]', self.b2('status')[1])

    def test_pending_answers_can_never_be_accepted(self):
        self.fail('refs')
        self.fail('triage', drop=True)
        code, out = self.b2('next', '--accept-errors')
        self.assertEqual(code, 2)
        self.assertIn('回答还不完整', out)
        self.assertNotIn('accepted_errors', json.loads((self.stage_root / '2-branch2' / 'stages' / 'state.json').read_text(encoding='utf-8'))
                         if (self.stage_root / '2-branch2' / 'stages' / 'state.json').exists() else {})


if __name__ == '__main__':
    unittest.main()
