import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qwen_polish as qp


class StandalonePolishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tex = self.root / 'book.tex'
        self.out = self.root / 'out'
        self.out.mkdir()

    def call(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return qp.main([str(arg) for arg in args])

    def prepare_apply(self, text, revisions, location='General', edits=None):
        self.tex.write_text(text, encoding='utf-8')
        candidate = {
            'id': 'abc123', 'section': 'Test section', 'location': location,
            'original': revisions[0]['original'], 'problem': 'Improve the language.', 'snippets': [],
        }
        row = {
            'id': candidate['id'], 'location': location,
            'answer': {'verdict': 'revise', 'revisions': revisions, 'note_zh': ''},
        }
        (self.out / 'results.jsonl').write_text(json.dumps(row, ensure_ascii=False) + '\n', encoding='utf-8')
        qp.write_review(self.out / 'review.md', [candidate], {candidate['id']: row}, 'test-model', [])
        review = (self.out / 'review.md').read_text(encoding='utf-8').replace('- [ ] 接受', '- [x] 接受')
        for model_text, final_text in (edits or {}).items():
            self.assertEqual(review.count(model_text), 1)
            review = review.replace(model_text, final_text, 1)
        (self.out / 'review.md').write_text(review, encoding='utf-8')

    def apply(self):
        return self.call('--apply', '--tex', self.tex, '--out', self.out)

    def polished_path(self):
        return self.out / 'book.polished.tex'

    def write_candidates(self, originals):
        lines = ['## Test section']
        for index, original in enumerate(originals, 1):
            lines += ['* **Location %d**' % index,
                      '* 原句：' + original,
                      '* 问题：Improve the language.']
        path = self.root / 'candidates.md'
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        self.tex.write_text('\\begin{document}\n' + '\n\n'.join(originals) + '\n\\end{document}\n',
                            encoding='utf-8')
        return path

    def test_apply_requires_exact_original_despite_tolerant_lookup(self):
        old = r'The expression $\sinx$ is used in this sentence.'
        revised = r'The formula $\sinx$ is used in this sentence.'
        text = '\\begin{document}\n' + r'The expression $\sin x$ is used in this sentence.' + '\n\\end{document}\n'
        self.assertEqual(len(qp.find_all(text, old)), 1)  # triage lookup remains whitespace-tolerant
        self.prepare_apply(text, [{'original': old, 'revised': revised}])

        self.assertEqual(self.apply(), 3)
        self.assertEqual(self.polished_path().read_text(encoding='utf-8'), text)
        self.assertNotIn('The formula', self.polished_path().read_text(encoding='utf-8'))

    def test_named_location_never_uses_quote_from_neighbouring_environment(self):
        shared = 'This shared wording is sufficiently long to locate exactly.'
        revised = 'This revised wording is sufficiently long to locate exactly.'
        text = '\\begin{document}\n' + '\n'.join([
            r'\begin{theorem}\label{thm:1.2.1} ' + shared + r' First.\end{theorem}',
            r'\begin{theorem}\label{thm:1.2.2} The target has different wording.\end{theorem}',
            r'\begin{theorem}\label{thm:1.2.3} ' + shared + r' Third.\end{theorem}',
        ]) + '\n\\end{document}\n'
        self.assertIsNone(qp.locate(text, shared, 'Theorem 1.2.2'))
        self.assertIsNotNone(qp.locate(text, shared, 'Theorem 1.2.1'))
        self.prepare_apply(text, [{'original': shared, 'revised': revised}], location='Theorem 1.2.2')

        self.assertEqual(self.apply(), 3)
        self.assertEqual(self.polished_path().read_text(encoding='utf-8'), text)

    def test_named_proof_belongs_to_its_theorem_not_the_next_theorem(self):
        shared = 'This shared proof wording is sufficiently long to locate exactly.'
        revised = 'This revised proof wording is sufficiently long to locate exactly.'
        text = '\\begin{document}\n' + '\n'.join([
            r'\begin{theorem}\label{thm:1.2.1} First statement.\end{theorem}',
            r'\begin{theorem}\label{thm:1.2.2} Target statement.\end{theorem}',
            r'\begin{proof} ' + shared + r'\end{proof}',
            r'\begin{theorem}\label{thm:1.2.3} ' + shared + r'\end{theorem}',
        ]) + '\n\\end{document}\n'
        found = qp.locate(text, shared, 'Proof of Theorem 1.2.2')
        self.assertIsNotNone(found)
        self.assertTrue(text.index(r'\begin{proof}') < found[0] < text.index(r'\end{proof}'))
        self.prepare_apply(text, [{'original': shared, 'revised': revised}],
                           location='Proof of Theorem 1.2.2')

        self.assertEqual(self.apply(), 0)
        published = self.polished_path().read_text(encoding='utf-8')
        self.assertIn(revised, published)
        self.assertIn(r'\label{thm:1.2.3} ' + shared, published)

    def test_distant_alternative_proof_uses_its_explicit_reference(self):
        shared = 'This shared alternative proof wording is sufficiently long to locate exactly.'
        revised = 'This revised alternative proof wording is sufficiently long to locate exactly.'
        text = '\\begin{document}\n' + '\n'.join([
            r'\begin{theorem}\label{thm:1.2.1} Target statement.\end{theorem}',
            r'\begin{theorem}\label{thm:9.9.9} ' + shared + r'\end{theorem}',
            r'\begin{altproof}[Alternative proof of Theorem~\ref{thm:1.2.1}] '
            + shared + r'\end{altproof}',
        ]) + '\n\\end{document}\n'
        found = qp.locate(text, shared, 'Alternative proof of Theorem 1.2.1')
        self.assertIsNotNone(found)
        self.assertTrue(text.index(r'\begin{altproof}') < found[0] < text.index(r'\end{altproof}'))
        self.prepare_apply(text, [{'original': shared, 'revised': revised}],
                           location='Alternative proof of Theorem 1.2.1')

        self.assertEqual(self.apply(), 0)
        published = self.polished_path().read_text(encoding='utf-8')
        self.assertIn(revised, published)
        self.assertIn(r'\label{thm:9.9.9} ' + shared, published)

    def test_invalid_manual_edits_are_skipped_while_safe_edit_is_applied(self):
        safe_old = 'The safe sentence uses an article in the wrong place.'
        safe_new = 'The safe sentence uses an article in the right place.'
        emph_old = 'A second sentence should be phrased more clearly.'
        emph_model = 'A second sentence should be expressed more clearly.'
        emph_bad = r'\emph{A second sentence should be expressed more clearly.'
        comment_old = 'A third sentence should remain fully visible.'
        comment_model = 'A third sentence ought to remain fully visible.'
        comment_bad = '% ' + comment_model
        command_old = r'A fourth sentence is \emph{very important} here.'
        command_model = r'A fourth sentence is \emph{quite important} here.'
        command_bad = command_model.replace(r'\emph', r'\textbf')
        math_old = r'A fifth sentence keeps $\sin x$ and Theorem~\ref{thm:safe}.'
        math_model = r'A fifth sentence preserves $\sin x$ and Theorem~\ref{thm:safe}.'
        math_bad = math_model.replace(r'\sin x', r'\sin y').replace('thm:safe', 'thm:other')
        revisions = [
            {'original': safe_old, 'revised': safe_new},
            {'original': emph_old, 'revised': emph_model},
            {'original': comment_old, 'revised': comment_model},
            {'original': command_old, 'revised': command_model},
            {'original': math_old, 'revised': math_model},
        ]
        text = '\\begin{document}\n' + r'\begin{theorem}\label{thm:safe} Statement.\end{theorem}' + '\n' + '\n'.join([
            safe_old, emph_old, comment_old, command_old, math_old,
        ]) + '\n\\end{document}\n'
        self.prepare_apply(text, revisions, edits={
            emph_model: emph_bad, comment_model: comment_bad,
            command_model: command_bad, math_model: math_bad,
        })

        self.assertEqual(self.apply(), 3)
        published = self.polished_path().read_text(encoding='utf-8')
        self.assertIn(safe_new, published)
        self.assertIn(emph_old, published)
        self.assertIn(comment_old, published)
        self.assertIn(command_old, published)
        self.assertIn(math_old, published)
        self.assertNotIn(emph_bad, published)
        self.assertNotIn(comment_bad, published)
        self.assertNotIn(r'\textbf', published)
        self.assertNotIn(r'\sin y', published)
        self.assertNotIn('thm:other', published)
        self.assertIn('已应用 1 处，跳过 4 处', (self.out / 'apply-report.md').read_text(encoding='utf-8'))

    def test_final_invariant_failure_preserves_existing_published_file(self):
        first_old = 'The first original sentence is ready for a safe edit.'
        first_new = 'The first improved sentence is ready for a safe edit.'
        second_old = 'The second original sentence is ready for a safe edit.'
        second_new = 'The second improved sentence is ready for a safe edit.'
        text = '\\begin{document}\n' + first_old + '\n' + second_old + '\n\\end{document}\n'
        revisions = [
            {'original': first_old, 'revised': first_new},
            {'original': second_old, 'revised': second_new},
        ]
        self.prepare_apply(text, revisions)
        expected = text.replace(first_old, first_new).replace(second_old, second_new)
        sentinel = 'existing published manuscript must survive\n'
        self.polished_path().write_text(sentinel, encoding='utf-8')
        real_invariants = qp.invariants

        def fail_only_for_final_text(candidate):
            result = real_invariants(candidate)
            if candidate == expected:
                result['math'] = result['math'] + ['forced final-validation failure']
            return result

        with patch.object(qp, 'invariants', side_effect=fail_only_for_final_text):
            self.assertEqual(self.apply(), 4)
        self.assertEqual(self.polished_path().read_text(encoding='utf-8'), sentinel)
        self.assertTrue((self.out / 'book.failed.tex').exists())
        self.assertIn('未更新正式的 .polished.tex', (self.out / 'apply-report.md').read_text(encoding='utf-8'))

    def test_presence_requires_every_fragment_in_pre_audit_text(self):
        candidate = {
            'snippets': ['the first quoted fragment', 'the second quoted fragment'],
            'original': 'both quoted fragments', 'location': '',
        }
        self.assertEqual(qp.presence('', candidate, 'only the first quoted fragment remains'), 'unmatched')
        self.assertEqual(
            qp.presence('', candidate, 'the first quoted fragment and the second quoted fragment'), 'gone')
        self.assertEqual(
            qp.presence('the first quoted fragment', candidate,
                        'the first quoted fragment and the second quoted fragment'), 'partial')

    def test_ask_main_records_errors_keeps_success_and_returns_nonzero(self):
        first = 'The first original sentence has enough words for a complete context.'
        second = 'The second original sentence has enough words for a complete context.'
        candidates = self.write_candidates([first, second])
        answer = {
            'verdict': 'revise',
            'revisions': [{'original': first, 'revised': first.replace('original', 'improved')}],
            'note_zh': '',
        }
        malformed_responses = [
            [],
            {'choices': [{'message': None}]},
        ]
        for index, malformed in enumerate(malformed_responses):
            with self.subTest(malformed=malformed):
                out = self.root / ('ask-out-%d' % index)

                def respond(url, payload, key, timeout):
                    user = payload['messages'][1]['content']
                    if first in user and second not in user:
                        return {'model': 'test', 'choices': [{
                            'message': {'content': json.dumps(answer)}, 'finish_reason': 'stop',
                        }]}
                    return malformed

                with patch.object(qp, 'http_json', side_effect=respond):
                    result = self.call(candidates, '--tex', self.tex, '--out', out, '--model', 'test',
                                       '--max-retries', '0', '--concurrency', '1')
                self.assertEqual(result, 3)
                rows = [json.loads(line) for line in (out / 'results.jsonl').read_text(encoding='utf-8').splitlines()]
                self.assertEqual(len(rows), 2)
                self.assertEqual(sum('answer' in row for row in rows), 1)
                self.assertEqual(sum('error' in row for row in rows), 1)
                review = (out / 'review.md').read_text(encoding='utf-8')
                self.assertIn(first.replace('original', 'improved'), review)
                self.assertIn('- 错误：', review)
                self.assertIn('建议修改 1', review)
                self.assertIn('出错 1', review)

    def test_ask_main_keyboard_interrupt_returns_130_after_review(self):
        original = 'The original sentence has enough words for a complete context.'
        candidates = self.write_candidates([original])
        out = self.root / 'interrupt-out'
        with patch.object(qp, 'http_json', side_effect=KeyboardInterrupt):
            result = self.call(candidates, '--tex', self.tex, '--out', out, '--model', 'test',
                               '--max-retries', '0')
        self.assertEqual(result, 130)
        self.assertTrue((out / 'results.jsonl').exists())
        self.assertTrue((out / 'review.md').exists())
        self.assertIn('未处理 1', (out / 'review.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
