import contextlib
import fcntl
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nt27b as nt
import qwen_polish as qp


class MainPipelineOptimizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.tex'
        paragraphs = []
        for index in range(1, 4):
            text = ('Paragraph %d contains the original explanatory sentence with enough words '
                    'for this complete paragraph to be processed correctly.' % index)
            paragraphs.append(r'\begin{theorem}\label{thm:1.1.%d} ' % index + text + r'\end{theorem}')
        self.source.write_text(
            '\\documentclass{article}\n\\begin{document}\n'
            + '\n\n'.join(paragraphs) + '\n\\end{document}\n', encoding='utf-8')
        self.job = self.root / 'job'
        self.assertEqual(self.call(
            'prepare', '--tex', self.source, '--out', self.job, '--task', 'polish',
            '--list', self.root / 'missing-list.txt'), 0)

    def call(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return nt.main([str(arg) for arg in args])

    @staticmethod
    def keep_response(url, payload, key, timeout):
        answer = {'verdict': 'keep', 'revisions': [], 'note_zh': '无需修改'}
        return {
            'model': 'test',
            'choices': [{'message': {'content': json.dumps(answer)}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5},
        }

    def ask_args(self):
        return ('ask', self.job, '--task', 'polish', '--model', 'test', '--max-retries', '0')

    def test_malformed_response_is_one_error_not_a_batch_crash(self):
        def respond(url, payload, key, timeout):
            block = payload['messages'][1]['content'].split('### Block to edit\n', 1)[1]
            if 'Paragraph 1 contains' in block:
                return []
            return self.keep_response(url, payload, key, timeout)

        with patch.object(qp, 'http_json', side_effect=respond):
            result = self.call(*self.ask_args(), '--concurrency', '2')
        self.assertEqual(result, 3)
        rows = nt.read_jsonl(self.job / 'polish' / 'responses.jsonl')
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(bool(row.get('error')) for row in rows), 1)
        self.assertEqual(sum(bool(row.get('answer')) for row in rows), 2)

    def test_unexpected_request_exception_preserves_other_finished_answers(self):
        def sometimes_fail(req, args, key, model):
            if 'Paragraph 1 contains' in req['meta']['block']:
                raise AttributeError('simulated malformed backend object')
            answer = {'verdict': 'keep', 'revisions': [], 'note_zh': '无需修改'}
            return answer, {'attempts': 1, 'prompt_tokens': 10, 'completion_tokens': 5}

        with patch.object(nt, 'ask_one', side_effect=sometimes_fail):
            result = self.call(*self.ask_args(), '--concurrency', '2')
        self.assertEqual(result, 3)
        rows = nt.read_jsonl(self.job / 'polish' / 'responses.jsonl')
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(bool(row.get('answer')) for row in rows), 2)
        self.assertIn('AttributeError', next(row['error'] for row in rows if row.get('error')))

    def test_invalid_numeric_options_fail_before_any_request(self):
        options = [
            ('--sample', '-1'), ('--limit', '-1'), ('--max-retries', '-1'),
            ('--progress-every', '0'), ('--timeout', '0'), ('--top-p', '0'),
            ('--gpu-price', '-1'),
        ]
        for option, value in options:
            with self.subTest(option=option, value=value):
                with patch.object(qp, 'http_json') as request:
                    with self.assertRaises(SystemExit) as raised:
                        self.call(*self.ask_args(), option, value)
                self.assertEqual(raised.exception.code, 2)
                request.assert_not_called()

    def test_zero_limit_and_zero_retries_are_valid(self):
        with patch.object(qp, 'http_json') as request:
            result = self.call(*self.ask_args(), '--limit', '0')
        self.assertEqual(result, 0)
        request.assert_not_called()

    def test_overlapping_ask_is_rejected_before_writing(self):
        lock_path = self.job / '.ask.lock'
        lock_path.touch()
        with lock_path.open('a+') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            with patch.object(qp, 'http_json') as request:
                result = self.call(*self.ask_args())
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        self.assertEqual(result, 2)
        request.assert_not_called()
        self.assertFalse((self.job / 'polish' / 'responses.jsonl').exists())

    def test_failed_full_reprepare_leaves_existing_job_usable(self):
        with patch.object(qp, 'http_json', side_effect=self.keep_response):
            self.assertEqual(self.call(*self.ask_args()), 0)
        before = {
            str(path.relative_to(self.job)): path.read_bytes()
            for path in self.job.rglob('*') if path.is_file()
        }
        self.source.write_text(
            self.source.read_text(encoding='utf-8').replace('Paragraph 1 contains', 'Changed paragraph contains'),
            encoding='utf-8')
        result = self.call(
            'prepare', '--tex', self.source, '--out', self.job, '--task', 'all',
            '--csv', self.root / 'missing.csv', '--pre-fix-tex', self.source,
            '--list', self.root / 'missing-list.txt')
        self.assertEqual(result, 2)
        after = {
            str(path.relative_to(self.job)): path.read_bytes()
            for path in self.job.rglob('*') if path.is_file()
        }
        self.assertEqual(after, before)
        self.assertEqual(self.call('collect', self.job), 0)


class CitationAndEvidenceTests(unittest.TestCase):
    def test_identical_citation_sentences_in_different_proofs_are_both_checked(self):
        repeated = r'Let $g$ be a primitive root modulo $p$ (Theorem~\ref{thm:cited}).'
        tex = '\n'.join([
            r'\begin{document}',
            r'\begin{theorem}\label{thm:cited} The cited result has its own precise hypotheses.\end{theorem}',
            r'\begin{theorem}\label{thm:first} The first statement needs one particular argument.\end{theorem}',
            r'\begin{proof}', repeated, r'\end{proof}',
            r'\begin{theorem}\label{thm:second} The second statement needs a different argument.\end{theorem}',
            r'\begin{proof}', repeated, r'\end{proof}',
            r'\end{document}',
        ])
        with tempfile.TemporaryDirectory() as directory:
            nt.prepare_refs(nt.Doc(tex), Path(directory))
            rows = nt.read_jsonl(Path(directory) / 'refs' / 'requests.jsonl')
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row['id'] for row in rows}), 2)
        self.assertEqual({row['meta']['where'] for row in rows}, {'proof of thm:first', 'proof of thm:second'})
        prompts = {row['meta']['where']: row['messages'][1]['content'] for row in rows}
        self.assertIn('The first statement needs one particular argument.', prompts['proof of thm:first'])
        self.assertIn('The second statement needs a different argument.', prompts['proof of thm:second'])

    def test_short_formula_can_be_verbatim_evidence(self):
        self.assertTrue(nt.found_anywhere('$x>0$', 'The assumption is $x>0$.'))
        self.assertFalse(nt.found_anywhere('$x>1$', 'The assumption is $x>0$.'))
        self.assertFalse(nt.found_anywhere('   ', 'The assumption is $x>0$.'))
        self.assertFalse(nt.found_anywhere('it', 'The assumption is $x>0$.'))


if __name__ == '__main__':
    unittest.main()
