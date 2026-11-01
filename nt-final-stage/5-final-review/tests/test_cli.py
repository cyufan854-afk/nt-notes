import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name) / 'state'
    def tearDown(self):
        self.tmp.cleanup()
    def cli(self, *args, code=0):
        p = subprocess.run([sys.executable, '-m', 'coop', '--workspace', str(self.ws), *args], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, code, p.stdout + p.stderr)
        return json.loads(p.stdout)
    def init(self):
        self.cli('init', '--demo')
    def test_complete_and_resume_without_repeating_calls(self):
        self.init()
        job = self.cli('run', '证明素数相关命题', '--tag', 'math')
        self.assertEqual(job['state'], 'completed')
        self.assertEqual(job['calls'], 5)
        again = self.cli('resume', job['id'])
        self.assertEqual(again['calls'], 5)
    def test_budget_pause_then_resume(self):
        self.init()
        job = self.cli('run', '分析问题', '--max-calls', '3', code=2)
        self.assertEqual(job['state'], 'paused')
        done = self.cli('resume', job['id'], '--add-calls', '3')
        self.assertEqual(done['state'], 'completed')
        self.assertEqual(done['calls'], 5)
    def test_unapproved_memory_is_not_retrieved(self):
        self.init()
        a = self.cli('run', '证明素数命题', '--tag', 'math')
        self.assertEqual(self.cli('memory', 'search', '--tag', 'math'), [])
        self.cli('memory', 'approve', a['id'])
        hits = self.cli('memory', 'search', '--tag', 'math')
        self.assertEqual(hits[0]['id'], a['id'])
        self.assertEqual(self.cli('memory', 'search', '--tag', 'math', '--project', 'other'), [])
    def test_missing_file_does_not_start_run(self):
        self.init()
        self.cli('run', 'test', '--file', '/does/not/exist', code=1)
        self.assertEqual(self.cli('status'), [])

if __name__ == '__main__':
    unittest.main()

class BatchCLI(unittest.TestCase):
    setUp = Integration.setUp
    tearDown = Integration.tearDown
    cli = Integration.cli
    init = Integration.init
    def test_batch_commands(self):
        self.init()
        path=Path(self.tmp.name)/'findings.jsonl'
        path.write_text(json.dumps({'location':'L1','excerpt':r'$\nu$','concern':'条件'})+'\n')
        result=self.cli('batch','run',str(path),'--max-calls-per-finding','3',code=2)
        self.assertEqual(result['items'][0]['calls'],3)
        done=self.cli('batch','resume',result['id'],'--add-calls-per-finding','3',code=2)
        self.assertEqual(done['items'][0]['calls'],5)
        self.assertEqual(self.cli('batch','status',result['id'],code=2)['items'][0]['finding_status'],'待人工')
