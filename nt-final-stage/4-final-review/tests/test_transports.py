import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from coop.core import default_config
from coop.providers import invoke, reset_cancel

ROOT = Path(__file__).resolve().parents[1]


class TransportTests(unittest.TestCase):
    def test_output_limit(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError, '限制'):
                invoke({'kind': 'command', 'max_output_bytes': 1000, 'argv': [sys.executable, '-c', 'print("x" * 10000)']}, '', 'plan', Path(d), 2)
    def test_cli_envelopes(self):
        for name in ('claude', 'gemini', 'kimi', 'codex'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                bin_dir = root / 'bin'; bin_dir.mkdir()
                exe = bin_dir / name
                answer = json.dumps({'answer': 'fixture'})
                script = '#!' + sys.executable + '\nimport json,sys\nfrom pathlib import Path\n'
                if name == 'codex':
                    script += 'Path(sys.argv[sys.argv.index("-o")+1]).write_text(' + repr(answer) + ')\n'
                else:
                    raw = json.dumps({'result' if name == 'claude' else 'response': answer}) if name != 'kimi' else json.dumps({'role': 'assistant', 'content': answer})
                    script += 'print(' + repr(raw) + ')\n'
                exe.write_text(script); exe.chmod(0o755)
                with patch.dict(os.environ, {'PATH': str(bin_dir) + os.pathsep + os.environ['PATH']}):
                    out = invoke({'kind': name, 'allow_auto_tools': True}, 'test', 'analysis0', root, 3)
                self.assertEqual(json.loads(out)['answer'], 'fixture')
    def test_sigint_pauses_parallel_processes_promptly(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            cfg = default_config(True)
            worker = ws / 'slow.py'
            worker.write_text('import time\ntime.sleep(30)\n')
            for name in cfg['roles']['analysts']:
                cfg['providers'][name] = {'kind': 'command', 'argv': [sys.executable, str(worker)]}
            (ws / 'config.json').write_text(json.dumps(cfg))
            proc = subprocess.Popen([sys.executable, '-m', 'coop', '--workspace', str(ws), 'run', 'test'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 5
                while len(list(ws.glob('*/000*-analysis*/worker.log'))) < 2 and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertEqual(len(list(ws.glob('*/000*-analysis*/worker.log'))), 2)
                start = time.monotonic()
                proc.send_signal(signal.SIGINT)
                out, err = proc.communicate(timeout=3)
                self.assertLess(time.monotonic() - start, 3)
                self.assertEqual(json.loads(out)['state'], 'paused', err)
                self.assertEqual(proc.returncode, 2)
            finally:
                if proc.poll() is None:
                    proc.kill(); proc.wait()


if __name__ == '__main__':
    unittest.main()

class FrameInstructionTests(unittest.TestCase):
    def test_kimi_and_gemini_defer_to_task_response_format(self):
        for name in ('gemini','kimi'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root=Path(d); exe=root/name
                script='#!'+sys.executable+'\nimport sys,json\nfrom pathlib import Path\n'
                if name=='gemini':
                    script+='assert "Return only the requested JSON" not in " ".join(sys.argv)\n'
                    script+='print(json.dumps({"response":"framed body"}))\n'
                else:
                    script+='p=Path(sys.argv[sys.argv.index("--agent-file")+1])\nassert "Return only the requested JSON" not in p.read_text()\nprint(json.dumps({"role":"assistant","content":"framed body"}))\n'
                exe.write_text(script); exe.chmod(0o755)
                out=invoke({'kind':name,'executable':str(exe)},'test','analysis0',root,3)
                self.assertEqual(out,'framed body')
