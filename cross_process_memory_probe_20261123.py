#!/usr/bin/env python3
"""Cross-process persistence probe (2026-11-23).

The mission's 'instant learning permanently' claim: one experience on content A
in one process must be usable by a fresh process with no other state. This probe
runs TEACH in a subprocess (memory written to disk), then runs a fresh process
against content B loading ONLY the disk file and expects INSTANT_RECALL with
content verified. Honest evidence for persistence, not a re-claim.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHILD = Path(tempfile.mkdtemp(prefix="cross_process_teach_"))
MEMORY = CHILD / "memory.json"

TEACH_CONTENT = b"alpha beta gamma\ndelta epsilon\nzeta eta\n"
TARGET_CONTENT = b"probe probe probe\ncontent differs\nsame shape\n"

PHASE_TEACH = r'''
import sys
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import build_env, KIND

goal = "decompress data.gz into out.txt"
import gzip
seed = {"data.gz": gzip.compress(b"alpha beta gamma\ndelta epsilon\nzeta eta\n")}
env, meta = build_env(goal, seed_contents=seed, limit=8)
fresh = []
for vs in [b"variant one\n", b"variant two\n"]:
    fe, _ = build_env(goal, seed_contents={"data.gz": gzip.compress(vs)}, limit=8)
    fresh.append(fe)
out = pa.run(
    env, goal, env.action_names(),
    goal_predicate=meta["is_goal"], env_kind=KIND, memory_path_=sys.argv[1],
    budget=60, max_depth=4, heuristic=meta["heuristic"],
    unseen_instances=fresh,
    fresh_reset=lambda e: e.reset(),
    fresh_act=lambda e, a: e.act(a),
    fresh_state=lambda e: e.state(),
)
print("TEACH pass:", out.get("pass"), "status:", out.get("status"),
      "admit:", ((out.get("steps") or {}).get("admit") or {}).get("verdict"))
for e in (env, *fresh):
    try: e.close()
    except Exception: pass
'''

PHASE_COLD = r'''
import sys
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import build_env, KIND
import gzip

goal = "decompress data.gz into out.txt"
seed = {"data.gz": gzip.compress(b"probe probe probe\ncontent differs\nsame shape\n")}
env, meta = build_env(goal, seed_contents=seed, limit=8)
import pathlib
target_path = pathlib.Path(env.root) / "out.txt"
out = pa.run(
    env, goal, env.action_names(),
    goal_predicate=meta["is_goal"], env_kind=KIND, memory_path_=sys.argv[1],
    budget=60, max_depth=4, heuristic=meta["heuristic"],
)
steps = out.get("steps") or {}
mr = steps.get("memory_replay") or {}
content = target_path.read_bytes() if target_path.is_file() else None
print("COLD pass:", out.get("pass"), "status:", out.get("status"),
      "outcome:", out.get("outcome"), "replay:", mr.get("status"),
      "replay_rule:", mr.get("rule_id"),
      "content_matches:", content == b"probe probe probe\ncontent differs\nsame shape\n")
try: env.close()
except Exception: pass
'''


def run_phase(name, code, argv):
    t0 = time.time()
    proc = subprocess.run([sys.executable, "-c", code] + argv,
                          capture_output=True, text=True,
                          cwd=str(ROOT), timeout=300)
    dur = time.time() - t0
    print(f"--- {name} ({round(dur,1)}s) stdout ---")
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print("STDERR:", proc.stderr.strip()[-2000:])
    return proc.returncode


def main():
    rc1 = run_phase("phase 1: TEACH (process A)", PHASE_TEACH, [str(MEMORY)])
    assert rc1 == 0
    print(f"memory file exists: {MEMORY.is_file()}, size: {MEMORY.stat().st_size if MEMORY.exists() else 0}")

    rc2 = run_phase("phase 2: COLD B (fresh process)", PHASE_COLD, [str(MEMORY)])
    print()
    print("summary: phase1 rc:", rc1, "phase2 rc:", rc2)


if __name__ == "__main__":
    main()
