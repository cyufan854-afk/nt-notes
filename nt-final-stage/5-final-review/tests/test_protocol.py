import unittest
from coop import protocol


class ProtocolTests(unittest.TestCase):
    def test_latex_body_is_lossless(self):
        for body in [r'$\nu_p(n)$', r'$\frac{a}{b}$', r'$\theta$', r'$a \equiv b$', '\n  leading\ntrailing  \n']:
            with self.subTest(body=body):
                raw = protocol.encode({'kind': 'analysis', 'assessment': 'unknown'}, body)
                result = protocol.parse(raw, 'analysis')
                self.assertEqual(result['body'], body)
    def test_approve_with_notes_is_normalized(self):
        raw = protocol.encode({'kind': 'review', 'verdict': 'approve', 'issues': [{'id': 'N1', 'severity': 'note'}]}, '措辞建议')
        self.assertEqual(protocol.parse(raw, 'review')['meta']['verdict'], 'approve_with_notes')
    def test_legacy_advisory_strings_do_not_pause(self):
        raw = protocol.encode({'kind': 'review', 'verdict': 'approve', 'issues': ['小意见']}, '详见正文')
        self.assertEqual(protocol.parse(raw, 'review')['meta']['verdict'], 'approve_with_notes')
    def test_explicit_blockers_cannot_be_approved(self):
        raw = protocol.encode({'kind': 'review', 'verdict': 'approve', 'issues': [{'id': 'B1', 'severity': 'blocking'}]}, '逻辑有缺口')
        self.assertEqual(protocol.parse(raw, 'review')['meta']['verdict'], 'revise')
    def test_legacy_json_body_rejected(self):
        with self.assertRaises(ValueError):
            protocol.parse(r'{"answer":"$\nu$"}', 'analysis')
    def test_control_chars_in_metadata_rejected(self):
        raw = protocol.encode({'kind':'review', 'verdict':'approve', 'issues':[]}, 'text').replace('"issues": []', '"issues": ["$\\nu$"]')
        with self.assertRaises(ValueError):
            protocol.parse(raw, 'review')
    def test_script_extraction_only_explicit_check(self):
        body = '文本\n```python coop-check\nprint(2+2)\n```\n其他文本'
        result = protocol.parse(protocol.encode({'kind':'analysis','check':True},body),'analysis')
        self.assertEqual(protocol.check_script(result), 'print(2+2)\n')
        result['meta']['check'] = False
        self.assertIsNone(protocol.check_script(result))
    def test_missing_script_is_not_ignored(self):
        result = protocol.parse(protocol.encode({'kind':'analysis','check':True},'no script'),'analysis')
        with self.assertRaises(ValueError):
            protocol.check_script(result)
