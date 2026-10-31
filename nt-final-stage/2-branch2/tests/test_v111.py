import contextlib
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nt27b as nt


class IndexedDocumentTests(unittest.TestCase):
    def setUp(self):
        self.tex = ('\\begin{document}\n前言\n\\subsection{Before}\n'
                    '\\section{One}\n\\begin{theorem}A\\end{theorem}\n'
                    '\\subsection{Part}\n\\begin{proof}B\\end{proof}\n'
                    '\\section{Two}\n\\end{document}\n')
        self.doc = nt.Doc(self.tex)

    def test_indexed_lines_match_string_count_at_all_offsets(self):
        for pos in range(-len(self.tex) - 2, len(self.tex) + 3):
            self.assertEqual(self.doc.line_of(pos), nt.line_of(self.tex, pos), pos)

    def test_environment_boundaries_match_linear_lookup(self):
        for pos in range(-1, len(self.tex) + 2):
            expected = next((e for e in self.doc.envs
                             if e['start'] <= pos < e['end']), None)
            self.assertEqual(self.doc.env_at(pos), expected, pos)

    def test_headings_match_linear_lookup_at_all_offsets(self):
        for pos in range(-1, len(self.tex) + 2):
            sec = sub = ''
            for start, kind, title in self.doc.heads:
                if start > pos:
                    break
                if kind == 'section':
                    sec, sub = title, ''
                else:
                    sub = title
            self.assertEqual(self.doc.heading_at(pos), (sec, sub), pos)

    def test_version_option(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as result:
            nt.main(['--version'])
        self.assertEqual(result.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), 'nt27b 1.1.1')
