import contextlib
import csv
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


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tex = self.root/'book.tex'
        self.original = 'This is the original explanatory sentence with enough words for this full paragraph to be included.'
        body = '\n'.join(r'\begin{theorem}\label{thm:1.1.%d} '%i + self.original + r' For $n>0$, the conclusion holds.\end{theorem}' for i in range(1,6))
        self.tex.write_text(r'\documentclass{article}'+'\n'+r'\begin{document}'+'\n'+body+'\n'+r'By Theorem~\ref{thm:1.1.1}, the assertion holds in the case under discussion.'+'\n'+r'\end{document}',encoding='utf-8')
        self.job=self.root/'job'
        self.csv=self.root/'findings.csv'
        fields=['Claude分类','Claude核实','起行','止行','引文','序号','任务','严重度','类型','理由','单元']
        with self.csv.open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            writer.writerow(dict(zip(fields,['待看:显式性/边界','','3','3',self.original,'1','test','LOW','boundary','Check this condition','thm:1.1.1'])))
        self.assertEqual(self.call('prepare','--tex',self.tex,'--out',self.job,'--csv',self.csv,'--pre-fix-tex',self.tex,'--list',self.root/'none'),0)

    def call(self,*args):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            return nt.main([str(x) for x in args])

    def respond(self,url,payload,key,timeout):
        system=payload['messages'][0]['content']
        if '[task: polish]' in system:
            answer={'verdict':'revise','revisions':[{'original':self.original,'revised':self.original.replace('the original','an improved')}],'note_zh':'冠词调整'}
        elif '[task: triage]' in system:
            answer={'verdict':'cannot_decide','evidence':'','patch_original':'','patch_revised':'','note_zh':'模拟回答，交给人工复核'}
        else:
            answer={'verdict':'mismatch','cited_fact':'','missing_hypotheses':[],'note_zh':'模拟回答，交给人工复核'}
        return {'model':payload['model'],'choices':[{'message':{'content':json.dumps(answer)},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':50}}

    def test_prepare_ask_verify_collect_apply_roundtrip(self):
        before=self.tex.read_bytes()
        with patch.object(qp,'http_json',side_effect=self.respond):
            self.assertEqual(self.call('ask',self.job,'--model','test','--concurrency','4'),0)
        self.assertEqual(self.call('verify',self.job),0)
        self.assertEqual(self.call('collect',self.job),0)
        summary=json.loads((self.job/'summary.json').read_text())
        self.assertEqual(set(summary),{'polish','triage','refs'})
        for stats in summary.values():
            self.assertEqual(stats['errors'],0)
            self.assertEqual(stats['pending'],0)
            self.assertEqual(stats['stale'],0)
        self.assertEqual(self.call('apply',self.job,'--tex',self.tex,'--accept-clean'),0)
        result=(self.job/'polish/book.polished.tex').read_text()
        self.assertEqual(result.count('an improved explanatory'),5)
        self.assertEqual(self.tex.read_bytes(),before)
        self.assertIn('cannot_decide',(self.job/'triage/for-claude.md').read_text())
        self.assertIn('mismatch',(self.job/'refs/for-claude.md').read_text())

    def test_changed_endpoint_sample_then_full_refresh(self):
        with patch.object(qp,'http_json',side_effect=self.respond):
            self.assertEqual(self.call('ask',self.job,'--task','polish','--model','test'),0)
            self.assertEqual(self.call('ask',self.job,'--task','polish','--model','test','--base-url','http://changed.test/v1','--sample','3'),0)
            self.assertEqual(self.call('verify',self.job,'--task','polish','--sample','3'),0)
            self.assertNotEqual(self.call('verify',self.job,'--task','polish'),0)
            self.assertEqual(self.call('ask',self.job,'--task','polish','--model','test','--base-url','http://changed.test/v1'),0)
        self.assertEqual(self.call('verify',self.job,'--task','polish'),0)


    def test_mock_citation_with_formula_only_target_still_has_evidence(self):
        from tools import mock_server
        target=r'\begin{theorem}\label{thm:x}$x=x$.\end{theorem}'
        user='### Cited statement (thm:x)\n'+target+'\n### End'
        answer=mock_server.refs(user,3)
        self.assertTrue(answer['cited_fact'])
        self.assertIn(answer['cited_fact'],target)
        self.assertEqual(nt.validate_refs(answer)['verdict'],'supports')


if __name__ == '__main__': unittest.main()
