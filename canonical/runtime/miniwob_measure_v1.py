"""Measure one policy on one sample, with the null-actuator gate applied.

    python3 canonical/runtime/miniwob_measure_v1.py --sample /tmp/r130_sample.json \
            --run-id r137 --policy planner_v3

Writes three things:
    canonical/governance/run_ledger_v1.jsonl          one row per (run, task)
    /tmp/miniwob_validity_<n>.json                    cached null-actuator verdicts
    stdout                                            the tally, both raw and gated

The gate matters. `click-test` and `use-colorwheel-2` both pass 100% of the time on a
policy that clicks Submit and touches nothing else. Counting those as successes makes a
policy look 2 tasks better than it is, on a sample of 40.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


HERE = os.path.dirname(os.path.abspath(__file__))
# Root the package. `goal_verb_decomposition_v1` imports a sibling by absolute package path
# inside decompose(); without this, every goal that mentions a colour raises, the exception
# escapes the episode, and the run reports a capability loss that is really an import bug.
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
M = _load("miniwob_actuator_v1", os.path.join(HERE, "miniwob_actuator_v1.py"))
D = _load("goal_verb_decomposition_v1", os.path.join(HERE, "goal_verb_decomposition_v1.py"))
L = _load("run_ledger_v1", os.path.join(HERE, "run_ledger_v1.py"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--policy", default="planner")
    ap.add_argument("--null-episodes", type=int, default=6)
    ap.add_argument("--validity-cache", default="/tmp/miniwob_validity.json")
    ap.add_argument("--ledger", default=None)
    a = ap.parse_args()

    tasks = json.load(open(a.sample))
    act = M.Actuator()

    cache: dict = {}
    if os.path.exists(a.validity_cache):
        try:
            cache = json.load(open(a.validity_cache))
        except Exception:
            cache = {}
    missing = [t for t in tasks if t not in cache]
    print("validity: %d cached, %d to probe" % (len(cache), len(missing)), flush=True)
    for i, t in enumerate(missing, 1):
        cache[t] = M.null_actuator(act, t, a.null_episodes)
        print("  [%d/%d] %-26s %-16s rate=%.2f raw=%s"
              % (i, len(missing), t, cache[t]["verdict"], cache[t]["rate"], cache[t]["raw"]),
              flush=True)
        if i % 5 == 0:
            json.dump(cache, open(a.validity_cache, "w"), indent=1)

    json.dump(cache, open(a.validity_cache, "w"), indent=1)
    invalid = [t for t in tasks if cache[t]["verdict"] == "REWARDS_INACTION"]

    print("\nrunning policy %s on %d tasks (%d invalid excluded)"
          % (a.policy, len(tasks), len(invalid)), flush=True)

    def record(run_id, policy, task, success, **kw):
        L.record(run_id, policy, task, success, path=a.ledger, **kw)

    rows = M.run_sample(act, tasks, D.decompose, valid=cache, record=record,
                        run_id=a.run_id, policy=a.policy)
    act.close()

    tally = M.tally(rows)
    print("\n=== TALLY ===")
    print(json.dumps(tally, indent=2))
    print("\npassed but INVALID (lottery):", [r["task"] for r in rows
                                             if r["success"] and r["invalid_task"]])
    print("counted passes:", [r["task"] for r in rows if r["counts"]])
    print("failed:", [r["task"] for r in rows if not r["success"]])
    for r in rows:
        if r["status"] in ("NOT_IMPLEMENTED", "REFUSED"):
            print("  %-12s %-26s %s" % (r["status"], r["task"], r["action"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
