import unittest
from retention import analyse, unit_index, unit_of

DOC = r'''\documentclass{article}
\begin{document}
\section{Divisibility}
\begin{theorem}\label{thm:1.1}
	Every prime is odd and every square is nonnegative.
\end{theorem}
\begin{proof}
	Trivial by inspection of small cases.
\end{proof}
\begin{theorem}\label{thm:1.2}
	The sum of two even numbers is even.
\end{theorem}
\end{document}
'''


def status(before, after, final):
    return [r['status'] for r in analyse('S', before, after, final, 2)]


class Outcomes(unittest.TestCase):
    after = DOC.replace('Every prime is odd', 'Every prime $p>2$ is odd')

    def test_kept(self):
        final = self.after.replace('two even numbers', 'two even integers')  # unrelated later edit
        self.assertEqual(status(DOC, self.after, final), ['kept'])

    def test_reverted(self):
        self.assertEqual(status(DOC, self.after, DOC), ['reverted'])

    def test_rewritten(self):
        final = DOC.replace('Every prime is odd', 'Every prime other than $2$ is odd')
        self.assertEqual(status(DOC, self.after, final), ['rewritten'])

    def test_insertion_and_deletion_hunks(self):
        ins = DOC.replace('small cases.', 'small cases and induction.')
        self.assertEqual(status(DOC, ins, ins), ['kept'])
        self.assertEqual(status(DOC, ins, DOC), ['reverted'])
        dele = DOC.replace('by inspection of small cases', 'by inspection')
        self.assertEqual(status(DOC, dele, dele), ['kept'])
        self.assertEqual(status(DOC, dele, DOC), ['reverted'])
        self.assertEqual(status(DOC, dele, DOC.replace('by inspection of small cases', 'by inspection and luck')), ['rewritten'])

    def test_rewrapping_is_not_a_change(self):
        wrapped = DOC.replace('Every prime is odd and every', 'Every prime is odd\n\tand every')
        self.assertEqual(status(DOC, wrapped, DOC), [])
        self.assertEqual(status(DOC, self.after, self.after.replace('odd and every', 'odd\n\tand every')), ['kept'])

    def test_kept_means_the_changed_text_itself_is_intact(self):
        # Later additions next to the hunk do not undo it.
        final = self.after.replace('$p>2$', '$p>2$ (that is, $p$ odd)')
        self.assertEqual(status(DOC, self.after, final), ['kept'])
        final = DOC.replace('Every prime is odd', 'Every prime $p$ with $p>2$ is odd')
        self.assertEqual(status(DOC, self.after, final), ['kept'])
        # Changing the hunk's own text is a rewrite.
        final = DOC.replace('Every prime is odd', 'Every prime $p\\ge3$ is odd')
        self.assertEqual(status(DOC, self.after, final), ['rewritten'])
        # Text inserted inside a multi-word hunk breaks it.
        after = DOC.replace('small cases', 'every residue class modulo four')
        final = DOC.replace('small cases', 'every residue class, say, modulo four')
        self.assertEqual(status(DOC, after, final), ['rewritten'])

    def test_units(self):
        rows = analyse('S', DOC, self.after.replace('two even numbers', 'two even integers'), DOC, 2)
        self.assertEqual([r['unit'] for r in rows], ['thm:1.1', 'thm:1.2'])
        units = unit_index(DOC)
        self.assertEqual(unit_of(units, DOC.index('Trivial')), 'thm:1.1')
        self.assertEqual(unit_of(units, 5), 'preamble')


if __name__ == '__main__':
    unittest.main()
