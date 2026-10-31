import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from coop.core import Store, default_config, dumps
from coop import findings
from coop.protocol import encode
from coop.workflow import finding_status


def branch(assessment='confirmed', status='not_requested', accepted=False):
    return {'answer': {'meta': {'assessment':assessment}},
            'review': {'meta': {'verdict':'approve','assessment':assessment,'evidence_accepted':accepted,'evidence_ids':['actual']}},
            'execution': {'id':'actual','status':status,'returncode':0,'stdout':'observed=1.89','cleanup_ok':True}}


class FindingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.store=Store(self.root/'state')
        (self.store.root/'config.json').write_text(dumps(default_config(True)))
        self.file=self.root/'findings.jsonl'
    def tearDown(self): self.tmp.cleanup()
    def write(self,rows):
        self.file.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows),encoding='utf-8')
    def test_aliases_and_formula_preservation(self):
        self.write([{'位置':'定理 1','原文片段':r'$\nu_p(n)$','疑点':'边界条件'}])
        rows=findings.load(self.file)
        self.assertEqual(rows[0]['excerpt'],r'$\nu_p(n)$')
    def test_invalid_last_line_starts_no_jobs(self):
        self.file.write_text('{"location":"L","excerpt":"x","concern":"y"}\nnot json')
        with self.assertRaises(ValueError): findings.create(self.store,self.file,[],['math'],'notes',3)
        self.assertEqual(self.store.status(),[])
    def test_per_finding_budget_pause_and_resume(self):
        self.write([{'id':'A','location':'L1','excerpt':'a','concern':'b'},{'id':'B','location':'L2','excerpt':'c','concern':'d'}])
        batch=findings.create(self.store,self.file,[],['math'],'notes',3)
        first=findings.execute(self.store,batch)
        self.assertEqual(len(first['items']),2)
        self.assertTrue(all(x['calls']==3 for x in first['items']))
        ids=[x['job_id'] for x in first['items']]
        second=findings.execute(self.store,batch,add_calls=3)
        self.assertEqual([x['job_id'] for x in second['items']],ids)
        self.assertTrue(all(x['calls']==5 for x in second['items']))
        self.assertTrue(all(x['finding_status']=='待人工' for x in second['items']))
        self.assertEqual(findings.execute(self.store,batch),second)
    def test_no_evidence_from_model_claim_only(self):
        self.assertEqual(finding_status([branch(),branch()]),'确认有问题')
        self.assertEqual(finding_status([branch(accepted=True),branch()]),'确认有问题')
        self.assertEqual(finding_status([branch(status='completed',accepted=True),branch()]),'有计算证据')
        self.assertEqual(finding_status([branch(status='timeout',accepted=True),branch()]),'待人工')
        self.assertEqual(finding_status([branch('fixed'),branch('fixed')]),'已修复')
        self.assertEqual(finding_status([branch('false_positive'),branch('false_positive')]),'误报')
        self.assertEqual(finding_status([branch('confirmed'),branch('false_positive')]),'待人工')
    def test_single_finding_context_not_whole_list(self):
        self.write([{'location':'L1','excerpt':'UNIQUE_A','concern':'x'},{'location':'L2','excerpt':'UNIQUE_B','concern':'y'}])
        batch=findings.create(self.store,self.file,[],['math'],'notes')
        summary=findings.status(self.store,batch)
        req=json.loads(self.store.get(summary['items'][0]['job_id'])['request'])
        self.assertEqual(req['finding']['excerpt'],'UNIQUE_A')
        self.assertNotIn('UNIQUE_B',dumps(req))
