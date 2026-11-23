#!/usr/bin/env python3
"""Unseen-content probe for the ZIP and BZIP2 goals (2026-11-23).

Same discipline as unseen_archive_computer_probe_20261123.py -- TEACH on
content A with fresh-instance admission, COLD with empty store on content
B, WARM seeded by TEACH, CONTROL re-running content A. Zero model calls,
zero network, $0. Producer-run sandbox measurement. No capability registered.

The zip goal is the newly-reachable file-writing path ('zip data.txt into
data.zip'), the bzip2 goal is the stdout-capture path ('make a bzip2
archive out.bz2'). Both record whether the admit 2/2 replay on B is a
memory_replay (instant) -- same honest claim the .tar.gz unseen probe
makes -- and what happens to the carried-model walk (warm_walk) when a
rule is NOT served.
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
    drive_perfect_algorithm,
    build_env,
    KIND,
)

GOALS = [
    {"name": "zip_file_writing", "goal": "zip data.txt into data.zip"},
    {"name": "bzip2_stdout_capture", "goal": "make a bzip2 archive out.bz2"},
]

BUDGET = 60
MAX_DEPTH = 4

TEACH_SEED = b"alpha beta gamma\ndelta epsilon\nzeta eta\n"
TARGET_SEED = b"probe probe probe\ncontent differs\nsame shape\n"
CONTROL_SEED = TEACH_SEED
FRESH_VARIANTS = [
    b"variant one\nrule must not require specific content\n",
    b"variant two\nsame goal family, fresh bytes\n",
]


def run_case(name: str, goal: str, results: list):
    rec: dict = {"case": name, "goal": goal, "kind": KIND,
                 "teach": {"seed_bytes": len(TEACH_SEED)},
                 "target": {"seed_bytes": len(TARGET_SEED)},
                 "carried_model": None}
    tmp = Path(tempfile.mkdtemp(prefix="unseen_zip_bzip2_computer_"))

    # ---- TEACH (content A, fresh variants offered) ----
    teach_mem = tmp / "memory.json"
    env_teach, meta_teach = build_env(goal, seed_contents={"data.txt": TEACH_SEED},
                                      limit=8)
    fresh_instances = []
    for vs in FRESH_VARIANTS:
        fe, _ = build_env(goal, seed_contents={"data.txt": vs}, limit=8)
        fresh_instances.append(fe)
    t0 = time.time()
    out_teach = pa.run(
        env_teach, goal, env_teach.action_names(),
        goal_predicate=meta_teach["is_goal"], env_kind=KIND, memory_path_=teach_mem,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta_teach["heuristic"],
        unseen_instances=fresh_instances,
        fresh_reset=lambda e: e.reset(),
        fresh_act=lambda e, a: e.act(a),
        fresh_state=lambda e: e.state(),
    )
    teach_dur = time.time() - t0
    admit = (out_teach.get("steps") or {}).get("admit") or {}
    rec["teach"] = {"pass": bool(out_teach.get("pass")),
                    "status": out_teach.get("status"),
                    "outcome": out_teach.get("outcome"),
                    "admit_verdict": admit.get("verdict"),
                    "admit_rows": admit.get("rows"),
                    "admit_reached": admit.get("reached"),
                    "persist": (out_teach.get("steps") or {}).get("admit", {}).get("persist"),
                    "plan_sketch": (out_teach.get("steps") or {}).get("learn", {}).get("plan_sketch"),
                    "save_priors": (out_teach.get("steps") or {}).get("save_priors", {}).get("status"),
                    "duration_s": round(teach_dur, 3)}

    # ---- COLD (target content, empty store) ----
    cold_path = tmp / "cold_memory.json"
    env_cold, meta_cold = build_env(goal, seed_contents={"data.txt": TARGET_SEED}, limit=8)
    t0 = time.time()
    out_cold = pa.run(
        env_cold, goal, env_cold.action_names(),
        goal_predicate=meta_cold["is_goal"], env_kind=KIND, memory_path_=cold_path,
        budget=BUDGET, max_depth=MAX_DEPTH, heuristic=meta_cold["heuristic"],
    )
    rec["cold"] = {"pass": bool(out_cold.get("pass")),
                   "status": out_cold.get("status"),
                   "outcome": out_cold.get("outcome"),
                   "duration_s": round(time.time() - t0, 3),
                   "scan_duration_s": (out_cold.get("steps", {}).get("scan") or {}).get("duration_s")}

    # ---- WARM (target content, memory seeded by TEACH) ----
    env_warm, meta_warm = build_env(goal, seed_contents={"data.txt": TARGET_SEED}, limit=8)
    t0 = time.time()
    out_warm = pa.run(
        env_warm, goal, env_warm.action_names(),
        goal_predicate=meta_warm["is_goal"], env_kind=KIND,
        memory_path_=teach_mem, budget=BUDGET, max_depth=MAX_DEPTH,
        heuristic=meta_warm["heuristic"],
    )
    warm_steps = out_warm.get("steps") or {}
    rec["warm"] = {"pass": bool(out_warm.get("pass")),
                   "status": out_warm.get("status"),
                   "outcome": out_warm.get("outcome"),
                   "memory_replay": warm_steps.get("memory_replay"),
                   "warm_walk": warm_steps.get("warm_walk"),
                   "duration_s": round(time.time() - t0, 3)}

    # ---- CONTROL (same content as TEACH, warm) ----
    env_ctl, meta_ctl = build_env(goal, seed_contents={"data.txt": CONTROL_SEED}, limit=8)
    t0 = time.time()
    out_ctl = pa.run(
        env_ctl, goal, env_ctl.action_names(),
        goal_predicate=meta_ctl["is_goal"], env_kind=KIND,
        memory_path_=teach_mem, budget=BUDGET, max_depth=MAX_DEPTH,
        heuristic=meta_ctl["heuristic"],
    )
    ctl_steps = out_ctl.get("steps") or {}
    rec["control"] = {"pass": bool(out_ctl.get("pass")),
                      "status": out_ctl.get("status"),
                      "outcome": out_ctl.get("outcome"),
                      "memory_replay": ctl_steps.get("memory_replay"),
                      "duration_s": round(time.time() - t0, 3)}

    # ---- Priors-only memory (no fresh instances offered) -> content-B replay ----
    # No admitted rule is ever saved; only the learned model is persisted.
    # Run content B against that priors-only memory: NOT_served by the rule
    # (no rule), carried model walked on content B, honest outcome recorded.
    prior_only_mem = tmp / "priors_only_memory.json"
    env_po, meta_po = build_env(goal, seed_contents={"data.txt": TEACH_SEED}, limit=8)
    out_po = pa.run(
        env_po, goal, env_po.action_names(),
        goal_predicate=meta_po["is_goal"], env_kind=KIND,
        memory_path_=prior_only_mem, budget=BUDGET, max_depth=MAX_DEPTH,
        heuristic=meta_po["heuristic"],
    )

    env_bw, meta_bw = build_env(goal, seed_contents={"data.txt": TARGET_SEED}, limit=8)
    t0 = time.time()
    out_bw = pa.run(
        env_bw, goal, env_bw.action_names(),
        goal_predicate=meta_bw["is_goal"], env_kind=KIND,
        memory_path_=prior_only_mem, budget=BUDGET, max_depth=MAX_DEPTH,
        heuristic=meta_bw["heuristic"],
    )
    bw_steps = out_bw.get("steps") or {}
    rec["carried_model"] = {
        "pass": bool(out_bw.get("pass")),
        "status": out_bw.get("status"),
        "outcome": out_bw.get("outcome"),
        "memory_replay": bw_steps.get("memory_replay"),
        "warm_walk": bw_steps.get("warm_walk"),
        "priors_in_memory": bool((out_po.get("steps") or {}).get("save_priors", {})),
        "save_priors": (out_po.get("steps") or {}).get("save_priors"),
        "duration_s": round(time.time() - t0, 3),
    }

    for e in (env_teach, env_cold, env_warm, env_ctl, *fresh_instances,
              env_po, env_bw):
        try:
            e.close()
        except Exception:
            pass
    results.append(rec)


def main():
    results = []
    for spec in GOALS:
        run_case(spec["name"], spec["goal"], results)
    print(json.dumps({"cases": results}, indent=2))
    out = Path("/tmp/unseen_zip_bzip2_probe_result.json")
    out.write_text(json.dumps({"cases": results}, indent=2))
    print("\nwrote", out)


if __name__ == "__main__":
    main()
