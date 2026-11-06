#!/usr/bin/env bash
# 在租来的单卡 GPU（H100 80GB / A100 80GB）上一次跑完三个任务。
# 前提：机器上装好了 vllm（第 1 步生成把关用的是 0.33.0：python3 -m pip install "vllm==0.33.0"）；本程序包连同 job/ 目录已经传上来。
# RunPod 上从开机到取回结果的完整做法见 README.md“在 RunPod 上跑”。
#
#   MODEL=/workspace/nt27b GPU_PRICE=2.5 bash gpu/run_gpu.sh
#
# 可选环境变量：
#   JOB=job          prepare 生成的目录
#   MODEL_REVISION=版本 权重或适配器版本；已有响应时必须显式设置，原地更换权重时必须更新。
#                    MODEL 是 Hugging Face 仓库名、MODEL_REVISION 是 40 位 commit 时，vLLM 也按这个 commit 下载
#                    （--revision / --tokenizer-revision），保证跑的正是第 1 步上传的那一版。私有仓库需要 HF_TOKEN。
#   QUANTIZATION=    留空（默认）：按仓库原样加载，BF16 仓库就跑 BF16。fp8：把 BF16 仓库在线量化成 FP8（第 1 步生成把关的做法），
#                    设了就进入回答缓存的身份。FP8 仓库（…-FP8）自带量化配置，不要再设。
#   TEXT_ONLY=1      不给视觉编码器留显存（--limit-mm-per-prompt 图像、视频都为 0，同第 1 步）；vLLM 因这一项启动失败时，
#                    去掉它自动重启一次。0：不加
#   PREFETCH=1       Hub 上的模型先用 hf download 下到缓存再启动 vLLM：下载不占就绪的 30 分钟；私有仓库没有 HF_TOKEN、
#                    commit 不对、磁盘不够时马上停下。0：由 vLLM 自己下载
#   VLLM_EXPECTED=0.33.0  第 1 步用的 vLLM 版本；vLLM 日志里的版本不同时只提示，不停
#   CONC=64          同时在途的请求数（也作为 vLLM 的 --max-num-seqs）
#   MAXLEN=16384     上下文长度（最长的请求约 4.5k token，回答最多 8192，16k 足够）
#   PORT=8000
#   GPU_PRICE=0      每小时价格，只用来打印花费
#   AUTO_STOP=1      成功或出错后自动停机（RunPod，需要 runpodctl 和 RUNPOD_POD_ID）；结果先打包到 JOB 所在的卷上。
#                    RunPod 停机会清空容器盘，所以 JOB 必须在 /workspace 卷上，否则开跑前就停下
#
# 在 RunPod 上（有 /workspace 卷、没有另设 HF_HOME / HF_HUB_CACHE 时），Hugging Face 缓存放在 /workspace/.cache/huggingface：
# 容器盘一般放不下约 54 GB 的 BF16 权重，停机时还会被清空。登录 token 的位置不变。
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
      # 旧写法 stop pod 在文档里仍有；新版 runpodctl 的写法是 pod stop
      if runpodctl stop pod "$RUNPOD_POD_ID" || runpodctl pod stop "$RUNPOD_POD_ID"; then
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
QUANTIZATION="${QUANTIZATION:-}"
TEXT_ONLY="${TEXT_ONLY:-1}"
PREFETCH="${PREFETCH:-1}"
VLLM_EXPECTED="${VLLM_EXPECTED:-0.33.0}"
VOLUME="${RUNPOD_VOLUME:-/workspace}"
BASE="http://127.0.0.1:${PORT}/v1"

[ -f "$JOB/manifest.json" ] || { echo "没有 $JOB/manifest.json：先在 Mac 上运行 prepare，再把整个目录传上来。"; exit 2; }
[[ "$QUANTIZATION" =~ ^[A-Za-z0-9_-]*$ ]] || { echo "QUANTIZATION 只能是 vLLM 的量化方式名（例如 fp8），现在是：${QUANTIZATION}" >&2; exit 2; }
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
  # 在线量化改变回答，所以进入身份；不设时身份与以前完全相同，已有的回答照常沿用
  if [ -n "$QUANTIZATION" ]; then
    quantization="quantization=${QUANTIZATION}"
    printf '%s:%s,' "${#quantization}" "$quantization"
  fi
)"
for tool in vllm python3 curl tar; do
  command -v "$tool" >/dev/null || { echo "这台机器上没有 ${tool}。"; exit 2; }
done

# df -P 的第二行：可用 KB 和挂载点（没有 df 时什么都不做）
disk_of() {
  local path="$1" _ avail mount
  while [ ! -e "$path" ]; do path="$(dirname "$path")"; done
  df -Pk "$path" 2>/dev/null | { read -r _; read -r _ _ _ avail _ mount; printf '%s %s\n' "${avail:-}" "${mount:-}"; }
}

if [ "${AUTO_STOP:-0}" = 1 ] && [ -n "${RUNPOD_POD_ID:-}" ] && command -v df >/dev/null; then
  read -r _ job_mount < <(disk_of "$JOB") || true
  if [ "${job_mount:-}" = "/" ]; then
    echo "AUTO_STOP=1：${JOB} 在容器盘上，RunPod 停机会清空容器盘，结果会丢。把 2-branch2/ 放到 ${VOLUME} 下再运行，或者不设 AUTO_STOP。" >&2
    AUTO_STOP=0                                  # 这次退出时也不停机
    exit 2
  fi
fi

if [ -z "${HF_HOME:-}${HF_HUB_CACHE:-}" ] && [ -d "$VOLUME" ] && [ -w "$VOLUME" ]; then
  export HF_HUB_CACHE="${VOLUME}/.cache/huggingface/hub"
  export HF_XET_CACHE="${VOLUME}/.cache/huggingface/xet"
  echo "== Hugging Face 缓存放在卷上：${HF_HUB_CACHE}"
fi

if command -v nvidia-smi >/dev/null; then
  if gpu_line="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null)"; then
    IFS=',' read -r gpu_name gpu_mib <<< "${gpu_line%%$'\n'*}" || true
    gpu_mib="${gpu_mib//[^0-9]/}"
    echo "== GPU：${gpu_name:-?}，${gpu_mib:-?} MiB"
    if [ -n "$gpu_mib" ] && [ "$gpu_mib" -lt 76000 ] && [ -z "$QUANTIZATION" ] && [[ "$MODEL" != *-FP8 ]]; then
      echo "提示：BF16 权重约 54 GB，这张卡多半放不下。换 80GB 的卡，或者设 QUANTIZATION=fp8。" >&2
    fi
  fi
fi

HUB_MODEL=0
if [ ! -e "$MODEL" ] && [[ "$MODEL" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  HUB_MODEL=1
fi
VLLM_REVISION=()
if [ ! -e "$MODEL" ] && [[ "$MODEL_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  VLLM_REVISION=(--revision "$MODEL_REVISION" --tokenizer-revision "$MODEL_REVISION")
  echo "== 模型 ${MODEL} 固定在 commit ${MODEL_REVISION}"
fi

if [ "$PREFETCH" = 1 ] && [ "$HUB_MODEL" = 1 ]; then
  HF_CLI=()
  if command -v hf >/dev/null; then
    HF_CLI=(hf download)
  elif command -v huggingface-cli >/dev/null; then
    HF_CLI=(huggingface-cli download)
  else
    echo "没有 hf 命令：模型由 vLLM 启动时下载，算在就绪的 30 分钟里。" >&2
  fi
  if [ ${#HF_CLI[@]} -gt 0 ]; then
    if command -v df >/dev/null; then
      read -r cache_kb cache_mount < <(disk_of "${HF_HUB_CACHE:-${HF_HOME:-${HOME:-/root}/.cache/huggingface}/hub}") || true
      if [[ "${cache_kb:-}" =~ ^[0-9]+$ ]]; then
        echo "== 缓存所在的盘（${cache_mount}）可用 $((cache_kb / 1048576)) GiB"
        if [ "$cache_kb" -lt $((60 * 1048576)) ]; then
          echo "提示：BF16 仓库约 54 GB、FP8 仓库约 37 GB；已经在缓存里的部分不再占地方。不够时下载会失败。" >&2
        fi
      fi
    fi
    HF_REVISION=()
    [ ${#VLLM_REVISION[@]} -eq 0 ] || HF_REVISION=(--revision "$MODEL_REVISION")
    echo "== 下载模型到缓存（已经下好的文件跳过）"
    if ! "${HF_CLI[@]}" "$MODEL" ${HF_REVISION[@]+"${HF_REVISION[@]}"}; then
      echo "下载 ${MODEL} 失败：私有仓库要设 HF_TOKEN（对这个仓库有读权限）；MODEL_REVISION 要是这个仓库的 commit；也看一下磁盘空间。" >&2
      exit 2
    fi
  fi
fi

MM_ARGS=()
if [ "$TEXT_ONLY" = 1 ]; then
  MM_ARGS=(--limit-mm-per-prompt '{"image":0,"video":0}')
fi
QUANT_ARGS=()
[ -z "$QUANTIZATION" ] || QUANT_ARGS=(--quantization "$QUANTIZATION")

start_vllm() {
  echo "== 启动 vLLM（日志 vllm.log）"
  vllm serve "$MODEL" ${VLLM_REVISION[@]+"${VLLM_REVISION[@]}"} --served-model-name nt27b --port "$PORT" --max-model-len "$MAXLEN" \
    --gpu-memory-utilization 0.92 --dtype bfloat16 --enable-prefix-caching --max-num-seqs "$CONC" \
    ${QUANT_ARGS[@]+"${QUANT_ARGS[@]}"} ${MM_ARGS[@]+"${MM_ARGS[@]}"} > vllm.log 2>&1 &
  VLLM_PID=$!
}

vllm_alive() {
  kill -0 "$VLLM_PID" 2>/dev/null
}

# 0：就绪；1：vLLM 退出了；2：30 分钟内没有就绪
wait_ready() {
  local i
  for i in $(seq 1 180); do
    vllm_alive || return 1
    if curl -sf --connect-timeout 2 --max-time 5 "$BASE/models" >/dev/null; then
      vllm_alive || return 1
      return 0
    fi
    vllm_alive || return 1
    sleep 10
  done
  vllm_alive || return 1
  curl -sf --connect-timeout 2 --max-time 5 "$BASE/models" >/dev/null || return 2
  vllm_alive || return 1
}

# vLLM 是不是因为纯文本那一项而退出的：不认这个参数，或者模型不是多模态的。启动时打印的 non-default args 不算
rejected_text_only() {
  local line
  [ -f vllm.log ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    [[ "$line" == *non-default* ]] && continue
    if [[ "$line" =~ limit[-_](mm[-_])?per[-_]prompt|multimodal ]] && [[ "$line" =~ [Ee]rror|unrecognized ]]; then
      return 0
    fi
  done < vllm.log
  return 1
}

start_vllm
if wait_ready; then ready=0; else ready=$?; fi
if [ "$ready" -eq 1 ] && [ ${#MM_ARGS[@]} -gt 0 ] && rejected_text_only; then
  wait "$VLLM_PID" 2>/dev/null || true
  mv vllm.log vllm-text-only.log
  echo "vLLM 不接受纯文本设置（见 vllm-text-only.log），去掉 --limit-mm-per-prompt 重启一次。" >&2
  MM_ARGS=()
  start_vllm
  if wait_ready; then ready=0; else ready=$?; fi
fi
if [ "$ready" -eq 1 ]; then
  echo "vLLM 启动失败："
  tail -40 vllm.log
  exit 3
elif [ "$ready" -eq 2 ]; then
  echo "vLLM 30 分钟内没有就绪："
  tail -40 vllm.log
  exit 3
fi

served_version=""
while IFS= read -r line || [ -n "$line" ]; do
  if [[ "$line" =~ vLLM.*version\ ([0-9]+\.[0-9]+[0-9A-Za-z.+-]*) ]]; then
    served_version="${BASH_REMATCH[1]}"
    break
  fi
done < vllm.log
if [ -n "$served_version" ]; then
  echo "== vLLM ${served_version}"
  if [ -n "$VLLM_EXPECTED" ] && [ "$served_version" != "$VLLM_EXPECTED" ]; then
    echo "提示：第 1 步生成把关用的是 vLLM ${VLLM_EXPECTED}，这里是 ${served_version}。能跑，但没有验证过；要一致就 python3 -m pip install \"vllm==${VLLM_EXPECTED}\"。" >&2
  fi
fi

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
