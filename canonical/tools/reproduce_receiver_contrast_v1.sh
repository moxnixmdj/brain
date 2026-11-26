#!/usr/bin/env bash
# Host-side reproduction on pinned historical sources. Not a Harbor task or a model.
# Requires Git, gh, Python 3.11 + venv, Linux user/mount/PID/network namespaces.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
w=$(realpath -m "${1:?specify a NEW scratch directory outside the checkout}")
case "$w/" in "$PWD/"*) exit 2;; esac
mkdir "$w"
parent=f25f697a439acc2b0d84aa8f5413330f4e2e75cf
teacher=05f6fd0df4ecbd104eb7a229f9f185c2484dee69
git init -q --template= --bare "$w/click.git"
git --git-dir="$w/click.git" fetch -q --no-tags --depth=65 https://github.com/pallets/click.git "$parent"
git --git-dir="$w/click.git" cat-file blob "$parent:src/click/core.py" > "$w/parent.py"
unshare -c -n env -i PATH=/usr/bin:/bin HOME="$w" PYTHONDONTWRITEBYTECODE=1 python3 - "$w" <<'PY'
from pathlib import Path
import sys
from canonical.tools.subtree_transfer_probe_v1 import teach
w = Path(sys.argv[1]); print(teach(w/'parent.py', w/'store.json'))
PY
for off in 1 16 64 4 32; do
  id=$(git --git-dir="$w/click.git" rev-parse "$parent~$off")
  mkdir "$w/click-$off"; git --git-dir="$w/click.git" archive "$id" | tar -x -C "$w/click-$off"
  args=(--checkout "$w/click-$off" --store "$w/store.json" --product src/click)
  python3 -m canonical.tools.receiver_cli_contrast_v1 "${args[@]}" --out "$w/result-click-$off"
  if [ "$off" = 4 ] || [ "$off" = 32 ]; then
    python3 -m canonical.tools.receiver_cli_contrast_v1 "${args[@]}" --out "$w/result-click-$off-directed" --directed
  fi
done
git init -q --template= --bare "$w/typer.git"
git --git-dir="$w/typer.git" fetch -q --no-tags --depth=1 https://github.com/fastapi/typer.git a9179507924aa0095813d6197b891121d05ed74f
mkdir "$w/typer-release"; git --git-dir="$w/typer.git" archive FETCH_HEAD | tar -x -C "$w/typer-release"
python3 -m canonical.tools.receiver_cli_contrast_v1 --checkout "$w/typer-release" --product typer --store "$w/store.json" --out "$w/result-typer-release"
sha256sum "$w"/result-*/{probe,contrast}.json > "$w/pregrade.sha256"
# Now access the evaluation check. No grading log, test, patch hash or verifier enters a producer room.
gh api "repos/pallets/click/contents/tests/test_arguments.py?ref=$teacher" --jq .content | base64 -d > "$w/check.py"
for env in initial locked; do
  python3 -m venv "$w/$env-grader"; py="$w/$env-grader/bin/python"
  "$py" -m pip install -q --only-binary=:all: --no-deps --index-url https://pypi.org/simple flit_core==3.12.0
  if [ "$env" = initial ]; then
    "$py" -m pip install -q --only-binary=:all: --index-url https://pypi.org/simple pytest==9.2.0
    offsets=(1 16 64 4 32)
  else
    # Preserve the initial collection errors. Separate evaluator, project's own lock, no warning suppression.
    python3 - "$w" <<'PY'
from pathlib import Path
import sys, tomllib
w = Path(sys.argv[1]); locks = []
for off in (32,64):
    packages = tomllib.loads((w/f'click-{off}/uv.lock').read_text())['package']
    locks.append(sorted(row['name']+'=='+row['version']+' '+' '.join('--hash='+wh['hash'] for wh in row['wheels'])
                        for row in packages if row['name'] in {'pytest','iniconfig','pluggy','pygments','packaging'}))
assert len(locks[0]) == 5 and locks[0] == locks[1]
(w/'evaluator.lock').write_text('\n'.join(locks[0])+'\n')
PY
    "$py" -m pip install -q --only-binary=:all: --no-deps --require-hashes --index-url https://pypi.org/simple -r "$w/evaluator.lock"
    offsets=(32 64)
  fi
  for off in "${offsets[@]}"; do
    d="$w/result-click-$off"; if [ "$off" = 4 ] || [ "$off" = 32 ]; then d="$d-directed"; fi
    "$py" -m pip install -q --no-index --no-deps --no-build-isolation --force-reinstall "$w/click-$off"
    "$py" -m canonical.tools.grade_frozen_click_transfer_v1 --checkout "$w/click-$off" --teacher-check "$w/check.py" \
      --frozen "$d/frozen" --probe "$d/probe.json" --index 0 --output "$w/$env-logs-$off" > "$w/$env-$off.json"
  done
done
for off in 4 32; do
  python3 -m canonical.tools.receiver_cli_contrast_v1 --checkout "$w/click-$off" --product src/click \
    --out "$w/result-click-$off-directed" --recheck-to "$w/aba-$off"
done
printf 'Pre-grader probes and separate per-arm grades: %s\n' "$w"
