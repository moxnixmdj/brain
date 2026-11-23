#!/usr/bin/env python3
"""Mass-observation probe: 12 disjoint-start cases, single-experience warm transfer (2026-11-23).

Extends unseen_towers_probe_20261123.py from 3 cases to 12, all with the same
goal peg (peg 1) but DISTINCT source and target start arrangements, across both
directions (classic<->mixed) plus identical-shape controls. Every case runs the
full loop honestly through pa.run:

  TEACH   solve the source instance with admission on fresh variants -> rule persisted
  COLD    solve the target instance with an empty store
  WARM    solve the target instance with the memory seeded by TEACH   (single-experience transfer)

Metrics per case: teach/warm/cold status + outcome + pass; warm zero-scan split
(rule replay / carried-model walk / full scan); warm walk counters when carried.

Authority NONE. Producer-run sandbox mass observation, $0, zero model calls,
cold scan trials capped at the same BUDGET as the 3-case probe.
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

from unseen_towers_probe_20261123 import (
    TowersEnv, ACTIONS, heuristic_peg, run_pa, fresh_tmp, BUDGET,
)

# (id, source, target) — disjoint start arrangements, same goal peg "1".
CLASSIC = ((), (), (1, 2, 3))
MIXED_1 = ((), (1,), (2, 3))
MIXED_2 = ((), (1, 2), (3,))
MIXED_3 = ((1,), (), (2, 3))
MIXED_4 = ((1, 2), (3,), ())
MIXED_5 = ((1,), (), (2, 3))  # alias kept explicit for symmetric naming
SINGLE_EACH = ((1,), (2,), (3,))
CASES = [
    ("classic_to_mixed1",  CLASSIC, MIXED_1),
    ("classic_to_mixed2",  CLASSIC, MIXED_2),
    ("classic_to_mixed3",  CLASSIC, MIXED_3),
    ("mixed1_to_classic",  MIXED_1, CLASSIC),
    ("mixed1_to_mixed2",   MIXED_1, MIXED_2),
    ("mixed2_to_classic",  MIXED_2, CLASSIC),
    ("mixed2_to_mixed1",   MIXED_2, MIXED_1),
    ("mixed1_to_mixed3",   MIXED_1, MIXED_3),
    ("mixed3_to_classic",  MIXED_3, CLASSIC),
    ("mixed3_to_mixed1",   MIXED_3, MIXED_1),
    ("identical_mixed2",   MIXED_2, MIXED_2),  # identical shape control
    ("identical_classic",  CLASSIC, CLASSIC),  # identical shape control
]


def main():
    results = []
    for name, src, tgt in CASES:
        rec = {"case": name, "source": src, "target": tgt}

        # ---- TEACH ----
        mem_path, _ = fresh_tmp()
        env_src = TowersEnv(goal_peg="1", initial=src)
        fresh = [TowersEnv(goal_peg="1", initial=src) for _ in range(2)]
        t0 = time.time()
        out_teach = run_pa(env_src, "park all disks on peg 1", ACTIONS,
                           goal_predicate=env_src.is_goal,
                           heuristic=lambda obs: heuristic_peg(obs, "1"),
                           goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                           memory_path=mem_path, budget=BUDGET, max_depth=12,
                           unseen_instances=fresh)
        rec["teach"] = {"pass": bool(out_teach.get("pass")),
                       "status": out_teach.get("status"),
                       "admit_verdict": (out_teach.get("steps") or {}).get("admit", {}).get("verdict"),
                       "rule_persisted": (out_teach.get("steps") or {}).get("save", {}).get("status"),
                       "duration_s": round(time.time() - t0, 3)}

        # ---- COLD ----
        cold_path, _ = fresh_tmp()
        env_cold = TowersEnv(goal_peg="1", initial=tgt)
        t0 = time.time()
        out_cold = run_pa(env_cold, "park all disks on peg 1", ACTIONS,
                          goal_predicate=env_cold.is_goal,
                          heuristic=lambda obs: heuristic_peg(obs, "1"),
                          goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                          memory_path=cold_path, budget=BUDGET, max_depth=12)
        cold_dur = time.time() - t0
        rec["cold"] = {"pass": bool(out_cold.get("pass")),
                      "duration_s": round(cold_dur, 3),
                      "status": out_cold.get("status"),
                      "plan_length": ((out_cold.get("steps") or {}).get("plan") or {}).get("plan_length"),
                      "scan_states": (out_cold.get("steps") or {}).get("scan", {}).get("states_seen"),
                      "scan_transitions": (out_cold.get("steps") or {}).get("scan", {}).get("transitions_seen")}

        # ---- WARM (same store as TEACH) ----
        env_warm = TowersEnv(goal_peg="1", initial=tgt)
        t0 = time.time()
        out_warm = run_pa(env_warm, "park all disks on peg 1", ACTIONS,
                          goal_predicate=env_warm.is_goal,
                          heuristic=lambda obs: heuristic_peg(obs, "1"),
                          goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                          memory_path=mem_path, budget=BUDGET, max_depth=12)
        warm_dur = time.time() - t0
        steps_w = out_warm.get("steps") or {}
        scan_w = steps_w.get("scan")
        walk_w = steps_w.get("warm_walk")
        rec["warm"] = {"pass": bool(out_warm.get("pass")),
                      "status": out_warm.get("status"),
                      "outcome": out_warm.get("outcome"),
                      "duration_s": round(warm_dur, 3),
                      "priors_used": (scan_w or {}).get("priors_used") or (walk_w or {}).get("priors_used"),
                      "priors_stale_discarded": (scan_w or {}).get("priors_stale_discarded"),
                      "walk_counters": (walk_w or {}).get("counters"),
                      "walk_max_act_calls": (walk_w or {}).get("max_act_calls"),
                      "memory_replay_status": (steps_w.get("memory_replay") or {}).get("status")}
        rec["warm_zero_scan"] = walk_w is not None or (scan_w is None and out_warm.get("outcome") == "INSTANT_RECALL")
        rec["warm_path"] = ("rule_replay" if steps_w.get("memory_replay", {}).get("status") == "PASS__REPLAY_REACHED_GOAL" else
                           "carried_walk" if walk_w else
                           "full_scan")
        results.append(rec)
        print(f"case={name}  teach={rec['teach']['status']}({rec['teach']['admit_verdict']})  "
              f"cold={rec['cold']['status']}  warm={rec['warm']['outcome']} [{rec['warm_path']}] "
              f"({rec['warm']['duration_s']}s)")

    # ---- summary ----
    print()
    print("=== MASS-OBSERVATION SUMMARY ===")
    n = len(results)
    teach_pass = sum(1 for r in results if r["teach"]["pass"])
    cold_pass = sum(1 for r in results if r["cold"]["pass"])
    warm_pass = sum(1 for r in results if r["warm"]["pass"])
    warm_zero_scan = sum(1 for r in results if r["warm_zero_scan"])
    warm_rule = sum(1 for r in results if r["warm_path"] == "rule_replay")
    warm_walk = sum(1 for r in results if r["warm_path"] == "carried_walk")
    warm_scan = sum(1 for r in results if r["warm_path"] == "full_scan")
    cross_identical = sum(1 for r in results if r["source"] == r["target"])
    print(f"cases: {n}  teach PASS: {teach_pass}/{n}  cold PASS: {cold_pass}/{n}")
    print(f"warm PASS: {warm_pass}/{n}  zero-scan: {warm_zero_scan}/{n}  "
          f"(rule replay {warm_rule}, carried walk {warm_walk}, full scan {warm_scan})")
    total_warm_s = sum(r["warm"]["duration_s"] for r in results)
    total_cold_s = sum(r["cold"].get("plan_length") or 0 for r in results)  # not wall time
    total_cold_wall = sum(r["cold"].get("duration_s") or 0.0 for r in results)
    print(f"warm total wall: {total_warm_s:.2f}s (12 cases)  | cold total wall (same 12 cases): {total_cold_wall:.2f}s  | controls: {cross_identical}")
    print(f"warm counters: {[(r['case'], r['warm']['walk_counters']) for r in results if r['warm']['walk_counters']]}")

    with open("/tmp/mass_unseen_probe_result.json", "w") as f:
        json.dump({"schema": "MASS_UNSEEEN_TOWERS_V1",
                   "cases": results}, f, indent=2, default=str)
    print("\nfull receipt: /tmp/mass_unseen_probe_result.json")


if __name__ == "__main__":
    main()
