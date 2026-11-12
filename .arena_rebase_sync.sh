#!/usr/bin/env bash
# Rebase this branch onto current origin/main, resolve the generated artifact by regeneration only,
# rebind the base commit, and re-run every local gate. Never hand-merges BRAIN_UNIFIED_MODEL_V1.json.
set -euo pipefail
cd /home/user/brain

git fetch origin main -q
BASE=$(git rev-parse origin/main)
echo "current main: $BASE"

if git merge-base --is-ancestor "$BASE" HEAD; then
  echo "already up to date with main"
  exit 0
fi

if git rebase origin/main 2>&1 | tail -4; then
  :
else
  # a conflict can only be in generated artifacts; regenerate rather than merge
  git checkout --theirs canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json 2>/dev/null || true
  git add -A
  GIT_EDITOR=true git -c user.name="Brain Agent" -c user.email="agent@arena.ai" rebase --continue 2>&1 | tail -3
fi

python3 - "$BASE" <<'PY'
import json, pathlib, sys
base = sys.argv[1]
p = pathlib.Path('canonical/action_intents/WHAT_A_SUCCESS_TEACHES_20261112_V1.json')
d = json.loads(p.read_text())
d['canonical_base_commit'] = base
d['recursive_obs']['canonical_base_commit'] = base
p.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
print("rebound", base)
PY

python3 canonical/runtime/compile_brain_unified_model_v1.py >/dev/null
python3 canonical/runtime/verify_brain_unified_model_v1.py | tail -2
python3 canonical/runtime/enforce_goal_hierarchy.py --base "$BASE" --head HEAD | head -1
python3 execution_guard/repo_integrity_guard_v1.py --base HEAD | tail -1
/tmp/venv/bin/python -m pytest canonical/tests/test_what_a_success_teaches_v1.py -q | tail -1

git add -A
git -c user.name="Brain Agent" -c user.email="agent@arena.ai" commit -q -m "Rebind to main $BASE and regenerate the artifact

Automated rebase: main advanced, the content-addressed artifact is a function of the whole tree, so
the binding and the artifact are regenerated together. Local gates re-run before pushing." || echo "nothing to commit"
git push --force-with-lease origin arena/b2f83018-brain 2>&1 | tail -1
