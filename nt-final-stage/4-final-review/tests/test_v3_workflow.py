import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from coop.core import Store, default_config, dumps
from coop.protocol import encode
from coop.providers import invoke


class V3WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.store=Store(self.tmp.name)
        self.cfg=default_config(True)
        (self.store.root/'config.json').write_text(dumps(self.cfg))
    def tearDown(self): self.tmp.cleanup()
    def job(self): return self.store.create('检查数学',[],['math'],'notes')
    def test_only_rejected_branch_is_rewritten(self):
        seen=[]
        def fake(spec,prompt,stage,folder,timeout):
            seen.append(stage)
            if stage=='review0_1':
                return encode({'kind':'review','verdict':'revise','issues':[{'id':'B1','severity':'blocking'}]},'修订 B')
            return invoke(spec,prompt,stage,folder,timeout)
        job=self.job()
        with patch('coop.core.invoke',side_effect=fake): result=self.store.execute(job)
        self.assertEqual(result['state'],'completed')
        self.assertIn('revision1_1',seen)
        self.assertNotIn('revision1_0',seen)
        self.assertEqual(result['calls'],7)
        self.assertEqual(self.store.execute(job)['calls'],7)
    def test_notes_do_not_pause(self):
        def fake(spec,prompt,stage,folder,timeout):
            if stage.startswith('review'):
                return encode({'kind':'review','verdict':'approve','issues':['小意见']},'仅调整措辞')
            return invoke(spec,prompt,stage,folder,timeout)
        job=self.job()
        with patch('coop.core.invoke',side_effect=fake): result=self.store.execute(job)
        self.assertEqual(result['state'],'completed')
        self.assertIn('approve_with_notes',self.store.get(job)['result'])
    def test_role_timeout_and_codex_default(self):
        self.assertGreaterEqual(self.cfg['timeouts']['analysis0'],900)
        self.cfg['timeouts']['analysis1']=977
        (self.store.root/'config.json').write_text(dumps(self.cfg))
        seen={}
        def fake(spec,prompt,stage,folder,timeout):
            seen[stage]=timeout
            return invoke(spec,prompt,stage,folder,timeout)
        with patch('coop.core.invoke',side_effect=fake): self.store.execute(self.job())
        self.assertGreaterEqual(seen['analysis0'],900)
        self.assertEqual(seen['analysis1'],977)
    def test_latex_survives_report_and_resume(self):
        body=r'$\nu_p(n)$; $\frac{a}{b}$; $\theta$; $a \equiv b$'
        def fake(spec,prompt,stage,folder,timeout):
            if stage.startswith('analysis'):
                return encode({'kind':'analysis','assessment':'unknown'},body)
            return invoke(spec,prompt,stage,folder,timeout)
        job=self.job()
        with patch('coop.core.invoke',side_effect=fake): self.store.execute(job)
        self.assertIn(body,self.store.get(job)['result'])
        self.store.execute(job)
        self.assertIn(body,self.store.get(job)['result'])

class FeedbackTests(unittest.TestCase):
    setUp = V3WorkflowTests.setUp
    tearDown = V3WorkflowTests.tearDown
    job = V3WorkflowTests.job
    def make_fake_docker(self,path):
        import sys
        path.write_text('#!'+sys.executable+'\nimport sys\nif sys.argv[1]=="image":\n print("sha256:fixture"); raise SystemExit(0)\nif sys.argv[1]=="rm":\n raise SystemExit(0)\nsys.stdin.read()\nprint("actual_residual=1.89")\n')
        path.chmod(0o755)
    def responder(self,spec,prompt,stage,folder,timeout):
        if stage.startswith(('analysis','revision')):
            return encode({'kind':'analysis','assessment':'confirmed','check':True},'模型自述：residual=0（不可采信）\n```python coop-check\nprint("residual=0")\n```')
        if stage.startswith('review'):
            context=json.loads(prompt.split('\nCONTEXT:\n',1)[1])
            record=context['execution']
            self.assertEqual(record['stdout'],'actual_residual=1.89\n')
            self.assertEqual(record['returncode'],0)
            return encode({'kind':'review','verdict':'approve','assessment':'confirmed','issues':[],
                           'evidence_accepted':True,'evidence_ids':[record['id']]},'以调度器记录为准：1.89。')
        return invoke(spec,prompt,stage,folder,timeout)
    def test_real_record_reaches_review_and_status(self):
        exe=self.store.root/'fake-docker'; self.make_fake_docker(exe)
        self.cfg['execution']['executable']=str(exe)
        (self.store.root/'config.json').write_text(dumps(self.cfg))
        job=self.job()
        with patch('coop.core.invoke',side_effect=self.responder): result=self.store.execute(job)
        self.assertEqual(result['finding_status'],'有计算证据')
        with self.store.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM executions WHERE job=?',(job,)).fetchone()[0],2)
        report=self.store.get(job)['result']
        self.assertIn('actual_residual=1.89',report)
        self.assertEqual(self.store.execute(job)['calls'],5)
    def test_missing_runtime_resume_reuses_paid_analysis(self):
        exe=self.store.root/'later-docker'
        self.cfg['execution']['executable']=str(exe)
        (self.store.root/'config.json').write_text(dumps(self.cfg))
        job=self.job()
        with patch('coop.core.invoke',side_effect=self.responder):
            first=self.store.execute(job)
            self.assertEqual(first['state'],'paused')
            self.assertEqual(first['finding_status'],'待人工')
            self.assertEqual(first['calls'],3)
            self.make_fake_docker(exe)
            second=self.store.execute(job)
        self.assertEqual(second['finding_status'],'有计算证据')
        self.assertEqual(second['calls'],5)

class MalformedCheckTests(unittest.TestCase):
    setUp=V3WorkflowTests.setUp
    tearDown=V3WorkflowTests.tearDown
    job=V3WorkflowTests.job
    def test_bad_check_fence_is_retryable(self):
        def fake(spec,prompt,stage,folder,timeout):
            if stage=='analysis0':
                return encode({'kind':'analysis','check':True},'missing code block')
            return invoke(spec,prompt,stage,folder,timeout)
        job=self.job()
        with patch('coop.core.invoke',side_effect=fake): first=self.store.execute(job)
        self.assertEqual(first['state'],'paused')
        done=self.store.execute(job)
        self.assertEqual(done['state'],'completed')
        self.assertGreater(done['calls'],first['calls'])
