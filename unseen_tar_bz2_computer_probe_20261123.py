#!/usr/bin/env python3
"""Unseen-content probe for the .tar.bz2 archive goal (2026-11-23).

Same discipline as unseen_zip_bzip2_computer_probe_20261123.py:
TEACH on content A with fresh-instance admission, COLD with empty store on
content B, WARM seeded by TEACH, CONTROL re-running content A.
Zero model calls, zero network, $0.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tarfile

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import (  # noqa: E402
    build_env, KIND,
)

GOAL = "make an archive out.tar.bz2"
BUDGET = 60
MAX_DEPTH = 4

TEACH_SEED = b"alpha beta gamma\ndelta epsilon\nzeta eta\n"
TARGET_SEED = b"probe probe probe\ncontent differs\nsame shape\n"
FRESH_VARIANTS = [
    b"variant one\nrule must not require specific content\n",
    b"variant two\nsame goal family, fresh bytes\n",
]


def _members(blob):
    out = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:bz2") as tf:
        for m in tf.getmembers():
            if m.isfile():
                out[m.name] = tf.extractfile(m).read()
    return out


def _matches(tree, seed):
    blob = tree.get("out.tar.bz2")
    if not blob:
        return False
    try:
        members = _members(blob)
    except Exception:
        return False
    # predicate requires the source file by basename with exact bytes
    src_basename = "data.txt"
    return any(n.endswith(src_basename) and b == seed for n, b in members.items())


def main():
    tmp = Path(tempfile.mkdtemp(prefix="unseen_tar_bz2_probe_"))
    teach_mem = tmp / "memory.json"

    # TEACH
    env_t, meta_t = build_env(GOAL, seed_contents={"data.txt": TEACH_SEED}, limit=8)
    fresh_instances = []
    for vs in FRESH_VARIANTS:
        fe, _ = build_env(GOAL, seed_contents={"data.txt": vs}, limit=8)
        fresh_instances.append(fe)
    t0 = time.time()
    out_teach = pa.run(
        env_t, GOAL, env_t.action_names(),
        goal_predicate=meta_t["is_goal"], env_kind=KIND, memory_path_=teach_mem,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta_t["heuristic"],
        unseen_instances=fresh_instances,
        fresh_reset=lambda e: e.reset(),
        fresh_act=lambda e, a: e.act(a),
        fresh_state=lambda e: e.state(),
    )
    teach_dur = time.time() - t0
    admit = (out_teach.get("steps") or {}).get("admit") or {}
    print("TEACH pass:", out_teach.get("pass"), "status:", out_teach.get("status"),
          "admit:", admit.get("verdict"), "reached:", admit.get("reached"),
          "dur:", round(teach_dur, 3),
          "content_verified:", _matches(env_t.tree(), TEACH_SEED))

    # COLD
    cold_path = tmp / "cold.json"
    env_c, meta_c = build_env(GOAL, seed_contents={"data.txt": TARGET_SEED}, limit=8)
    t0 = time.time()
    out_cold = pa.run(
        env_c, GOAL, env_c.action_names(),
        goal_predicate=meta_c["is_goal"], env_kind=KIND, memory_path_=cold_path,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta_c["heuristic"],
    )
    print("COLD pass:", out_cold.get("pass"), "outcome:", out_cold.get("outcome"),
          "dur:", round(time.time() - t0, 3),
          "content_verified:", _matches(env_c.tree(), TARGET_SEED))

    # WARM
    env_w, meta_w = build_env(GOAL, seed_contents={"data.txt": TARGET_SEED}, limit=8)
    t0 = time.time()
    out_warm = pa.run(
        env_w, GOAL, env_w.action_names(),
        goal_predicate=meta_w["is_goal"], env_kind=KIND,
        memory_path_=teach_mem, budget=BUDGET, max_depth=MAX_DEPTH,
        heuristic=meta_w["heuristic"],
    )
    warm_steps = out_warm.get("steps") or {}
    mr = warm_steps.get("memory_replay")
    print("WARM pass:", out_warm.get("pass"), "status:", out_warm.get("status"),
          "outcome:", out_warm.get("outcome"), "dur:", round(time.time() - t0, 3),
          "replay:", (mr or {}).get("status"), (mr or {}).get("rule_id"),
          "content_verified:", _matches(env_w.tree(), TARGET_SEED))

    # CONTROL (content A, warm)
    env_ctl, meta_ctl = build_env(GOAL, seed_contents={"data.txt": TEACH_SEED}, limit=8)
    t0 = time.time()
    out_ctl = pa.run(
        env_ctl, GOAL, env_ctl.action_names(),
        goal_predicate=meta_ctl["is_goal"], env_kind=KIND,
        memory_path_=teach_mem, budget=BUDGET, max_depth=MAX_DEPTH,
        heuristic=meta_ctl["heuristic"],
    )
    ctl_steps = out_ctl.get("steps") or {}
    mr_ctl = ctl_steps.get("memory_replay")
    print("CONTROL pass:", out_ctl.get("pass"), "status:", out_ctl.get("status"),
          "dur:", round(time.time() - t0, 3), "replay:", (mr_ctl or {}).get("status"),
          "content_verified:", _matches(env_ctl.tree(), TEACH_SEED))

    for e in (env_t, env_c, env_w, env_ctl, *fresh_instances):
        try:
            e.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
