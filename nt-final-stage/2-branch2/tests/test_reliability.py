import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nt27b as nt
import qwen_polish as qp


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.tex'
        self.text = 'This is the original explanatory sentence with enough words for the paragraph to be processed correctly.'
        self.source.write_text('\\documentclass{article}\n\\begin{document}\n' + self.text + '\n\\end{document}\n', encoding='utf-8')
        self.job = self.root / 'job'
        self.call('prepare', '--tex', self.source, '--out', self.job, '--task', 'polish', '--list', self.root/'missing.txt')

    def call(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return nt.main([str(x) for x in args])

    def ask(self, answer=None, **extra):
        if answer is None:
            answer = {'verdict': 'revise', 'revisions': [{'original': self.text, 'revised': self.text.replace('the original', 'an improved')}], 'note_zh': '冠词修改'}
        def respond(url, payload, key, timeout):
            return {'model': 'test', 'choices': [{'message': {'content': json.dumps(answer)}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 50, 'completion_tokens': 20}}
        args = ['ask', self.job, '--task', 'polish', '--model', 'test', '--max-retries', '0']
        for k, v in extra.items(): args.extend(['--'+k.replace('_','-'), str(v)])
        with patch.object(qp, 'http_json', side_effect=respond):
            return self.call(*args)

    def test_formula_control_word_space_is_protected(self):
        old = r'This is represented by $\sin x$ in the equation.'
        self.assertEqual(nt.polish_checks({'original': old, 'revised': old.replace(r'\sin x', r'\sinx')}, old)[0], 'rejected')

    def test_formula_text_spaces_are_protected(self):
        old = r'The label is $\text{a b}$ in the equation.'
        self.assertEqual(nt.polish_checks({'original': old, 'revised': old.replace('a b','ab')}, old)[0], 'rejected')

    def test_removing_nonzero_requires_review(self):
        old = 'For every nonzero integer $n$, the claimed conclusion follows.'
        self.assertEqual(nt.polish_checks({'original': old, 'revised': old.replace('nonzero ', '')}, old)[0], 'flagged')

    def test_changing_quantifier_requires_review(self):
        old = 'For every integer $n$, the claimed conclusion follows.'
        self.assertEqual(nt.polish_checks({'original': old, 'revised': old.replace('every', 'some')}, old)[0], 'flagged')

    def test_original_must_be_exact_not_whitespace_equivalent(self):
        block = 'This sentence\ncontains enough text for an exact original quote.'
        self.assertEqual(nt.polish_checks({'original': block.replace('\n', ' '), 'revised': 'This sentence contains enough text for a better original quote.'}, block)[0], 'rejected')

    def test_small_grammar_change_remains_eligible(self):
        self.assertEqual(nt.polish_checks({'original': self.text, 'revised': self.text.replace('the original', 'an improved')}, self.text)[0], 'clean')

    def test_refs_requires_all_fields(self):
        with self.assertRaises(ValueError): nt.validate_refs({'verdict': 'supports'})

    def test_refs_support_requires_nonempty_evidence(self):
        with self.assertRaises(ValueError): nt.validate_refs({'verdict': 'supports', 'cited_fact': '', 'missing_hypotheses': [], 'note_zh': '支持'})

    def test_refs_support_cannot_have_missing_hypotheses(self):
        with self.assertRaises(ValueError): nt.validate_refs({'verdict': 'supports', 'cited_fact': 'A literal theorem quotation.', 'missing_hypotheses': ['nonzero'], 'note_zh': '支持'})

    def test_triage_resolved_requires_evidence(self):
        with self.assertRaises(ValueError): nt.validate_triage({'verdict': 'resolved', 'evidence': '', 'patch_original': '', 'patch_revised': '', 'note_zh': '已解决'})

    def test_empty_ref_quote_cannot_bypass_collector(self):
        (self.root/'refs').mkdir()
        req = {'id': 'abc', 'meta': {'target': 'The original theorem statement.', 'line': 1, 'where': 'proof', 'label': 'thm:x', 'sentence': 'By the theorem.'}}
        _, stats = nt.collect_refs(self.root, [req], {'abc': {'answer': {'verdict': 'supports', 'cited_fact': '', 'missing_hypotheses': [], 'note_zh': '支持'}}})
        self.assertEqual(stats['supports'], 0)
        self.assertEqual(stats['quote_unverified'], 1)

    def test_endpoint_change_reissues_requests(self):
        self.ask()
        (self.job/'polish/responses.jsonl').write_text((self.job/'polish/responses.jsonl').read_text(), encoding='utf-8')
        self.ask(base_url='http://another.test/v1')
        rows = nt.read_jsonl(self.job/'polish/responses.jsonl')
        self.assertEqual(rows[0].get('base_url'), 'http://another.test/v1')

    def test_sampling_changes_fingerprint(self):
        req = nt.read_jsonl(self.job/'polish/requests.jsonl')[0]
        a = NS(thinking='off', json_schema=False, base_url='http://one/v1', top_p=.8)
        b = NS(thinking='off', json_schema=False, base_url='http://one/v1', top_p=.2)
        self.assertNotEqual(nt.fingerprint(req, a, 'test'), nt.fingerprint(req, b, 'test'))

    def test_budget_changes_fingerprint(self):
        req = nt.read_jsonl(self.job/'polish/requests.jsonl')[0]
        a = NS(thinking='off', json_schema=False, base_url='http://one/v1', top_p=.8)
        self.assertNotEqual(nt.fingerprint(req, a, 'test'), nt.fingerprint(dict(req, max_tokens=req['max_tokens']+1), a, 'test'))

    def test_request_tamper_cannot_be_collected(self):
        self.ask()
        path = self.job/'polish/requests.jsonl'
        rows = nt.read_jsonl(path); rows[0]['messages'][0]['content'] += '\nChanged prompt.'; nt.write_jsonl(path, rows)
        self.assertNotEqual(self.call('collect', self.job), 0)
        stats = json.loads((self.job/'summary.json').read_text())['polish']
        self.assertEqual(stats['answered'], 0)
        self.assertEqual(stats['stale'], 1)

    def test_legacy_response_cannot_be_applied(self):
        self.ask()
        path = self.job/'polish/responses.jsonl'; rows = nt.read_jsonl(path)
        rows[0].pop('request_hash', None); nt.write_jsonl(path, rows)
        self.assertNotEqual(self.call('apply', self.job, '--tex', self.source, '--accept-clean'), 0)
        self.assertFalse((self.job/'polish/source.polished.tex').exists())

    def test_failed_requests_return_failure(self):
        with patch.object(qp, 'http_json', side_effect=ValueError('bad backend response')):
            result = self.call('ask', self.job, '--task', 'polish', '--model', 'test', '--max-retries', '0')
        self.assertNotEqual(result, 0)

    def test_requested_compilation_failure_does_not_publish(self):
        self.ask()
        with patch.object(nt, 'compile_check', return_value=(False, 'test compiler failed')):
            result = self.call('apply', self.job, '--tex', self.source, '--accept-clean', '--compile')
        self.assertNotEqual(result, 0)
        self.assertFalse((self.job/'polish/source.polished.tex').exists())
        self.assertTrue((self.job/'polish/apply-report.md').exists())

    def test_missing_requested_compiler_is_failure(self):
        self.ask()
        with patch.object(nt, 'compile_check', return_value=(None, 'compiler unavailable')):
            result = self.call('apply', self.job, '--tex', self.source, '--accept-clean', '--compile')
        self.assertNotEqual(result, 0)
        self.assertFalse((self.job/'polish/source.polished.tex').exists())

    def test_manual_unbalanced_replacement_is_rejected(self):
        self.ask(); self.call('collect', self.job)
        path = self.job/'polish/review.md'
        content = path.read_text().replace('- [ ] 接受', '- [x] 接受')
        content = content.replace('an improved explanatory', r'\emph{an improved explanatory')
        path.write_text(content)
        self.call('apply', self.job, '--tex', self.source)
        self.assertNotIn(r'\emph{', (self.job/'polish/source.polished.tex').read_text())

    def test_partial_prepare_rejects_changed_shared_snapshot(self):
        self.source.write_text(self.source.read_text().replace('the original', 'another original'))
        self.assertNotEqual(self.call('prepare', '--tex', self.source, '--out', self.job, '--task', 'polish', '--list', self.root/'missing.txt'), 0)
        self.assertIn('the original', (self.job/'nt.prepared.tex').read_text())

    def test_prepared_snapshot_tamper_blocks_collect(self):
        self.ask()
        path = self.job/'nt.prepared.tex'; path.write_text(path.read_text()+'changed')
        self.assertNotEqual(self.call('collect', self.job), 0)


    def test_verify_missing_answers_fails(self):
        self.assertNotEqual(self.call('verify', self.job), 0)

    def test_verify_completed_answers_pass(self):
        self.ask()
        self.assertEqual(self.call('verify', self.job), 0)

    def test_manual_new_comment_is_rejected(self):
        old = self.text
        self.assertEqual(nt.polish_checks({'original':old,'revised':'% '+old},old)[0], 'rejected')

    def test_new_latex_command_is_rejected(self):
        old = self.text
        self.assertEqual(nt.polish_checks({'original':old,'revised':r'\vspace{3cm}'+old},old)[0], 'rejected')

    def test_cached_invalid_answer_is_requested_again(self):
        self.ask()
        path=self.job/'polish/responses.jsonl';rows=nt.read_jsonl(path)
        rows[0]['answer']={'verdict':'keep'};nt.write_jsonl(path,rows)
        self.ask()
        self.assertEqual(self.call('verify',self.job),0)

    def test_apply_without_answers_fails(self):
        self.assertNotEqual(self.call('apply', self.job, '--tex', self.source, '--accept-clean'),0)

    def test_collect_without_prepared_job_fails(self):
        self.assertNotEqual(self.call('collect', self.root/'absent'),0)

    def test_ambiguous_apply_does_not_guess_nearest(self):
        self.ask()
        self.source.write_text(self.source.read_text().replace(self.text,self.text+'\n\n'+self.text))
        self.assertEqual(self.call('apply', self.job, '--tex', self.source, '--accept-clean'),0)
        output=(self.job/'polish/source.polished.tex').read_text()
        self.assertNotIn('an improved',output)

    def test_semantic_edit_not_auto_applied(self):
        self.text='For every nonzero integer $n$, the claimed conclusion follows in the precise form given in this sentence.'
        self.source.write_text('\\begin{document}\n'+self.text+'\n\\end{document}')
        self.job=self.root/'semantic-job'
        self.call('prepare','--tex',self.source,'--out',self.job,'--task','polish','--list',self.root/'none')
        self.ask({'verdict':'revise','revisions':[{'original':self.text,'revised':self.text.replace('nonzero ','')}],'note_zh':'条件变化'})
        self.call('apply',self.job,'--tex',self.source,'--accept-clean')
        self.assertIn('nonzero',(self.job/'polish/source.polished.tex').read_text())

    @unittest.skipUnless(__import__('shutil').which('pdflatex'),'pdflatex unavailable')
    def test_single_page_compilation_succeeds(self):
        ok, message=nt.compile_check(self.source.read_text())
        self.assertTrue(ok,message)

    def test_compiler_timeout_is_reported_as_failure(self):
        import subprocess
        with patch.object(nt.shutil,'which',return_value='/fake/pdflatex'),patch.object(nt.subprocess,'run',side_effect=subprocess.TimeoutExpired('pdflatex',900)):
            ok,message=nt.compile_check(self.source.read_text())
        self.assertFalse(ok)



    def test_partial_formula_edit_is_rejected_in_context(self):
        block='The formula is $x$.'
        self.assertEqual(nt.polish_checks({'original':'x','revised':'y'},block)[0],'rejected')

    def test_partial_macro_name_edit_is_rejected_in_context(self):
        block=r'The \emph{long phrase} is retained.'
        self.assertEqual(nt.polish_checks({'original':'emph','revised':'textbf'},block)[0],'rejected')

    def test_extra_brace_in_partial_group_is_rejected(self):
        block=r'\emph{This original sentence.} More.'
        self.assertEqual(nt.polish_checks({'original':'original sentence.}','revised':'updated sentence.}}'},block)[0],'rejected')

    def test_removing_space_cannot_join_neighboring_command(self):
        block=r'\LaTeX gives this explanatory sentence.'
        self.assertEqual(nt.polish_checks({'original':' gives this explanatory sentence.','revised':'gives this explanatory sentence.'},block)[0],'rejected')


class TriageLocationTests(unittest.TestCase):
    def test_repeated_quote_uses_named_unit(self):
        tex = r'\begin{document}'+'\n'+r'\begin{definition}\label{def:1.1.1} Here in particular is the first shared phrase.\end{definition}'+'\n'+r'\begin{theorem}\label{thm:6.9.1} Here in particular is the intended shared phrase.\end{theorem}'+'\n'+r'\end{document}'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'old.tex').write_text(tex)
            import csv
            with (p/'input.csv').open('w', newline='') as f:
                fields=['Claude分类','Claude核实','起行','止行','引文','序号','任务','严重度','类型','理由','单元']
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow(dict(zip(fields,['待看:显式性/边界','','3','3','in particular','4595','test','LOW','boundary','Review this phrase','thm:6.9.1'])))
            nt.prepare_triage(nt.Doc(tex), p/'input.csv', p/'old.tex', p)
            row=nt.read_jsonl(p/'triage/requests.jsonl')[0]
            self.assertEqual(row['meta']['unit_now'], 'thm:6.9.1')
            self.assertIn('intended shared phrase', row['meta']['material'])
            self.assertNotIn('first shared phrase', row['meta']['material'])



    def test_quote_missing_in_named_unit_is_not_assumed_rewritten_elsewhere(self):
        tex = r"\begin{document}"+'\n'+r"\begin{definition}\label{def:1.1.1} The set $\mathbb{Z}^+$ appears here.\end{definition}"+'\n'+r"\begin{definition}\label{def:6.2.1} For $m \in \mathbb{Z}^+$ the stated condition applies.\end{definition}"+'\n'+r"\end{document}"
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'old.tex').write_text(tex)
            import csv
            fields=['Claude分类','Claude核实','起行','止行','引文','序号','任务','严重度','类型','理由','单元']
            with (p/'input.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow(dict(zip(fields,['待看:显式性/边界','','3','3',r'$\mathbb{Z}^+$','361','test','LOW','boundary','Review domain','def:6.2.1'])))
            nt.prepare_triage(nt.Doc(tex),p/'input.csv',p/'old.tex',p)
            rows=nt.read_jsonl(p/'triage/requests.jsonl')
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['meta']['unit_now'],'def:6.2.1')


if __name__ == '__main__': unittest.main()
