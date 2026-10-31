import json
import os
import shlex
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import unittest


RUNNER = Path(__file__).resolve().parents[1] / "gpu" / "run_gpu.sh"


class GpuRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / "package"
        (self.package / "gpu").mkdir(parents=True)
        shutil.copy2(RUNNER, self.package / "gpu" / "run_gpu.sh")
        self.job = self.root / "volume" / "tiny job"
        self.job.mkdir(parents=True)
        (self.job / "manifest.json").write_text("{}", encoding="utf-8")
        (self.job / "partial.json").write_text('{"saved": true}', encoding="utf-8")
        self.events_path = self.root / "events.jsonl"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.write_stub()
        for command in ("python3", "vllm", "curl", "tar", "runpodctl"):
            (self.bin / command).symlink_to(self.bin / "fake-tool")
        for command in ("dirname", "basename", "date", "seq", "sleep", "tail", "mv", "rm"):
            source = shutil.which(command)
            self.assertIsNotNone(source, command)
            (self.bin / command).symlink_to(source)

    def write_stub(self):
        stub = self.bin / "fake-tool"
        stub.write_text(
            "#!/bin/sh\n'''exec' " + shlex.quote(sys.executable) + " \"$0\" \"$@\" # '''\n" + textwrap.dedent(r'''
                import json
                import os
                from pathlib import Path
                import signal
                import sys
                import tarfile
                import time

                name = Path(sys.argv[0]).name
                args = sys.argv[1:]
                scenario = os.environ["FAKE_SCENARIO"]
                event = {"tool": name, "args": args}
                with open(os.environ["FAKE_EVENTS"], "a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event) + "\n")

                if name == "vllm":
                    if scenario == "vllm_exited":
                        Path(os.environ["FAKE_EVENTS"] + ".vllm-pid").write_text(str(os.getpid()), encoding="utf-8")
                    while True:
                        time.sleep(0.05)
                elif name == "python3":
                    if len(args) < 3 or args[0] != "nt27b.py":
                        sys.exit(90)
                    action = args[1]
                    if action == "ask":
                        sample = "--sample" in args
                        retry = "--retry-errors" in args
                        state = Path(args[2]) / "attempts.jsonl"
                        with state.open("a", encoding="utf-8") as stream:
                            stream.write(json.dumps({"sample": sample, "retry": retry}) + "\n")
                        if scenario == "stale_unsampled":
                            responses = Path(args[2]) / "polish" / "responses.jsonl"
                            rows = [json.loads(line) for line in responses.read_text(encoding="utf-8").splitlines()]
                            selected = rows[:3] if sample else rows
                            for row in selected:
                                row["config"] = "current"
                            responses.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
                        if scenario == "smoke_error" and sample:
                            sys.exit(7)
                        if scenario == "full_error_retry_ok" and not sample and not retry:
                            sys.exit(8)
                        if scenario == "retry_error" and retry:
                            sys.exit(9)
                    elif action == "verify":
                        sample = "--sample" in args
                        if scenario == "stale_unsampled":
                            rows = [json.loads(line) for line in (Path(args[2]) / "polish" / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
                            selected = rows[:3] if sample else rows
                            if any(row["config"] != "current" for row in selected):
                                sys.exit(3)
                        if scenario == "smoke_invalid" and sample:
                            sys.exit(10)
                        if scenario in ("full_invalid", "retry_error") and not sample:
                            sys.exit(11)
                    elif action == "collect":
                        if scenario == "stale_unsampled":
                            rows = [json.loads(line) for line in (Path(args[2]) / "polish" / "responses.jsonl").read_text(encoding="utf-8").splitlines()]
                            if any(row["config"] != "current" for row in rows):
                                sys.exit(3)
                    else:
                        sys.exit(91)
                elif name == "curl":
                    if scenario == "vllm_exited":
                        pid_path = Path(os.environ["FAKE_EVENTS"] + ".vllm-pid")
                        pid = None
                        for _ in range(1000):
                            try:
                                pid = int(pid_path.read_text(encoding="utf-8"))
                                break
                            except (FileNotFoundError, ValueError):
                                time.sleep(0.005)
                        if pid is None:
                            sys.exit(94)
                        try:
                            os.kill(pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        for _ in range(1000):
                            try:
                                os.kill(pid, 0)
                            except ProcessLookupError:
                                break
                            time.sleep(0.005)
                elif name == "tar":
                    if scenario == "archive_error":
                        sys.exit(12)
                    archive = Path(args[args.index("-czf") + 1]) if "-czf" in args else Path(args[1])
                    base = Path(args[args.index("-C") + 1]) if "-C" in args else Path.cwd()
                    target = args[-1]
                    with tarfile.open(archive, "w:gz") as output:
                        output.add(base / target, arcname=Path(target).name)
                elif name == "runpodctl":
                    archives = list(Path(os.environ["JOB"]).parent.glob("results-*.tgz"))
                    if len(archives) != 1:
                        sys.exit(92)
                    with tarfile.open(archives[0], "r:gz") as archive:
                        if not any(member.name.endswith("/partial.json") for member in archive):
                            sys.exit(93)
            '''),
            encoding="utf-8",
        )
        stub.chmod(0o755)

    def run_runner(self, scenario="success", auto_stop=False, model="fake-model", model_revision=None):
        env = os.environ.copy()
        env.pop("MODEL_REVISION", None)
        env.update({
            "PATH": str(self.bin),
            "MODEL": model,
            "JOB": str(self.job),
            "AUTO_STOP": "1" if auto_stop else "0",
            "RUNPOD_POD_ID": "fake-pod",
            "FAKE_SCENARIO": scenario,
            "FAKE_EVENTS": str(self.events_path),
        })
        if model_revision is not None:
            env["MODEL_REVISION"] = model_revision
        return subprocess.run(
            ["/bin/bash", str(self.package / "gpu" / "run_gpu.sh")],
            cwd=str(self.root), env=env, text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        )

    def events(self, tool=None):
        if not self.events_path.exists():
            return []
        events = [json.loads(line) for line in self.events_path.read_text(encoding="utf-8").splitlines()]
        return [event for event in events if tool is None or event["tool"] == tool]

    def cli_calls(self):
        return [event["args"][1:] for event in self.events("python3")]

    def assert_archive(self):
        archives = list(self.job.parent.glob("results-*.tgz"))
        self.assertEqual(len(archives), 1, "Archive must be beside JOB on its result volume")
        self.assertEqual(len(self.events("tar")), 1, "Cleanup must archive once")
        with tarfile.open(archives[0], "r:gz") as archive:
            self.assertIn("tiny job/partial.json", archive.getnames())

    def test_smoke_request_failure_stops_before_full_run_and_archives(self):
        result = self.run_runner("smoke_error")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([call[0] for call in self.cli_calls()], ["ask"])
        self.assert_archive()
        self.assertEqual(self.events("runpodctl"), [])

    def test_smoke_verification_failure_stops_before_full_run(self):
        result = self.run_runner("smoke_invalid")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.cli_calls()
        self.assertEqual([call[0] for call in calls], ["ask", "verify"])
        self.assertEqual(calls[-1], ["verify", str(self.job), "--task", "all", "--sample", "3"])
        self.assert_archive()

    def test_full_refresh_replaces_unsampled_stale_responses_after_verified_smoke(self):
        responses = self.job / "polish" / "responses.jsonl"
        responses.parent.mkdir()
        responses.write_text("\n".join(
            json.dumps({"id": index, "config": "old"}) for index in range(5)
        ), encoding="utf-8")
        result = self.run_runner("stale_unsampled", model_revision="new-weights")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.cli_calls()
        self.assertEqual([call[0] for call in calls], ["ask", "verify", "collect", "ask", "ask", "collect", "verify"])
        self.assertEqual(calls[1], ["verify", str(self.job), "--task", "all", "--sample", "3"])
        self.assertEqual(calls[-1], ["verify", str(self.job), "--task", "all"])
        self.assertEqual([json.loads(line)["config"] for line in responses.read_text(encoding="utf-8").splitlines()], ["current"] * 5)
        self.assert_archive()

    def test_model_reference_and_explicit_revision_are_forwarded_to_every_ask(self):
        cases = [
            ("weights-one", None, "11:weights-one,11:weights-one,"),
            ("weights-two", None, "11:weights-two,11:weights-two,"),
            ("weights-two", "weights-two-commit-b", "11:weights-two,20:weights-two-commit-b,"),
        ]
        for model, revision, expected in cases:
            with self.subTest(model=model, revision=revision):
                result = self.run_runner(model=model, model_revision=revision)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                asks = [call for call in self.cli_calls() if call[0] == "ask"][-3:]
                self.assertEqual(len(asks), 3)
                for call in asks:
                    self.assertIn("--model-revision", call)
                    self.assertEqual(call[call.index("--model-revision") + 1], expected)

    def test_resuming_existing_answers_requires_explicit_model_revision(self):
        responses = self.job / "polish" / "responses.jsonl"
        responses.parent.mkdir()
        responses.write_text('{"id": "old-answer"}\n', encoding="utf-8")
        result = self.run_runner()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self.cli_calls(), [])
        self.assertEqual(self.events("vllm"), [])
        self.assertIn("MODEL_REVISION", result.stderr)
        self.assert_archive()

    def test_same_checkpoint_revision_binds_distinct_model_references(self):
        identities = []
        for model in ("weights-one", "weights-two"):
            result = self.run_runner(model=model, model_revision="checkpoint-a")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            asks = [call for call in self.cli_calls() if call[0] == "ask"][-3:]
            identities.append(asks[0][asks[0].index("--model-revision") + 1])
        self.assertNotEqual(identities[0], identities[1])

    def test_full_request_failure_reaches_retry_and_verified_completion(self):
        result = self.run_runner("full_error_retry_ok")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.cli_calls()
        self.assertEqual([call[0] for call in calls], ["ask", "verify", "collect", "ask", "ask", "collect", "verify"])
        self.assertIn("--retry-errors", calls[4])
        self.assertEqual(calls[-1], ["verify", str(self.job), "--task", "all"])
        self.assert_archive()
        self.assertEqual(self.events("runpodctl"), [])

    def test_success_verifies_smoke_and_all_results_before_opt_in_stop(self):
        result = self.run_runner(auto_stop=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.cli_calls()
        self.assertEqual([call[0] for call in calls], ["ask", "verify", "collect", "ask", "ask", "collect", "verify"])
        self.assertEqual(calls[1], ["verify", str(self.job), "--task", "all", "--sample", "3"])
        self.assertEqual(calls[-1], ["verify", str(self.job), "--task", "all"])
        self.assert_archive()
        self.assertEqual([event["args"] for event in self.events("runpodctl")], [["stop", "pod", "fake-pod"]])
        tools = [event["tool"] for event in self.events()]
        self.assertLess(tools.index("tar"), tools.index("runpodctl"))

    def test_full_verification_failure_archives_without_reporting_success(self):
        result = self.run_runner("full_invalid")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.cli_calls()[-1], ["verify", str(self.job), "--task", "all"])
        self.assert_archive()
        self.assertEqual(self.events("runpodctl"), [])

    def test_retry_request_failure_still_collects_and_verifies(self):
        result = self.run_runner("retry_error")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([call[0] for call in self.cli_calls()][-3:], ["ask", "collect", "verify"])
        self.assert_archive()

    def test_opt_in_stop_on_exception_happens_once_after_archive(self):
        result = self.run_runner("smoke_error", auto_stop=True)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assert_archive()
        self.assertEqual([event["args"] for event in self.events("runpodctl")], [["stop", "pod", "fake-pod"]])

    def test_readiness_curl_success_still_requires_live_vllm(self):
        result = self.run_runner("vllm_exited")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(self.cli_calls(), [])
        curl_events = self.events("curl")
        self.assertTrue(curl_events)
        for event in curl_events:
            args = event["args"]
            self.assertEqual(args[args.index("--connect-timeout") + 1], "2")
            self.assertEqual(args[args.index("--max-time") + 1], "5")
        self.assert_archive()

    def test_missing_python3_is_rejected_before_vllm_starts(self):
        (self.bin / "python3").unlink()
        result = self.run_runner()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("python3", result.stdout + result.stderr)
        self.assertEqual(self.events("vllm"), [])
        self.assertEqual(self.cli_calls(), [])
        self.assert_archive()

    def test_auto_stop_without_runpodctl_fails_after_successful_archive(self):
        (self.bin / "runpodctl").unlink()
        result = self.run_runner(auto_stop=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assert_archive()
        self.assertEqual(self.events("runpodctl"), [])
        self.assertIn("AUTO_STOP=1", result.stderr)

    def test_auto_stop_without_runpodctl_preserves_prior_failure(self):
        (self.bin / "runpodctl").unlink()
        result = self.run_runner("smoke_error", auto_stop=True)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual([call[0] for call in self.cli_calls()], ["ask"])
        self.assert_archive()
        self.assertEqual(self.events("runpodctl"), [])

    def test_archive_failure_preserves_results_and_prevents_opt_in_stop(self):
        result = self.run_runner("archive_error", auto_stop=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.job / "partial.json").is_file())
        self.assertEqual(self.events("runpodctl"), [])
        self.assertEqual(len(self.events("tar")), 1)


if __name__ == "__main__":
    unittest.main()
