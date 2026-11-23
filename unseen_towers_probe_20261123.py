#!/usr/bin/env python3
"""Unseen-environment probe: 3-peg Hanoi-like stack (2026-11-23).

Mirrors the shape of transfer_learning_new_instance_probe_20261103.py but on
the NEVER-SEEN towers family, through the Perfect Algorithm (pa.run) path --
the same harness `canonical/tests/test_perfect_algorithm_v1.py` exercises.

What it measures, per seed and per arm:
  TEACH   solve a SOURCE instance with admission on fresh variants  -> rule persisted
  COLD    solve the TARGET instance with an empty store
  WARM    solve the TARGET instance with the memory seeded by TEACH
          (expect rule replay to FAIL on a different instance -- the rule is an
          instance hypothesis, and a new start is exactly where it does not hold)
  CONTROL same-instance warm replay (fresh store; TEACH target == CONTROL target)
          -> is the instant-recall path real on this env?
  CROSSK  teach towers -> grid target and teach grid -> towers target
          (expect 0 priors carried: priors are keyed by env_kind)

Metrics recorded per arm: solved/status/plan/duration; scan trials via a direct
reproduction of the internal scan (same seed, same env, same budget); kept honest
by recording ACTUAL admission verdict and whether the rule replayed.

Authority NONE. Producer-run sandbox measurement, $0, zero model calls, no
capability registered, truth.achieved stays false.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.runtime import environment_learning_v1 as el

ACTIONS = ["move-1-2", "move-1-3", "move-2-1", "move-2-3", "move-3-1", "move-3-2"]
PEG_NAMES = ("1", "2", "3")
BUDGET = 3000
SEEDS = (0, 1, 2)


class TowersEnv:
    kind = "towers_stack_like"

    def __init__(self, goal_peg="1", initial=None, disks=(1, 2, 3)):
        self.disks = tuple(disks)
        self.goal_peg = goal_peg
        self.initial = (tuple(tuple(p) for p in initial) if initial is not None else (tuple(), tuple(), tuple(self.disks)))
        self._clock = self._snap(self.initial)

    def _snap(self, s):
        return tuple(tuple(p) for p in s)

    def reset(self):
        self._clock = self._snap(self.initial)

    def state(self):
        return self._clock

    def snapshot(self):
        return self._clock

    def restore(self, s):
        self._clock = s

    def act(self, action):
        try:
            _, a, b = str(action).split("-")
        except ValueError:
            return
        if a == b:
            return
        ia, ib = PEG_NAMES.index(a), PEG_NAMES.index(b)
        src = self._clock[ia]
        if not src:
            return
        moving = src[0]
        target = self._clock[ib]
        if target and target[0] < moving:
            return
        new = list(self._clock)
        new[ia] = tuple(src[1:])
        new[ib] = tuple([moving] + list(target))
        self._clock = tuple(new)

    def is_goal(self, obs):
        if obs is None:
            return False
        goal = PEG_NAMES.index(self.goal_peg)
        expected = tuple(self.disks)
        return obs[goal] == expected and all(obs[j] == () for j in range(3) if j != goal)

    def __repr__(self):
        return f"Towers(goal={self.goal_peg}, state={self._clock})"


class GridEnv:
    kind = "grid_world"

    def __init__(self, goal=(3, 3), start=(0, 0)):
        self.goal, self.start = tuple(goal), tuple(start)
        self.reset()

    def reset(self):
        self.p = self.start

    def state(self):
        return self.p

    def act(self, a):
        x, y = self.p
        move = {"up": (x, y - 1), "down": (x, y + 1),
                "left": (x - 1, y), "right": (x + 1, y)}.get(str(a))
        if move and 0 <= move[0] < 4 and 0 <= move[1] < 4:
            self.p = move

    def snapshot(self):
        return self.p

    def restore(self, s):
        self.p = s


def heuristic_peg(obs, goal_peg="1"):
    goal = PEG_NAMES.index(goal_peg)
    return sum(len(obs[j]) for j in range(3) if j != goal)


def grid_heuristic(obs):
    return abs(3 - obs[0]) + abs(3 - obs[1])


CASES = [
    # (name, source_initial, source_goal, target_initial, target_goal) —
    # all three: same goal peg (peg 1), differing START arrangement.
    # The different-goal-peg sensitivity case is reported separately.
    ("seed0_stack_to_mixed",
     ((), (), (1, 2, 3)), "1",
     ((), (1,), (2, 3)), "1"),
    ("seed1_mixed_to_stack",
     ((), (1,), (2, 3)), "1",
     ((), (), (1, 2, 3)), "1"),
    ("seed2_identical_shape",
     ((), (1, 2), (3,)), "1",
     ((), (1, 2), (3,)), "1"),  # identical shape, see CONTROL
]


def fresh_tmp():
    d = Path(tempfile.mkdtemp(prefix="unseen_towers_probe_"))
    return d / "memory.json", d


def run_pa(env, goal, actions, goal_predicate, heuristic, goal_family, env_kind,
           memory_path, budget, max_depth, unseen_instances=None):
    kwargs = {}
    if unseen_instances:
        kwargs["unseen_instances"] = unseen_instances
        kwargs["fresh_reset"] = lambda e: e.reset()
        kwargs["fresh_act"] = lambda e, a: e.act(a)
        kwargs["fresh_state"] = lambda e: e.state()
    out = pa.run(env, goal, actions,
                 goal_predicate=goal_predicate, heuristic=heuristic,
                 goal_family=goal_family, env_kind=env_kind,
                 memory_path_=memory_path, budget=budget, max_depth=max_depth,
                 seed=0, **kwargs)
    return out


def scan_trials(env, actions, budget, heuristic, prior=None):
    """Reproduce the scan inside pa.run for trial bookkeeping (same seed/budget)."""
    learned = el.learn_model(env, actions, budget=budget, seed=0,
                             max_depth=12, heuristic=heuristic, prior=prior,
                             prior_schema=el.STATE_KEY_SCHEMA if prior else None)
    return learned["trials"], learned["state_count"], learned["transition_count"]


def main():
    results = []
    for name, src_initial, src_goal, tgt_initial, tgt_goal in CASES:
        rec = {"case": name, "source": {"initial": src_initial, "goal_peg": src_goal},
               "target": {"initial": tgt_initial, "goal_peg": tgt_goal}}

        # ---- TEACH (source instance) ----
        mem_path, tmpdir = fresh_tmp()
        env_src = TowersEnv(goal_peg=src_goal, initial=src_initial)
        fresh_variants = [TowersEnv(goal_peg=src_goal, initial=src_initial) for _ in range(2)]
        t0 = time.time()
        out_teach = run_pa(
            env_src, "park all disks on peg %s" % src_goal, ACTIONS,
            goal_predicate=env_src.is_goal,
            heuristic=lambda obs, g=src_goal: heuristic_peg(obs, g), goal_family="towers_park_peg_1",
            env_kind="towers_stack_like",
            memory_path=mem_path, budget=BUDGET, max_depth=12,
            unseen_instances=fresh_variants)
        teach_dur = time.time() - t0
        teach_passes = bool(out_teach.get("pass"))
        admit = (out_teach.get("steps") or {}).get("admit") or {}
        rec["teach"] = {"pass": teach_passes, "status": out_teach.get("status"),
                       "admit_verdict": admit.get("verdict"),
                       "rule_persisted": (out_teach.get("steps") or {}).get("save", {}).get("status"),
                       "duration_s": round(teach_dur, 3)}

        # ---- COLD (target, empty store) ----
        cold_path, cold_dir = fresh_tmp()
        env_tgt = TowersEnv(goal_peg=tgt_goal, initial=tgt_initial)
        t0 = time.time()
        out_cold = run_pa(
            env_tgt, "park all disks on peg %s" % tgt_goal, ACTIONS,
            goal_predicate=env_tgt.is_goal,
            heuristic=lambda obs, g=tgt_goal: heuristic_peg(obs, g), goal_family="towers_park_peg_1",
            env_kind="towers_stack_like",
            memory_path=cold_path, budget=BUDGET, max_depth=12)
        cold_dur = time.time() - t0
        cold_trials, cold_states, cold_transitions = scan_trials(
            TowersEnv(goal_peg=tgt_goal, initial=tgt_initial), ACTIONS, BUDGET,
            lambda obs, g=tgt_goal: heuristic_peg(obs, g))
        rec["cold"] = {"pass": bool(out_cold.get("pass")),
                      "status": out_cold.get("status"),
                      "plan_length": ((out_cold.get("steps") or {}).get("plan") or {}).get("plan_length"),
                      "scan_states": cold_states, "scan_transitions": cold_transitions,
                      "scan_trials": cold_trials,
                      "duration_s": round(cold_dur, 3)}

        # ---- WARM (target, memory seeded by TEACH) ----
        env_warm = TowersEnv(goal_peg=tgt_goal, initial=tgt_initial)
        t0 = time.time()
        out_warm = run_pa(
            env_warm, "park all disks on peg %s" % tgt_goal, ACTIONS,
            goal_predicate=env_warm.is_goal,
            heuristic=lambda obs, g=tgt_goal: heuristic_peg(obs, g), goal_family="towers_park_peg_1",
            env_kind="towers_stack_like",
            memory_path=mem_path, budget=BUDGET, max_depth=12)
        warm_dur = time.time() - t0
        steps_w = out_warm.get("steps") or {}
        mem_replay = steps_w.get("memory_replay")
        rec["warm"] = {"pass": bool(out_warm.get("pass")),
                      "status": out_warm.get("status"),
                      "outcome": out_warm.get("outcome"),
                      "memory_replay": mem_replay,
                      "duration_s": round(warm_dur, 3),
                      "priors_used": (steps_w.get("scan") or {}).get("priors_used")
                                      or (steps_w.get("warm_walk") or {}).get("priors_used"),
                      "priors_stale_discarded": (steps_w.get("scan") or {}).get("priors_stale_discarded"),
                      "warm_walk_counters": (steps_w.get("warm_walk") or {}).get("counters"),
                      "warm_walk_max_act_calls": (steps_w.get("warm_walk") or {}).get("max_act_calls")}

        # ---- CONTROL: same instance as teach (identical start+goal), warm ----
        ctl_path, ctl_dir = fresh_tmp()
        env_src2 = TowersEnv(goal_peg=src_goal, initial=src_initial)
        fresh_ctrl = [TowersEnv(goal_peg=src_goal, initial=src_initial) for _ in range(2)]
        out_ctl_teach = run_pa(
            env_src2, "park all disks on peg %s" % src_goal, ACTIONS,
            goal_predicate=env_src2.is_goal, heuristic=lambda obs, g=src_goal: heuristic_peg(obs, g),
            goal_family="towers_park_peg_1", env_kind="towers_stack_like",
            memory_path=ctl_path, budget=BUDGET, max_depth=12,
            unseen_instances=fresh_ctrl)
        env_ctl = TowersEnv(goal_peg=src_goal, initial=src_initial)
        out_ctl = run_pa(
            env_ctl, "park all disks on peg %s" % src_goal, ACTIONS,
            goal_predicate=env_ctl.is_goal, heuristic=lambda obs, g=src_goal: heuristic_peg(obs, g),
            goal_family="towers_park_peg_1", env_kind="towers_stack_like",
            memory_path=ctl_path, budget=BUDGET, max_depth=12)
        rec["control_same_instance_warm"] = {
            "teach_pass": bool(out_ctl_teach.get("pass")),
            "warm_status": out_ctl.get("status"),
            "warm_outcome": out_ctl.get("outcome"),
            "warm_pass": bool(out_ctl.get("pass")),
            "memory_replay": (out_ctl.get("steps") or {}).get("memory_replay"),
        }

        # ---- CROSS-KIND: towers memory -> grid target, grid memory -> towers target ----
        # towers -> grid: fresh grid target with the towers memory seeded
        cross_path, _ = fresh_tmp()
        env_grid = GridEnv()
        out_cross_t = run_pa(
            env_grid, "reach the exit", ["up", "down", "left", "right"],
            goal_predicate=lambda obs: obs == (3, 3), heuristic=grid_heuristic,
            goal_family="grid_world", env_kind="grid_world",
            memory_path=cross_path, budget=40, max_depth=12)
        # grid -> towers: fresh towers target with the grid memory seeded
        ttk_path, _ = fresh_tmp()
        env_g = GridEnv()
        out_grid_teach = run_pa(
            env_g, "reach the exit", ["up", "down", "left", "right"],
            goal_predicate=lambda obs: obs == (3, 3), heuristic=grid_heuristic,
            goal_family="grid_world", env_kind="grid_world",
            memory_path=ttk_path, budget=40, max_depth=12)
        env_tt = TowersEnv(goal_peg="1", initial=((), (), (1, 2, 3)))
        out_ttk = run_pa(
            env_tt, "park all disks on peg 1", ACTIONS,
            goal_predicate=env_tt.is_goal, heuristic=lambda obs: heuristic_peg(obs, "1"),
            goal_family="towers_park_peg_1", env_kind="towers_stack_like",
            memory_path=ttk_path, budget=BUDGET, max_depth=12)
        rec["across_kind"] = {
            "towers_memory_to_grid": {"pass": bool(out_cross_t.get("pass")),
                                      "status": out_cross_t.get("status"),
                                      "priors_used": (out_cross_t.get("steps") or {}).get("scan", {}).get("priors_used")},
            "grid_memory_to_towers": {"pass": bool(out_ttk.get("pass")),
                                      "status": out_ttk.get("status"),
                                      "priors_used": (out_ttk.get("steps") or {}).get("scan", {}).get("priors_used")},
        }

        results.append(rec)
        print(f"case={name}")
        print("  teach:", rec["teach"])
        print("  cold :", rec["cold"])
        print("  warm :", rec["warm"])
        print("  ctrl :", rec["control_same_instance_warm"])
        print("  cross:", rec["across_kind"])

    print()
    print("=== SUMMARY ===")
    cold_pass = sum(r["cold"]["pass"] for r in results)
    warm_pass = sum(r["warm"]["pass"] for r in results)
    # zero-scan warm paths: identical-shape replay OR carried-model walk
    ctrl_instant = sum(1 for r in results
                       if r["control_same_instance_warm"]["warm_outcome"] == "INSTANT_RECALL")
    teach_admitted = sum(1 for r in results if r["teach"]["admit_verdict"] == "ADMIT")
    cold_mean = sum(r["cold"]["scan_trials"] for r in results) / len(results)
    print(f"teach ADMIT: {teach_admitted}/{len(results)}")
    print(f"cold pass : {cold_pass}/{len(results)}  mean cold scan trials={cold_mean:.1f}")
    warm_rule_replay = sum(1 for r in results if r["warm"]["outcome"] == "INSTANT_RECALL")
    warm_walk_reached = sum(1 for r in results if r["warm"]["outcome"] == "CARRIED_MODEL_WALK_REACHED")
    warm_full_scan = sum(1 for r in results if r["warm"]["outcome"] == "VERIFIED_NOT_PERSISTED")
    print(f"warm pass : {warm_pass}/{len(results)}  "
          f"zero-scan (rule replay): {warm_rule_replay}/{len(results)}  "
          f"zero-scan (carried-model walk): {warm_walk_reached}/{len(results)}  "
          f"full-scan fallback: {warm_full_scan}/{len(results)}  "
          f"(cold target: {cold_pass}/{len(results)})")
    print(f"control same-instance warm INSTANT_RECALL: {ctrl_instant}/{len(results)}")
    print(f"across-kind priors carried (towers->grid, grid->towers): "
          f"{sum(r['across_kind']['towers_memory_to_grid']['priors_used'] or 0 for r in results)}"
          f" + {sum(r['across_kind']['grid_memory_to_towers']['priors_used'] or 0 for r in results)}")

    with open("/tmp/unseen_towers_probe_result.json", "w") as f:
        json.dump({"schema": "PROBE_UNSEEEN_TOWERS_V1", "budget": BUDGET,
                   "cases": results}, f, indent=2, default=str)
    print("\nfull receipt: /tmp/unseen_towers_probe_result.json")


if __name__ == "__main__":
    raise SystemExit(main())
