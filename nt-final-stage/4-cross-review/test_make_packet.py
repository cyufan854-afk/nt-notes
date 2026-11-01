"""make_packet.py: the full file and the compact parts for the cross review."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / '3-combine'))
import make_packet as mp  # noqa: E402
from test_merge_check import BASE, BRANCH1, BRANCH2  # noqa: E402


class Packet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / '3-combine').mkdir()
        self.final = BRANCH1.replace('Count lattice points under the hyperbola.', 'Count the lattice points under the hyperbola $xy=n$ for every $n\\ge1$.')
        for name, text in (('baseline.tex', BASE), ('branch1.tex', BRANCH1), ('branch2.tex', BRANCH2), ('final.tex', self.final)):
            (self.root / name).write_text(text, encoding='utf-8')
        self.out = self.root / 'out'
        self.out.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_file_has_the_prompt_and_four_wrapped_manuscripts(self):
        (self.root / '3-combine' / 'merge-log.md').write_text('- 单元 thm:5.7.1 · 类型：冲突处理 · …', encoding='utf-8')
        written, risky = mp.build(self.root, self.out)
        full = (self.out / 'cross-review-full.md').read_text(encoding='utf-8')
        self.assertTrue(full.startswith('# 交叉审查'))
        for name in ('baseline.tex', 'branch1.tex', 'branch2.tex', 'final.tex', 'merge-log.md'):
            self.assertIn(f'===== 文件：{name}', full)
            self.assertIn(f'===== 文件结束：{name} =====', full)
        self.assertIn(f'{len(self.final.splitlines())} 行', full)
        self.assertIn('最后一行「\\end{document}」', full)
        self.assertLess(full.index('文件：baseline.tex'), full.index('文件：final.tex'))

    def test_compact_part_holds_only_risky_units(self):
        written, risky = mp.build(self.root, self.out)
        self.assertEqual(risky, 1)
        compact = (self.out / 'cross-review-compact.md').read_text(encoding='utf-8')
        self.assertIn('##### 单元 thm:5.7.1', compact)
        self.assertIn('for every $n\\ge1$', compact)                           # final's text
        self.assertIn('--- 差异：baseline → branch2 ---', compact)
        self.assertIn('--- 差异：branch1 → final ---', compact)
        self.assertNotIn('##### 单元 def:5.7.2', compact)                     # took branch1 cleanly: listed only
        self.assertIn('def:5.7.2', compact.split('===== 不在材料包里的单元 =====')[1])

    def test_split_into_parts(self):
        many_final = self.final.replace('\\end{document}', ''.join(
            f'\\begin{{theorem}}\\label{{thm:9.9.{i}}} Claim {i} with enough words to be a unit of its own here.\\end{{theorem}}\n'
            for i in range(1, 4)) + '\\end{document}')
        many_b1 = BRANCH1.replace('\\end{document}', ''.join(
            f'\\begin{{theorem}}\\label{{thm:9.9.{i}}} Claim {i} with enough words to be a unit of its own.\\end{{theorem}}\n'
            for i in range(1, 4)) + '\\end{document}')
        (self.root / 'final.tex').write_text(many_final, encoding='utf-8')
        (self.root / 'branch1.tex').write_text(many_b1, encoding='utf-8')
        written, risky = mp.build(self.root, self.out, max_chars=1)
        parts = sorted(self.out.glob('cross-review-compact-*.md'))
        self.assertEqual(len(parts), risky)
        self.assertGreater(risky, 1)
        for n, part in enumerate(parts, 1):
            text = part.read_text(encoding='utf-8')
            self.assertTrue(text.startswith('# 交叉审查'))
            self.assertIn(f'材料包第 {n}/{len(parts)} 部分', text)

    def test_missing_final_is_refused(self):
        (self.root / 'final.tex').unlink()
        self.assertEqual(mp.main(['--root', str(self.root), '--out', str(self.out)]), 2)


if __name__ == '__main__':
    unittest.main()
