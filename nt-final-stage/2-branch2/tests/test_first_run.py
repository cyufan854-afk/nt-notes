"""Lessons from the first real run (2026-11-06, A100, 3090 requests):
- evidence quotes are compared up to whitespace (the manuscript wraps and indents, a quotation joins with one space);
  polish originals and triage patches stay exact;
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

    def test_collect_refs_uses_it_and_polish_stays_exact(self):
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
        block = 'This sentence\ncontains enough text for an exact original quote.'
        self.assertEqual(nt.polish_checks({'original': block.replace('\n', ' '),
                                           'revised': 'This sentence contains enough text for a better original quote.'}, block)[0],
                         'rejected')


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
