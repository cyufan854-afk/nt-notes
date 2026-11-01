#!/usr/bin/env bash
# Run the four test suites. The notebook suite needs numpy, torch and safetensors; it is skipped when they are missing.
set -u
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
status=0
run() {
  echo "== $1"
  (cd "$1" && shift && "$@") 2>&1 | tail -4
  [ "${PIPESTATUS[0]}" -eq 0 ] || status=1
}
run 5-final-review "$PY" -m unittest discover -s tests
run 2-branch2 "$PY" -m unittest discover -s tests
run 3-combine "$PY" -m unittest discover -s . -p 'test_*.py'
run 4-cross-review "$PY" -m unittest discover -s . -p 'test_*.py'
if "$PY" -c 'import numpy, torch, safetensors' 2>/dev/null; then
  run 1-model-merge "$PY" -m unittest discover -s tests
else
  echo "== 1-model-merge：缺 numpy / torch / safetensors，跳过（在装了它们的环境里用 PYTHON=... bash check_all.sh）"
fi
exit $status
