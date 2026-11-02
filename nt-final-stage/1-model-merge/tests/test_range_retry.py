"""qmerge_legacy.Engine._range (2026-11-02 patch): transient HTTP answers of the Hub or its CDN are retried."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tm2 import HAVE_TORCH, embedded_sources  # noqa: E402

try:
    import requests  # noqa: F401
    import huggingface_hub  # noqa: F401
    HAVE_HTTP = True
except ImportError:
    HAVE_HTTP = False


def load_legacy():
    if 'qmerge_legacy' not in sys.modules:
        directory = Path(tempfile.mkdtemp(prefix='legacy-'))
        (directory / 'qmerge_legacy.py').write_text(embedded_sources()['qmerge_legacy'], encoding='utf-8')
        spec = importlib.util.spec_from_file_location('qmerge_legacy', directory / 'qmerge_legacy.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules['qmerge_legacy'] = module
        spec.loader.exec_module(module)
    return sys.modules['qmerge_legacy']


class FakeRaw:
    def __init__(self, data):
        self.data = data

    def read(self, n, decode_content=False):
        return self.data[:n]


class FakeResponse:
    def __init__(self, status, data=b'', start=0, end=0, total=0):
        self.status_code = status
        self.headers = {'Content-Range': f'bytes {start}-{end}/{total}', 'Content-Length': str(len(data))} if status == 206 else {}
        self.raw = FakeRaw(data)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def get(self, url, headers=None, stream=True, timeout=None):
        self.calls += 1
        return self.answers.pop(0)


@unittest.skipUnless(HAVE_TORCH and HAVE_HTTP, 'needs torch, requests and huggingface_hub')
class RangeRetry(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy()
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = self.legacy.Engine(api=None, token='', work=self.tmp.name)
        self.engine.pins['o/r'] = 'a' * 40
        self.engine._sizes['o/r'] = {'model.safetensors': 100}
        self.sleeps = []
        self.old_sleep = self.legacy.time.sleep
        self.legacy.time.sleep = self.sleeps.append

    def tearDown(self):
        self.legacy.time.sleep = self.old_sleep
        self.tmp.cleanup()

    def use(self, answers):
        session = FakeSession(answers)
        self.engine._local.session = session
        return session

    def test_cdn_499_and_5xx_are_retried(self):
        ok = FakeResponse(206, b'0123456789', 10, 19, 100)
        session = self.use([FakeResponse(499), FakeResponse(503), FakeResponse(408), ok])
        self.assertEqual(self.engine._range('o/r', 'model.safetensors', 10, 19), b'0123456789')
        self.assertEqual(session.calls, 4)
        self.assertEqual(self.sleeps, [1, 2, 4])

    def test_gives_up_after_the_retries(self):
        self.use([FakeResponse(499)] * (self.legacy.RANGE_RETRIES + 1))
        with self.assertRaises(OSError):
            self.engine._range('o/r', 'model.safetensors', 0, 9)
        self.assertEqual(len(self.sleeps), self.legacy.RANGE_RETRIES)
        self.assertEqual(self.legacy.RANGE_RETRIES, 6)

    def test_a_full_file_answer_is_still_refused_at_once(self):
        session = self.use([FakeResponse(200), FakeResponse(404)])
        with self.assertRaisesRegex(ValueError, 'ignored the byte range \\(200\\)'):
            self.engine._range('o/r', 'model.safetensors', 0, 9)
        self.assertEqual(session.calls, 1)


if __name__ == '__main__':
    unittest.main()
