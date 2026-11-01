import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from coop import execution


class ExecutionTests(unittest.TestCase):
    def test_container_command_enforces_restrictions(self):
        argv = execution.container_command('/usr/bin/docker', 'coop-check-test', execution.defaults())
        for flag, value in [('--network','none'),('--pull','never'),('--user','65534:65534'),('--cap-drop','ALL'),('--pids-limit','32')]:
            self.assertEqual(argv[argv.index(flag)+1], value)
        self.assertIn('--read-only', argv)
        self.assertNotIn('--privileged', argv)
        self.assertNotIn('-v', argv)
        self.assertNotIn('--mount', argv)
        self.assertEqual(argv[-4:], ['python','-I','-u','-'])
    def test_missing_runtime_fails_closed(self):
        with tempfile.TemporaryDirectory() as d, patch('coop.execution.shutil.which', return_value=None):
            out = execution.run_check('raise Exception("must not run")', Path(d), execution.defaults())
        self.assertEqual(out['status'], 'unavailable')
        self.assertEqual(out['stdout'], '')
    def fake_docker(self, root, body):
        exe = root / 'fake-docker'
        exe.write_text('#!' + sys.executable + '\nimport sys,time\n'
                       'if sys.argv[1] == "image":\n print("sha256:fixture"); raise SystemExit(0)\n'
                       'if sys.argv[1] == "rm":\n raise SystemExit(0)\n' + body)
        exe.chmod(0o755)
        return str(exe)
    def test_actual_stdout_not_a_model_summary(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            exe=self.fake_docker(root, 'sys.stdin.read()\nprint("observed=1.89")\n')
            cfg=execution.defaults(); cfg['executable']=exe
            out=execution.run_check('print("claimed=0")',root/'record',cfg)
            self.assertEqual(out['stdout'],'observed=1.89\n')
            self.assertEqual(out['status'],'completed')
            self.assertEqual(out['returncode'],0)
            self.assertEqual((root/'record'/'stdout.txt').read_text(),out['stdout'])
    def test_timeout_is_recorded_and_cleaned_up(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            cfg=execution.defaults(); cfg.update(executable=self.fake_docker(root,'sys.stdin.read()\ntime.sleep(20)\n'),timeout=0.1)
            out=execution.run_check('pass',root/'record',cfg)
            self.assertEqual(out['status'],'timeout')
            self.assertTrue(out['cleanup_ok'])
    def test_output_is_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            cfg=execution.defaults(); cfg.update(executable=self.fake_docker(root,'sys.stdin.read()\nprint("x"*100000)\n'),max_output_bytes=1000)
            out=execution.run_check('pass',root/'record',cfg)
            self.assertEqual(out['status'],'output_limit')
            self.assertLessEqual(len(out['stdout'].encode())+len(out['stderr'].encode()),1000)


@unittest.skipUnless(os.environ.get('COOP_DOCKER_INTEGRATION') == '1', 'set COOP_DOCKER_INTEGRATION=1 with local Docker + pre-pulled image')
class RealDockerTests(unittest.TestCase):
    def test_network_denied_and_host_files_absent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); secret=root/'host-only.txt'; secret.write_text('not mounted')
            code='import socket, pathlib\nassert not pathlib.Path('+repr(str(secret))+').exists()\ns=socket.socket()\ns.settimeout(1)\ntry:\n s.connect(("1.1.1.1",443))\nexcept OSError:\n print("NETWORK_BLOCKED; HOST_FILE_ABSENT")\nelse:\n raise RuntimeError("network unexpectedly available")\n'
            out=execution.run_check(code,root/'record',execution.defaults())
            self.assertEqual(out['status'],'completed',out)
            self.assertIn('NETWORK_BLOCKED',out['stdout'])
