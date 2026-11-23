#!/usr/bin/env python3
"""Unseen-content probe for the HASH (sha256) goal (2026-11-23).

Same discipline as the archive/zip/bzip2 probes: TEACH on content A with fresh
variants offered (→ ADMIT), COLD on content B with an empty store, WARM on
content B seeded by TEACH (expect INSTANT_RECALL), CONTROL re-running content A.
Zero model calls, zero network, $0. Producer-run sandbox measurement.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import (  # noqa: E402
    build_env, KIND,
)

goal = "hash data.txt into data.sha256"
BUDGET = 60
MAX_DEPTH = 4

TEACH_SEED = b"alpha beta gamma\ndelta epsilon\nzeta eta\n"
TARGET_SEED = b"probe probe probe\ncontent differs\nsame shape\n"
FRESH_VARIANTS = [
    b"variant one\nrule must not require specific content\n",
    b"variant two\nsame goal family, fresh bytes\n",
]


def main():
    tmp = Path(tempfile.mkdtemp(prefix="unseen_hash_computer_"))
    mem = tmp / "memory.json"

    # TEACH
    env_t, meta_t = build_env(goal, seed_contents={"data.txt": TEACH_SEED}, limit=8)
    fresh = []
    for vs in FRESH_VARIANTS:
        fe, _ = build_env(goal, seed_contents={"data.txt": vs}, limit=8)
        fresh.append(fe)
    t0 = time.time()
    out_teach = pa.run(
        env_t, goal, env_t.action_names(),
        goal_predicate=meta_t["is_goal"], env_kind=KIND, memory_path_=mem,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta_t["heuristic"],
        unseen_instances=fresh,
        fresh_reset=lambda e: e.reset(),
        fresh_act=lambda e, a: e.act(a),
        fresh_state=lambda e: e.state(),
    )
    teach_dur = time.time() - t0
    admit = (out_teach.get("steps") or {}).get("admit") or {}
    print("TEACH pass:", out_teach.get("pass"), "status:", out_teach.get("status"),
          "admit:", admit.get("verdict"), "reached:", admit.get("reached"),
          "dur:", round(teach_dur, 3))

    # COLD (content B)
    cold_path = tmp / "cold.json"
    env_c, meta_c = build_env(goal, seed_contents={"data.txt": TARGET_SEED}, limit=8)
    t0 = time.time()
    out_cold = pa.run(
        env_c, goal, env_c.action_names(),
        goal_predicate=meta_c["is_goal"], env_kind=KIND, memory_path_=cold_path,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta_c["heuristic"],
    )
    print("COLD pass:", out_cold.get("pass"), "outcome:", out_cold.get("outcome"),
          "dur:", round(time.time() - t0, 3))

    # WARM (content B)
    env_w, meta_w = build_env(goal, seed_contents={"data.txt": TARGET_SEED}, limit=8)
    t0 = time.time()
    out_warm = pa.run(
        env_w, goal, env_w.action_names(),
        goal_predicate=meta_w["is_goal"], env_kind=KIND,
        memory_path_=mem, budget=BUDGET, max_depth=MAX_DEPTH,
        heuristic=meta_w["heuristic"],
    )
    warm_steps = out_warm.get("steps") or {}
    mr = warm_steps.get("memory_replay")
    print("WARM pass:", out_warm.get("pass"), "status:", out_warm.get("status"),
          "outcome:", out_warm.get("outcome"), "dur:", round(time.time() - t0, 3),
          "replay:", (mr or {}).get("status"), (mr or {}).get("rule_id"))

    # CONTROL (content A, warm)
    env_ctl, meta_ctl = build_env(goal, seed_contents={"data.txt": TEACH_SEED}, limit=8)
    t0 = time.time()
    out_ctl = pa.run(
        env_ctl, goal, env_ctl.action_names(),
        goal_predicate=meta_ctl["is_goal"], env_kind=KIND,
        memory_path_=mem, budget=BUDGET, max_depth=MAX_DEPTH,
        heuristic=meta_ctl["heuristic"],
    )
    ctl_steps = out_ctl.get("steps") or {}
    mr_ctl = ctl_steps.get("memory_replay")
    print("CONTROL pass:", out_ctl.get("pass"), "status:", out_ctl.get("status"),
          "dur:", round(time.time() - t0, 3), "replay:", (mr_ctl or {}).get("status"))

    for e in (env_t, env_c, env_w, env_ctl, *fresh):
        try:
            e.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
