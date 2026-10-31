"""Stage layout (nt-final-stage): the manuscript comes from the stage's baseline.tex (hash-checked, no second copy in data/), and apply can
publish the verified result as the stage's branch2.tex without ever overwriting it silently."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nt27b as nt
import qwen_polish as qp
import test_pipeline

PACKAGE = Path(__file__).resolve().parents[1]


def quiet(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = nt.main([str(x) for x in args])
    return code, out.getvalue(), err.getvalue()


class BaselineSource(unittest.TestCase):
    """PipelineTests' tiny book and fake model (borrowed, so its own tests do not run twice); setUp already prepared a
    job from an explicit --tex."""
    setUp = test_pipeline.PipelineTests.setUp
    call = test_pipeline.PipelineTests.call
    respond = test_pipeline.PipelineTests.respond

    def prepare_default(self, sha=None):
        job = self.root / 'job-default'
        with patch.object(nt, 'BASELINE', self.tex), patch.object(nt, 'BASELINE_SHA256', sha or qp.sha(self.tex.read_text())):
            result = quiet('prepare', '--out', job, '--csv', self.csv, '--pre-fix-tex', self.tex, '--list', self.root / 'none')
        return job, result

    def test_default_manuscript_is_the_stage_baseline(self):
        job, (code, _, err) = self.prepare_default()
        self.assertEqual(code, 0, err)
        manifest = json.loads((job / 'manifest.json').read_text())
        self.assertEqual(Path(manifest['tex']), self.tex)
        self.assertEqual(manifest['tool_version'], nt.VERSION)
        self.assertNotIn('不是 baseline.tex', err)

    def test_changed_baseline_is_refused(self):
        job, (code, _, err) = self.prepare_default(sha='0' * 64)
        self.assertEqual(code, 2)
        self.assertIn('SHA-256', err)
        self.assertFalse((job / 'manifest.json').exists())

    def test_missing_baseline_is_refused(self):
        with patch.object(nt, 'BASELINE', self.root / 'absent.tex'):
            code, _, err = quiet('prepare', '--out', self.root / 'j2', '--task', 'polish', '--list', self.root / 'none')
        self.assertEqual(code, 2)
        self.assertIn('baseline.tex', err)

    def test_other_manuscript_only_warns(self):
        code, _, err = quiet('prepare', '--tex', self.tex, '--out', self.root / 'j3', '--task', 'polish', '--list', self.root / 'none')
        self.assertEqual(code, 0)
        self.assertIn('不是 baseline.tex', err)

    def test_apply_publishes_branch2_once(self):
        with patch.object(qp, 'http_json', side_effect=self.respond):
            self.assertEqual(self.call('ask', self.job, '--model', 'test', '--concurrency', '4'), 0)
        self.assertEqual(self.call('collect', self.job), 0)
        target = self.root / 'stage' / 'branch2.tex'
        self.assertEqual(self.call('apply', self.job, '--tex', self.tex, '--accept-clean', '--out', target), 0)
        published = target.read_text()
        self.assertEqual(published, (self.job / 'polish' / 'book.polished.tex').read_text())
        self.assertEqual(published.count('an improved explanatory'), 5)
        target.write_text(published + '% triage fix made by the reviewer\n')
        self.assertEqual(self.call('apply', self.job, '--tex', self.tex, '--accept-clean', '--out', target), 5)
        self.assertIn('triage fix', target.read_text())
        self.assertEqual(self.call('apply', self.job, '--tex', self.tex, '--accept-clean', '--out', target, '--force'), 0)
        self.assertEqual(target.read_text(), published)


class StageLayout(unittest.TestCase):
    def test_no_second_copy_of_the_baseline(self):
        self.assertFalse((PACKAGE / 'data' / 'nt.tex').exists())

    def test_pinned_hash_matches_the_stage_baseline(self):
        if nt.BASELINE.exists():
            self.assertEqual(qp.sha(nt.BASELINE.read_text(encoding='utf-8')), nt.BASELINE_SHA256)


if __name__ == '__main__':
    unittest.main()
