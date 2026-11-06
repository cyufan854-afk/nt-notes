"""run_gpu.sh on RunPod with the step-1 model: Hugging Face cache on the volume, download before vLLM starts, text-only
vLLM with a fallback, online quantization in the cache identity, --max-num-seqs, the vLLM version hint, the GPU memory
hint, and AUTO_STOP refusing to run when the results would sit on the container disk (cleared when a pod stops).

Every outside program is a fake that records its arguments (and the HF_* variables it sees)."""
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
COMMIT = "0708c99c1ed8cd893ce03014adf1d8f0a811ebe4"
REPO = "YFC-112358/Qwen3.8-27B-pi-AuxMix-v1"

STUB = r'''
import json
import os
from pathlib import Path
import sys
import tarfile
import time

name = Path(sys.argv[0]).name
args = sys.argv[1:]
scenario = os.environ.get("FAKE_SCENARIO", "")
events = os.environ["FAKE_EVENTS"]
env = {k: v for k, v in os.environ.items() if k.startswith("HF_")}
with open(events, "a", encoding="utf-8") as stream:
    stream.write(json.dumps({"tool": name, "args": args, "env": env}) + "\n")
ready = Path(events + ".ready")

if name == "vllm":
    text_only = "--limit-mm-per-prompt" in args
    if scenario == "mm_rejected" and text_only:
        print("INFO non-default args: {'limit_mm_per_prompt': {'image': 0, 'video': 0}}")
        print("vllm serve: error: unrecognized arguments: --limit-mm-per-prompt")
        sys.exit(2)
    if scenario == "oom":
        print("INFO non-default args: {'limit_mm_per_prompt': {'image': 0, 'video': 0}}")
        print("torch.OutOfMemoryError: CUDA out of memory.")
        sys.exit(1)
    print("INFO 11-06 12:00:00 [api_server.py:1] vLLM API server version " + os.environ.get("FAKE_VLLM_VERSION", "0.33.0"),
          flush=True)
    ready.write_text("1", encoding="utf-8")
    while True:
        time.sleep(0.05)
elif name == "curl":
    sys.exit(0 if ready.exists() else 7)
elif name in ("hf", "huggingface-cli"):
    if scenario == "download_error":
        print("401 Client Error: Repository Not Found", file=sys.stderr)
        sys.exit(1)
    print("/fake/cache/snapshot")
elif name == "df":
    print("Filesystem 1024-blocks Used Available Capacity Mounted on")
    print("overlay 100 0 %s 0%% %s" % (os.environ.get("FAKE_DF_AVAIL", str(500 * 1048576)),
                                      os.environ.get("FAKE_DF_MOUNT", "/workspace")))
elif name == "nvidia-smi":
    print(os.environ.get("FAKE_GPU", "NVIDIA H100 80GB HBM3, 81559"))
elif name == "tar":
    archive = Path(args[args.index("-czf") + 1])
    base = Path(args[args.index("-C") + 1])
    with tarfile.open(archive, "w:gz") as output:
        output.add(base / args[-1], arcname=args[-1])
elif name == "runpodctl":
    if scenario == "old_stop_syntax_gone" and args[:2] == ["stop", "pod"]:
        sys.exit(1)
# python3 (nt27b.py ask / verify / collect), sleep: succeed
'''


class RunpodTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / "package"
        (self.package / "gpu").mkdir(parents=True)
        shutil.copy2(RUNNER, self.package / "gpu" / "run_gpu.sh")
        self.volume = self.root / "workspace"
        self.volume.mkdir()
        self.job = self.package / "job-27b"
        self.job.mkdir()
        (self.job / "manifest.json").write_text("{}", encoding="utf-8")
        self.events_path = self.root / "events.jsonl"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        stub = self.bin / "fake-tool"
        stub.write_text("#!/bin/sh\n'''exec' " + shlex.quote(sys.executable) + " \"$0\" \"$@\" # '''\n"
                        + textwrap.dedent(STUB), encoding="utf-8")
        stub.chmod(0o755)
        for command in ("python3", "vllm", "curl", "tar", "runpodctl", "hf", "df", "nvidia-smi", "sleep"):
            (self.bin / command).symlink_to(stub)
        for command in ("dirname", "basename", "date", "seq", "tail", "mv", "rm"):
            (self.bin / command).symlink_to(shutil.which(command))

    def without(self, *commands):
        for command in commands:
            (self.bin / command).unlink()

    def run_runner(self, scenario="", **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("HF_", "MODEL", "QUANT", "TEXT_ONLY", "PREFETCH"))}
        env.update({"PATH": str(self.bin), "MODEL": REPO, "MODEL_REVISION": COMMIT, "JOB": "job-27b",
                    "RUNPOD_VOLUME": str(self.volume), "RUNPOD_POD_ID": "pod-1", "AUTO_STOP": "0",
                    "FAKE_SCENARIO": scenario, "FAKE_EVENTS": str(self.events_path)})
        env.update(extra)
        return subprocess.run(["/bin/bash", str(self.package / "gpu" / "run_gpu.sh")], cwd=str(self.root), env=env,
                              text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=20)

    def events(self, tool=None):
        if not self.events_path.exists():
            return []
        rows = [json.loads(line) for line in self.events_path.read_text(encoding="utf-8").splitlines()]
        return [row for row in rows if tool is None or row["tool"] == tool]

    def serve_args(self, index=0):
        return self.events("vllm")[index]["args"]

    def identity(self):
        asks = [e["args"] for e in self.events("python3") if e["args"][1:2] == ["ask"]]
        self.assertTrue(asks)
        return {a[a.index("--model-revision") + 1] for a in asks}

    def archives(self):
        return list(self.package.glob("results-*.tgz"))

    # ------------------------------------------------------------------ download and cache
    def test_hub_model_is_downloaded_at_the_commit_into_the_volume_cache_before_vllm(self):
        result = self.run_runner()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tools = [e["tool"] for e in self.events() if e["tool"] in ("hf", "vllm")]
        self.assertEqual(tools, ["hf", "vllm"])
        download = self.events("hf")[0]
        self.assertEqual(download["args"], ["download", REPO, "--revision", COMMIT])
        cache = str(self.volume / ".cache" / "huggingface" / "hub")
        self.assertEqual(download["env"].get("HF_HUB_CACHE"), cache)
        self.assertEqual(self.events("vllm")[0]["env"].get("HF_HUB_CACHE"), cache)
        self.assertNotIn("HF_HOME", download["env"])          # the login token stays where it was
        self.assertEqual(self.serve_args()[:2], ["serve", REPO])
        self.assertIn("可用 500 GiB", result.stdout)

    def test_an_existing_hf_home_is_left_alone(self):
        home = str(self.root / "hf-home")
        result = self.run_runner(HF_HOME=home)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        env = self.events("hf")[0]["env"]
        self.assertEqual(env.get("HF_HOME"), home)
        self.assertNotIn("HF_HUB_CACHE", env)

    def test_failed_download_stops_before_vllm_and_names_the_token(self):
        result = self.run_runner("download_error")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self.events("vllm"), [])
        self.assertIn("HF_TOKEN", result.stderr)
        self.assertEqual(len(self.archives()), 1)

    def test_no_download_for_a_local_model_or_when_turned_off(self):
        local = self.root / "weights"
        local.mkdir()
        for extra in ({"MODEL": str(local)}, {"PREFETCH": "0"}):
            with self.subTest(extra=extra):
                self.events_path.unlink(missing_ok=True)
                result = self.run_runner(**extra)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.events("hf"), [])
                self.assertEqual(len(self.events("vllm")), 1)

    def test_without_hf_cli_vllm_downloads_itself(self):
        self.without("hf")
        result = self.run_runner()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("没有 hf 命令", result.stderr)
        self.assertEqual(self.serve_args()[self.serve_args().index("--revision") + 1], COMMIT)

    def test_low_disk_space_is_reported(self):
        result = self.run_runner(FAKE_DF_AVAIL=str(20 * 1048576))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("约 54 GB", result.stderr)

    # ------------------------------------------------------------------ vLLM arguments
    def test_default_vllm_arguments_text_only_bf16_and_max_num_seqs(self):
        result = self.run_runner(CONC="48")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        serve = self.serve_args()
        self.assertEqual(serve[serve.index("--limit-mm-per-prompt") + 1], '{"image":0,"video":0}')
        self.assertEqual(json.loads(serve[serve.index("--limit-mm-per-prompt") + 1]), {"image": 0, "video": 0})
        self.assertEqual(serve[serve.index("--max-num-seqs") + 1], "48")
        self.assertEqual(serve[serve.index("--dtype") + 1], "bfloat16")
        self.assertNotIn("--quantization", serve)
        self.assertIn("--enable-prefix-caching", serve)
        # unchanged identity: answers made before this change are still valid
        self.assertEqual(self.identity(), {"%d:%s,%d:%s," % (len(REPO), REPO, len(COMMIT), COMMIT)})

    def test_online_quantization_is_passed_and_enters_the_identity(self):
        result = self.run_runner(QUANTIZATION="fp8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        serve = self.serve_args()
        self.assertEqual(serve[serve.index("--quantization") + 1], "fp8")
        self.assertEqual(self.identity(), {"%d:%s,%d:%s,16:quantization=fp8," % (len(REPO), REPO, len(COMMIT), COMMIT)})

    def test_bad_quantization_value_is_refused(self):
        result = self.run_runner(QUANTIZATION="fp8 --trust-remote-code")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self.events("vllm"), [])

    def test_text_only_rejected_by_vllm_restarts_once_without_it(self):
        result = self.run_runner("mm_rejected")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.events("vllm")), 2)
        self.assertIn("--limit-mm-per-prompt", self.serve_args(0))
        self.assertNotIn("--limit-mm-per-prompt", self.serve_args(1))
        self.assertTrue((self.package / "vllm-text-only.log").is_file())
        self.assertTrue(any(e["args"][1:2] == ["ask"] for e in self.events("python3")))

    def test_other_startup_failures_are_not_retried(self):
        result = self.run_runner("oom")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(len(self.events("vllm")), 1)
        self.assertIn("OutOfMemoryError", result.stdout)
        self.assertEqual(self.events("python3"), [])

    def test_text_only_can_be_turned_off(self):
        result = self.run_runner(TEXT_ONLY="0")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("--limit-mm-per-prompt", self.serve_args())

    def test_vllm_version_other_than_step_1_is_only_a_hint(self):
        result = self.run_runner(FAKE_VLLM_VERSION="0.31.2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("vLLM 0.31.2", result.stdout)
        self.assertIn("0.33.0", result.stderr)
        result = self.run_runner()
        self.assertNotIn("没有验证过", result.stderr)

    def test_small_gpu_hint_for_bf16(self):
        result = self.run_runner(FAKE_GPU="NVIDIA L40S, 46068")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NVIDIA L40S", result.stdout)
        self.assertIn("QUANTIZATION=fp8", result.stderr)
        for extra in ({"QUANTIZATION": "fp8"}, {"MODEL": REPO + "-FP8"}, {}):
            with self.subTest(extra=extra):
                gpu = {} if not extra else {"FAKE_GPU": "NVIDIA L40S, 46068"}
                result = self.run_runner(**extra, **gpu)
                self.assertNotIn("多半放不下", result.stderr)

    # ------------------------------------------------------------------ AUTO_STOP on RunPod
    def test_auto_stop_refuses_results_on_the_container_disk(self):
        result = self.run_runner(AUTO_STOP="1", FAKE_DF_MOUNT="/")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("容器盘", result.stderr)
        self.assertEqual(self.events("vllm"), [])
        self.assertEqual(self.events("runpodctl"), [])

    def test_auto_stop_on_the_volume_runs_and_stops(self):
        result = self.run_runner(AUTO_STOP="1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.archives()), 1)
        self.assertEqual([e["args"] for e in self.events("runpodctl")], [["stop", "pod", "pod-1"]])

    def test_auto_stop_falls_back_to_the_new_runpodctl_syntax(self):
        result = self.run_runner("old_stop_syntax_gone", AUTO_STOP="1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([e["args"] for e in self.events("runpodctl")], [["stop", "pod", "pod-1"], ["pod", "stop", "pod-1"]])


if __name__ == "__main__":
    unittest.main()
