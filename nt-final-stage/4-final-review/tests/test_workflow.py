import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from coop.core import Store, default_config, dumps
from coop.providers import invoke
from coop.protocol import encode


class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.cfg = default_config(True)
        (self.store.root / 'config.json').write_text(dumps(self.cfg))
    def tearDown(self):
        self.tmp.cleanup()
    def create(self, **kwargs):
        return self.store.create('检查数学笔记', [], ['math'], 'project', **kwargs)
    def test_revision_is_bounded_and_not_promoted(self):
        real = invoke
        def revise(spec, prompt, stage, folder, timeout):
            if stage.startswith('review'):
                return encode({'kind':'review','verdict':'revise','issues':[{'id':'B1','severity':'blocking'}]}, '缺少条件，还需修订')
            return real(spec, prompt, stage, folder, timeout)
        job = self.create()
        with patch('coop.core.invoke', side_effect=revise):
            state = self.store.execute(job)
        self.assertEqual(state['state'], 'needs_review')
        self.assertEqual(state['calls'], 9)
        self.assertIn('缺少条件', self.store.get(job)['result'])
    def test_invalid_json_pauses_then_retries_only_failed_stage(self):
        job = self.create()
        real = invoke
        def broken(spec, prompt, stage, folder, timeout):
            if stage.startswith('review'):
                return 'not json'
            return real(spec, prompt, stage, folder, timeout)
        with patch('coop.core.invoke', side_effect=broken):
            state = self.store.execute(job)
        self.assertEqual(state['state'], 'paused')
        self.assertEqual(state['calls'], 4)
        self.assertEqual(self.store.execute(job)['calls'], 6)
        self.assertTrue(list((self.store.root / job).glob('*/raw.txt')))
    def test_input_and_config_are_frozen(self):
        file = self.store.root / 'note.md'
        file.write_text('original')
        job = self.store.create('check', [file], ['math'], 'project', 1)
        self.store.execute(job)
        file.write_text('changed')
        (self.store.root / 'config.json').write_text('{}')
        self.assertEqual(self.store.execute(job, 5)['state'], 'completed')
        row = self.store.get(job)
        self.assertEqual(json.loads(row['request'])['files'][0]['content'], 'original')
    def test_memory_separates_demo_and_live(self):
        job = self.create()
        self.store.execute(job)
        with self.store.db() as db:
            db.execute('UPDATE jobs SET approved=1 WHERE id=?', (job,))
        self.assertEqual(self.store.memories(['math'], 'project', False), [])
        self.assertEqual(len(self.store.memories(['math'], 'project', True)), 1)
    def test_same_job_is_locked(self):
        import fcntl
        job = self.create()
        with (self.store.root / job / 'lock').open('a') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, '已经'):
                self.store.execute(job)
    def test_command_timeout_and_failure(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            invoke({'kind': 'command', 'argv': [sys.executable, '-c', 'import time; time.sleep(10)']}, 'test', 'plan', self.store.root, 0.1)
        with self.assertRaisesRegex(RuntimeError, '退出码 7'):
            invoke({'kind': 'command', 'argv': [sys.executable, '-c', 'raise SystemExit(7)']}, 'test', 'plan', self.store.root, 1)
    def test_concurrent_budget_cannot_overspend(self):
        job = self.create(budget=2)
        result = self.store.execute(job)
        self.assertEqual(result['state'], 'paused')
        self.assertEqual(result['calls'], 2)
        self.assertEqual(self.store.execute(job, 3)['calls'], 5)


if __name__ == '__main__':
    unittest.main()
