"""branch2.py: the whole of step 2 in stages (polish -> triage -> refs -> ../branch2.tex), on a tiny book."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
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


class Driver(unittest.TestCase):
    setUp_book = test_pipeline.PipelineTests.setUp
    respond = test_pipeline.PipelineTests.respond
    call = test_pipeline.PipelineTests.call

    def setUp(self):
        self.setUp_book()                              # tiny book at self.tex, findings CSV, a job prepared at self.job
        self.stage_root = self.root / 'nt-final-stage'
        (self.stage_root / '2-branch2').mkdir(parents=True)
        (self.stage_root / 'baseline.tex').write_bytes(self.tex.read_bytes())
        self.job = self.stage_root / '2-branch2' / 'job-27b'
        code, _ = quiet(nt.main, ['prepare', '--tex', str(self.stage_root / 'baseline.tex'), '--out', str(self.job), '--csv', str(self.csv),
                                  '--pre-fix-tex', str(self.tex), '--list', str(self.root / 'none')])
        self.assertEqual(code, 0)

    def b2(self, *args):
        return quiet(b2.main, ['--root', str(self.stage_root), *args])

    def stage(self, name):
        return self.stage_root / '2-branch2' / 'stages' / name

    def test_whole_flow(self):
        code, out = self.b2('status')
        self.assertIn('[answers]', out)
        with patch.object(qp, 'http_json', side_effect=self.respond):
            self.assertEqual(quiet(nt.main, ['ask', str(self.job), '--model', 'test', '--concurrency', '4'])[0], 0)
        self.assertEqual(self.b2('next')[0], 0)                                  # collect
        self.assertIn('[polish]', self.b2('status')[1])
        self.assertEqual(self.b2('next')[0], 2)                                  # nothing ticked
        code, out = self.b2('next', '--accept-clean')
        self.assertEqual(code, 0, out)
        self.assertEqual(self.stage('1-polish.tex').read_text().count('an improved explanatory'), 5)
        self.assertEqual(self.b2('next')[0], 0)                                  # prepare the triage stage
        task = self.stage('2-triage-task.md').read_text(encoding='utf-8')
        self.assertIn(str(self.job / 'triage' / 'for-claude.md'), task)
        self.assertIn('--done', task)
        self.assertEqual(self.b2('next')[0], 2)                                  # waiting for the agent
        triage = self.stage('2-triage.tex')
        triage.write_text(triage.read_text().replace('the conclusion holds.', 'the conclusion holds for every $n>0$.', 1))
        self.stage('2-triage-log.md').write_text('- #1 · thm:1.1.1 · 改了 · 补上范围\n', encoding='utf-8')
        self.assertEqual(self.b2('next', '--done')[0], 0)
        self.assertEqual(self.b2('next')[0], 0)                                  # prepare the refs stage
        refs = self.stage('3-refs.tex')
        good = refs.read_text()
        refs.write_text(good.replace('\\label{thm:1.1.2}', '\\label{thm:odd}'))
        code, out = self.b2('next', '--done')
        self.assertEqual(code, 3)
        self.assertIn('label', out)
        refs.write_text(good)
        self.assertEqual(self.b2('next', '--done')[0], 0)
        code, out = self.b2('next')                                              # finalize
        self.assertEqual(code, 0, out)
        branch2 = self.stage_root / 'branch2.tex'
        self.assertEqual(branch2.read_text(), good)
        provenance = self.stage('provenance.md').read_text(encoding='utf-8')
        for title in ('润色', '初筛修补', '引用核查修补'):
            self.assertIn(title, provenance)
        self.assertIn('2-triage-log.md', provenance)
        self.assertIn('[done]', self.b2('status')[1])
        self.assertEqual((self.stage_root / 'baseline.tex').read_bytes(), self.tex.read_bytes())   # never modified

    def test_import_accepts_only_the_job_directory(self):
        good = self.root / 'good.tgz'
        payload = self.root / 'payload' / 'job-27b' / 'polish'
        payload.mkdir(parents=True)
        (payload / 'responses.jsonl').write_text('{}\n')
        with tarfile.open(good, 'w:gz') as tar:
            tar.add(self.root / 'payload' / 'job-27b', arcname='job-27b')
        self.assertEqual(self.b2('import', str(good))[0], 0)
        self.assertTrue((self.job / 'polish' / 'responses.jsonl').exists())
        bad = self.root / 'bad.tgz'
        evil = self.root / 'evil.txt'
        evil.write_text('x')
        with tarfile.open(bad, 'w:gz') as tar:
            tar.add(evil, arcname='../evil.txt')
        with self.assertRaises(SystemExit):
            self.b2('import', str(bad))

    def test_structure_check(self):
        base = (self.stage_root / 'baseline.tex').read_text()
        self.assertEqual(b2.structure_problems(base, base), [])
        self.assertTrue(b2.structure_problems(base.replace('\\end{theorem}', '', 1), base))
        self.assertTrue(b2.structure_problems(base + '\n<<<<<<< ours\n', base))


if __name__ == '__main__':
    unittest.main()
