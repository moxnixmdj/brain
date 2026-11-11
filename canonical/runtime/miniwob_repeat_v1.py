"""Repeated-trial measurement: reach as a distribution, not a point.

    python3 canonical/runtime/miniwob_repeat_v1.py --sample /tmp/r130_sample.json \
            --run-id r140 --policy planner_v3 --reps 5

WHY THIS EXISTS
---------------
r136 through r139 each ran ONE episode per task and reported the percentage of tasks that
passed. Those percentages moved: 11, 11, 7, 15, 15 -- and the movement was not all
capability. Two consecutive runs of identical code on the identical sample disagreed about
four tasks: `use-autocomplete-nodelay` and `drag-cube` passed in one and failed in the next,
`focus-text` and `scroll-text-2` did the reverse.

A single episode per task treats a coin flip as a fact. On 40 tasks where several sit near
p = 0.5, the standard error of the headline is about sqrt(sum p(1-p))/40, which is 2-3
points -- wider than most of the changes this project has been reporting.

So: run every task N times, report each task's pass RATE, and report the reach with a
binomial standard error. A difference smaller than two standard errors is not a difference,
and this module says so rather than leaving it to the reader.

VALIDITY is applied as before: a task whose do-nothing policy passes is excluded from the
gated number and reported separately.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

M = _load("miniwob_actuator_v1", os.path.join(HERE, "miniwob_actuator_v1.py"))
D = _load("goal_verb_decomposition_v1", os.path.join(HERE, "goal_verb_decomposition_v1.py"))
L = _load("run_ledger_v1", os.path.join(HERE, "run_ledger_v1.py"))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval -- correct at small n and at the extremes, unlike normal approx."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--policy", default="planner")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--validity-cache", default="/tmp/miniwob_validity.json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    tasks = json.load(open(a.sample))
    valid = {}
    if os.path.exists(a.validity_cache):
        valid = json.load(open(a.validity_cache))
    invalid = {t for t in tasks if valid.get(t, {}).get("verdict") == "REWARDS_INACTION"}

    act = M.Actuator()
    per: dict[str, dict] = {t: {"passes": 0, "reps": 0, "actions": [], "rewards": []}
                            for t in tasks}

    for rep in range(a.reps):
        print("rep %d/%d" % (rep + 1, a.reps), flush=True)
        for t in tasks:
            try:
                row = M.run_episode(act, t, D.decompose)
                ok = bool(row["success"])
                act_name = str(row.get("action"))
                rew = row.get("reward")
            except Exception as exc:
                ok = False
                act_name = "ERR:%s: %s" % (type(exc).__name__, str(exc)[:80])
                rew = None
            per[t]["reps"] += 1
            per[t]["passes"] += int(ok)
            per[t]["actions"].append(act_name)
            per[t]["rewards"].append(round(rew, 3) if isinstance(rew, (int, float)) else rew)
            L.record(a.run_id, a.policy, t, ok, action=act_name, reward=rew
                     if isinstance(rew, (int, float)) else None,
                     extra={"rep": rep, "invalid": t in invalid})
    act.close()

    counted = [t for t in tasks if t not in invalid]
    total_pass = sum(per[t]["passes"] for t in counted)
    total_obs = sum(per[t]["reps"] for t in counted)
    reach = total_pass / total_obs if total_obs else 0.0
    lo, hi = wilson(total_pass, total_obs)

    print("\n=== PER-TASK PASS RATE (%d reps) ===" % a.reps)
    print("%-26s %6s  %-9s %s" % ("task", "rate", "95% CI", "actions seen"))
    for t in sorted(tasks, key=lambda x: (-per[x]["passes"], x)):
        r = per[t]
        rate = r["passes"] / r["reps"] if r["reps"] else 0.0
        l, h = wilson(r["passes"], r["reps"])
        flag = " EXCLUDED" if t in invalid else ""
        head = "%d/%d" % (r["passes"], r["reps"])
        uniq = []
        for x in r["actions"]:
            if x not in uniq:
                uniq.append(x)
        print("%-26s %6s  %.2f-%.2f  %s%s"
              % (t, head, l, h, "; ".join(u[:28] for u in uniq[:3]), flag))

    print("\n=== REACH (%d valid tasks, %d episodes each) ===" % (len(counted), a.reps))
    print("  valid tasks        : %d of %d" % (len(counted), len(tasks)))
    print("  episodes           : %d" % total_obs)
    print("  passes             : %d" % total_pass)
    print("  reach              : %.4f  (%.1f%%)" % (reach, 100 * reach))
    print("  95%% CI (Wilson)    : %.4f - %.4f  (%.1f%% - %.1f%%)"
          % (lo, hi, 100 * lo, 100 * hi))
    print("  half-width         : +/- %.1f points" % (100 * (hi - lo) / 2))
    unstable = [t for t in counted if 0 < per[t]["passes"] < per[t]["reps"]]
    print("\n  tasks that are NOT deterministic (0 < k < n): %d" % len(unstable))
    for t in unstable:
        print("     %-26s %d/%d" % (t, per[t]["passes"], per[t]["reps"]))

    if a.out:
        json.dump({"run_id": a.run_id, "policy": a.policy, "reps": a.reps,
                   "per_task": per, "invalid": sorted(invalid),
                   "reach": reach, "ci": [lo, hi],
                   "total_pass": total_pass, "total_obs": total_obs},
                  open(a.out, "w"), indent=1)
        print("\nwrote %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
