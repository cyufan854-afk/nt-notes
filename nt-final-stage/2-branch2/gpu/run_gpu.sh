#!/usr/bin/env bash
# 在租来的单卡 GPU（H100 80GB / A100 80GB）上一次跑完三个任务。
# 前提：机器上装好了 vllm（RunPod / Vast 选 vLLM 镜像即可）；本程序包连同 job/ 目录已经传上来。
#
#   MODEL=/workspace/nt27b GPU_PRICE=2.5 bash gpu/run_gpu.sh
#
# 可选环境变量：
#   JOB=job          prepare 生成的目录
#   MODEL_REVISION=版本 权重或适配器版本；已有响应时必须显式设置，原地更换权重时必须更新
#   CONC=64          同时在途的请求数
#   MAXLEN=16384     上下文长度（最长的请求约 4.5k token，16k 足够）
#   PORT=8000
#   GPU_PRICE=0      每小时价格，只用来打印花费
#   AUTO_STOP=1      成功或出错后自动停机（RunPod，需要 runpodctl 和 RUNPOD_POD_ID）；结果先打包到 JOB 所在的卷上
set -euo pipefail
cd "$(dirname "$0")/.."

JOB="${JOB:-job}"
VLLM_PID=""

archive_results() {
  local job_dir job_parent job_name out temporary
  if [ ! -d "$JOB" ]; then
    echo "没有结果目录 ${JOB}，无法打包。" >&2
    return 1
  fi
  job_dir="$(cd "$JOB" && pwd)" || return 1
  job_parent="$(dirname "$job_dir")"
  job_name="$(basename "$job_dir")"
  out="${job_parent}/results-$(date +%Y%m%d-%H%M%S)-$$.tgz"
  temporary="${out}.tmp"
  if tar -czf "$temporary" -C "$job_parent" -- "$job_name" && mv "$temporary" "$out"; then
    echo "== 结果已打包：${out}（把它下载回 Mac）"
    return 0
  fi
  rm -f "$temporary"
  echo "结果打包失败。原始结果保留在 ${JOB}。" >&2
  return 1
}

cleanup() {
  local status=$? archive_ok=0 stop_status
  trap - EXIT INT TERM
  set +e
  if [ -n "$VLLM_PID" ]; then
    kill "$VLLM_PID" 2>/dev/null || true
    wait "$VLLM_PID" 2>/dev/null || true
  fi
  if archive_results; then
    archive_ok=1
  elif [ "$status" -eq 0 ]; then
    status=1
  fi
  if [ "${AUTO_STOP:-0}" = 1 ]; then
    if [ "$archive_ok" -ne 1 ]; then
      echo "结果没有成功打包，保留机器以便取回结果。" >&2
    elif command -v runpodctl >/dev/null && [ -n "${RUNPOD_POD_ID:-}" ]; then
      echo "== 自动停机"
      if runpodctl stop pod "$RUNPOD_POD_ID"; then
        :
      else
        stop_status=$?
        [ "$status" -ne 0 ] || status=$stop_status
      fi
    else
      echo "AUTO_STOP=1 但没有 runpodctl / RUNPOD_POD_ID：请手动停机。" >&2
      [ "$status" -ne 0 ] || status=1
    fi
  fi
  exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

MODEL="${MODEL:?请设置 MODEL=模型目录（HF 格式 safetensors）或 HF 仓库名}"
PORT="${PORT:-8000}"
CONC="${CONC:-64}"
MAXLEN="${MAXLEN:-16384}"
GPU_PRICE="${GPU_PRICE:-0}"
BASE="http://127.0.0.1:${PORT}/v1"

[ -f "$JOB/manifest.json" ] || { echo "没有 $JOB/manifest.json：先在 Mac 上运行 prepare，再把整个目录传上来。"; exit 2; }
if [ -z "${MODEL_REVISION:-}" ]; then
  for response in "$JOB"/{polish,triage,refs}/responses.jsonl; do
    if [ -s "$response" ]; then
      echo "已有响应，恢复运行必须显式设置 MODEL_REVISION。原地更换权重或适配器时请使用新版本值。" >&2
      exit 2
    fi
  done
  MODEL_REVISION="$MODEL"
fi
MODEL_IDENTITY="$(
  LC_ALL=C
  printf '%s:%s,%s:%s,' "${#MODEL}" "$MODEL" "${#MODEL_REVISION}" "$MODEL_REVISION"
)"
for tool in vllm python3 curl tar; do
  command -v "$tool" >/dev/null || { echo "这台机器上没有 ${tool}。"; exit 2; }
done

echo "== 启动 vLLM（日志 vllm.log）"
vllm serve "$MODEL" --served-model-name nt27b --port "$PORT" --max-model-len "$MAXLEN" \
  --gpu-memory-utilization 0.92 --dtype bfloat16 --enable-prefix-caching > vllm.log 2>&1 &
VLLM_PID=$!

require_vllm_running() {
  if ! kill -0 "$VLLM_PID" 2>/dev/null; then
    echo "vLLM 启动失败："
    tail -40 vllm.log
    exit 3
  fi
}

for i in $(seq 1 180); do
  require_vllm_running
  if curl -sf --connect-timeout 2 --max-time 5 "$BASE/models" >/dev/null; then
    require_vllm_running
    break
  fi
  require_vllm_running
  sleep 10
done
require_vllm_running
curl -sf --connect-timeout 2 --max-time 5 "$BASE/models" >/dev/null || { echo "vLLM 30 分钟内没有就绪："; tail -40 vllm.log; exit 3; }
require_vllm_running

ASK=(python3 nt27b.py ask "$JOB" --base-url "$BASE" --model nt27b --model-revision "$MODEL_IDENTITY" --json-schema --gpu-price "$GPU_PRICE")

echo "== 冒烟测试：每个任务 3 条"
"${ASK[@]}" --task all --sample 3 --concurrency 9
python3 nt27b.py verify "$JOB" --task all --sample 3
if ! python3 nt27b.py collect "$JOB"; then
  echo "冒烟样本已通过验证；其余旧响应或失败响应将在全量运行中刷新。" >&2
fi

echo "== 全量"
if ! "${ASK[@]}" --task all --concurrency "$CONC"; then
  echo "全量请求有错误，继续重试。" >&2
fi
echo "== 重试出错的"
if ! "${ASK[@]}" --task all --concurrency "$CONC" --retry-errors; then
  echo "重试后仍有请求错误，继续收集并验证。" >&2
fi
python3 nt27b.py collect "$JOB"
python3 nt27b.py verify "$JOB" --task all
