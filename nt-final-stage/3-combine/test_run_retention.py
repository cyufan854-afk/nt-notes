"""run_retention.py: 27B 的基线固定是主文件夹的 baseline.tex，路径按 nt-final-stage 的目录结构。"""
import hashlib
from pathlib import Path
import tempfile
import unittest

import run_retention as rr
from test_retention import DOC

BASE = DOC
BRANCH2 = DOC.replace('Every prime is odd', 'Every prime $p>2$ is odd')
MUSE_BEFORE = DOC
MUSE_AFTER = DOC.replace('two even numbers', 'two even integers')


class Layout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.snap = self.root / '3-combine' / 'snapshots'
        self.snap.mkdir(parents=True)
        (self.snap / rr.MUSE_BEFORE).write_text(MUSE_BEFORE)
        (self.snap / rr.MUSE_AFTER).write_text(MUSE_AFTER)
        (self.root / 'baseline.tex').write_text(BASE)
        (self.root / 'branch1.tex').write_text(MUSE_AFTER)
        self.sha = hashlib.sha256(BASE.encode()).hexdigest()
        self.out = self.root / '3-combine' / 'retention'

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, **kw):
        return rr.plan(root=self.root, snapshots=self.snap, out=self.out, expected_sha=self.sha, **kw)

    def test_27b_base_is_always_baseline_tex(self):
        (self.root / 'branch2.tex').write_text(BRANCH2)
        (self.root / 'final.tex').write_text(BRANCH2)
        args, notes = self.plan()
        i = args.index('27B')
        self.assertEqual(args[i + 1], str(self.root / 'baseline.tex'))
        self.assertEqual(args[i + 2], str(self.root / 'branch2.tex'))
        self.assertEqual(args[args.index('--final') + 1], str(self.root / 'final.tex'))
        self.assertNotIn('muse-before', args[i + 1])
        self.assertEqual(notes, [])

    def test_missing_baseline_stops_instead_of_substituting(self):
        (self.root / 'branch2.tex').write_text(BRANCH2)
        (self.root / 'baseline.tex').unlink()
        with self.assertRaisesRegex(rr.SetupError, 'baseline'):
            self.plan()

    def test_changed_baseline_is_refused(self):
        (self.root / 'branch2.tex').write_text(BRANCH2)
        (self.root / 'baseline.tex').write_text(BASE + '% edited\n')
        with self.assertRaisesRegex(rr.SetupError, 'SHA-256'):
            self.plan()

    def test_pinned_hash_is_the_real_baseline(self):
        real = Path(__file__).resolve().parent.parent / 'baseline.tex'
        if real.exists():
            self.assertEqual(rr.sha256(real), rr.BASELINE_SHA256)

    def test_demo_without_final_or_branch2(self):
        args, notes = self.plan()
        self.assertEqual(args[args.index('--final') + 1], str(self.root / 'branch1.tex'))
        self.assertNotIn('27B', args)
        self.assertEqual(len(notes), 2)

    def test_stage_snapshots_split_the_27b_changes(self):
        stages = self.root / '2-branch2' / 'stages'
        stages.mkdir(parents=True)
        one = BASE.replace('two even numbers', 'two even integers')
        (stages / '1-polish.tex').write_text(one)
        (stages / '2-triage.tex').write_text(one.replace('Every prime is odd', 'Every prime $p>2$ is odd'))
        (stages / '3-refs.tex').write_text((stages / '2-triage.tex').read_text())
        (self.root / 'branch2.tex').write_text((stages / '3-refs.tex').read_text())
        args, notes = self.plan()
        sources = [args[i + 1] for i, a in enumerate(args) if a == '--source']
        self.assertEqual(sources, ['27B', '27B·润色', '27B·初筛', '27B·引用核查', 'Muse Wonder'])
        i = args.index('27B·初筛')
        self.assertEqual(args[i + 1:i + 3], [str(stages / '1-polish.tex'), str(stages / '2-triage.tex')])
        self.assertEqual(notes, ['【演示】没找到 final.tex（第 3 步的最终稿），先用 branch1.tex 当最终稿。'])
        (self.root / 'branch2.tex').write_text(one)
        self.assertTrue(any('阶段稿之后又改过' in n for n in self.plan()[1]))

    def test_end_to_end_report(self):
        import retention
        (self.root / 'branch2.tex').write_text(BRANCH2)
        (self.root / 'final.tex').write_text(BRANCH2.replace('two even numbers', 'two even integers'))
        args, _ = self.plan()
        self.assertEqual(retention.main(args), 0)
        report = Path(str(self.out) + '.md').read_text(encoding='utf-8')
        self.assertIn('| 27B | 1 | 1 (100.0%)', report)
        self.assertIn('| Muse Wonder | 1 | 1 (100.0%)', report)
        self.assertIn('### thm:1.1', report)          # per-unit detail


if __name__ == '__main__':
    unittest.main()
