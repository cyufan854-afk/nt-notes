import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nt27b as nt


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / 'test.tex'
        source.write_text(r'\begin{document} This is a sufficiently long explanatory paragraph about the theorem and its proof with many words for processing.\end{document}')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(nt.main(['prepare', '--tex', str(source), '--out', str(self.root / 'job'), '--task', 'polish']), 0)
        self.job = self.root / 'job'

    def run_cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = nt.main([str(a) for a in args])
        return code, output.getvalue()

    def test_status_pending_and_unprepared(self):
        code, output = self.run_cli('status', self.job, '--json')
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data['polish']['pending'], data['polish']['total'])
        self.assertGreater(data['polish']['pending'], 0)
        self.assertEqual(data['refs']['state'], 'not_prepared')

    def test_status_stale_answers_include_ids_and_reasons(self):
        req = nt.read_jsonl(self.job / 'polish/requests.jsonl')[0]
        nt.write_jsonl(self.job / 'polish/responses.jsonl', [{'id': req['id'], 'answer': {'verdict': 'keep'}}])
        code, output = self.run_cli('status', self.job, '--json', '--details')
        data = json.loads(output)['polish']
        self.assertEqual(code, 0)
        self.assertEqual(data['stale'], 1)
        self.assertEqual(data['issues'][0]['id'], req['id'])
        self.assertTrue(data['issues'][0]['reason'])

    def test_corrupt_jsonl_reports_error(self):
        (self.job / 'polish/requests.jsonl').write_text('{broken')
        code, output = self.run_cli('status', self.job, '--json')
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(output)['polish']['state'], 'invalid')

    def test_status_does_not_repair_damaged_responses(self):
        path = self.job / 'polish/responses.jsonl'
        path.write_bytes(b'{broken')
        code, output = self.run_cli('status', self.job, '--json')
        self.assertEqual(code, 3)
        self.assertEqual(path.read_bytes(), b'{broken')
        self.assertFalse(list(path.parent.glob('*.torn-*')))

    def test_missing_job_fails(self):
        code, output = self.run_cli('status', self.root / 'missing', '--json')
        self.assertEqual(code, 3)

    def test_show_out_of_range_fails(self):
        code, output = self.run_cli('show', self.job, '--index', 999999)
        self.assertEqual(code, 2)
        self.assertNotIn('----- user -----', output)

    def test_estimate_zero_price(self):
        code, output = self.run_cli('estimate', self.job, '--gpu-price', 0)
        self.assertEqual(code, 0)
        self.assertIn('$0.00/小时约 $0.0', output)
