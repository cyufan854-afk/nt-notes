"""merge_check.py: unit plan, label map across an inserted definition, and the checks on final.tex."""
import unittest

import merge_check as mc

BASE = r'''\documentclass{article}
\newtheorem{theorem}{Theorem}[subsection]
\newtheorem{definition}{Definition}[subsection]
\begin{document}
\section{Orders}
\begin{definition}[average order]\label{def:5.7.1}
	An arithmetic function $g$ is an average order of $f$ if the partial sums are asymptotic, where $u\sim v$ means $u/v\to1$.
\end{definition}
\begin{theorem}\label{thm:5.7.1}
	The divisor function has average order $\ln n$ by Definition~\ref{def:5.7.1}.
\end{theorem}
\begin{proof}
	Count lattice points under the hyperbola.
\end{proof}
\end{document}
'''
# branch1 splits the notation off into a new definition before it: average order becomes def:5.7.2
BRANCH1 = BASE.replace(r'''\begin{definition}[average order]\label{def:5.7.1}
	An arithmetic function $g$ is an average order of $f$ if the partial sums are asymptotic, where $u\sim v$ means $u/v\to1$.''',
                       r'''\begin{definition}[asymptotic notation]\label{def:5.7.1}
	We write $u\sim v$ if $u/v\to1$ as $x\to\infty$, where $v$ is nonzero for large $x$.
\end{definition}
\begin{definition}[average order]\label{def:5.7.2}
	An arithmetic function $g$ is an average order of $f$ if the partial sums are asymptotic.''').replace(
    r'Definition~\ref{def:5.7.1}', r'Definition~\ref{def:5.7.2}')
BRANCH2 = BASE.replace('Count lattice points under the hyperbola.', 'Count the lattice points under the hyperbola $xy=n$.')


class PlanTests(unittest.TestCase):
    def test_label_map_follows_the_title_not_the_position(self):
        self.assertEqual(mc.label_map(BASE, BRANCH1)['def:5.7.1'], 'def:5.7.2')
        self.assertEqual(mc.label_map(BASE, BRANCH1)['thm:5.7.1'], 'thm:5.7.1')
        self.assertEqual({k: v for k, v in mc.label_map(BASE, BRANCH2).items() if k != v}, {})

    def test_units_and_sides(self):
        rows, maps = mc.plan(BASE, BRANCH1, BRANCH2)
        by = {r['unit']: r for r in rows}
        self.assertEqual(maps['renamed_in_branch1'], {'def:5.7.1': 'def:5.7.2'})
        self.assertIsNone(by['def:5.7.1']['baseline'])            # new in branch1
        self.assertEqual(by['def:5.7.2']['baseline'], 'def:5.7.1')
        self.assertTrue(by['thm:5.7.1']['branch1'])              # the \ref was renamed
        self.assertTrue(by['thm:5.7.1']['branch2'])              # the proof was polished
        self.assertFalse(by['def:5.7.2']['branch2'])


class VerifyTests(unittest.TestCase):
    def test_branch1_itself_passes(self):
        self.assertEqual(mc.verify(BRANCH1, BRANCH1), [])

    def test_good_merge_passes(self):
        final = BRANCH1.replace('Count lattice points under the hyperbola.', 'Count the lattice points under the hyperbola $xy=n$.')
        self.assertEqual(mc.verify(final, BRANCH1), [])

    def test_lost_environment_label_and_stale_ref_are_caught(self):
        problems = mc.verify(BASE, BRANCH1)
        self.assertTrue(any('label' in p for p in problems))
        self.assertTrue(any('带编号的环境' in p for p in problems))
        stale = BRANCH1.replace(r'Definition~\ref{def:5.7.2}', r'Definition~\ref{def:5.7.9}')
        self.assertTrue(any('不存在的 label' in p for p in mc.verify(stale, BRANCH1)))

    def test_conflict_markers_and_unbalanced_envs(self):
        bad = BRANCH1.replace('Count lattice', '<<<<<<< ours\nCount lattice', 1)
        self.assertTrue(any('冲突标记' in p for p in mc.verify(bad, BRANCH1)))
        bad = BRANCH1.replace('\\end{proof}', '', 1)
        self.assertTrue(any('proof' in p for p in mc.verify(bad, BRANCH1)))


if __name__ == '__main__':
    unittest.main()
