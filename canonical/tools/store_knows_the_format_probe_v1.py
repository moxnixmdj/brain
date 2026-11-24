#!/usr/bin/env python3
"""The store already knows this format, so the scan is not needed.

WHAT THIS MEASURES
------------------
A stored contract used to fire only when the goal looked familiar: the same plan,
or the same family. Ask for a format it can produce, under a name it was never
taught, and the loop fell into a full scan -- re-deriving, by execution, something
it already knew.

Stage A teaches `out.gz` once (with fresh instances, so admission is real).
Stage B asks for `backup.gz`, with the source renamed and in a different
directory. Nothing in the store names `backup.gz`.

  B with the store    -> the contract is bound to the new roles and the effect is
                         verified before any scan happens
  B with an empty     -> the loop scans, as it must, and the numbers show what
  store                  the store saved

WHAT THIS DOES NOT CLAIM
------------------------
One format family, one machine, producer-run. The comparison is a scan-off versus
scan-on measurement, not a benchmark score.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import os_isolation_v1 as isolation

SCHEMA = "PROJECT_BRAIN_STORE_KNOWS_THE_FORMAT_V1"

_DRIVER = r'''
import json, pathlib, shutil, sys
sys.path.insert(0, "/opt/brain")

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import effect_oracle_v1 as oracle
from canonical.swe_kernel import perfect_algorithm_v1 as pa

base = pathlib.Path("/state/knows_format")
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True, exist_ok=True)
memory = str(base / "memory.json")
empty = str(base / "empty.json")
programs = [p for p in ("gzip", "xz", "bzip2") if shutil.which(p)]
SEED = "the store knows this format\n"


def build(root, source_name, target, goal):
    root.mkdir(parents=True, exist_ok=True)
    (root / source_name).write_text(SEED)
    env = cenv.ComputerEnv(root=root, seed={source_name: SEED.encode()})
    for program in programs:
        for name, fn in cenv.program_actions(env, programs=[program], target=target,
                                             goal=goal):
            env.register([(name, fn)])
    for name, fn in (("copy_input",
                      lambda e: shutil.copyfile(e.root / source_name,
                                                e.root / "copy.txt") or True),):
        env.register([(name, fn)])
    return env


def run(env, goal, source_name, memory_path, instances=None, tag=""):
    check = oracle.oracle_from_goal(goal, programs=programs)
    receipt = pa.run(env, goal, env.action_names,
                     goal_predicate=lambda s: goal.split(" into ")[-1] + ":" in str(s),
                     goal_family="compress", env_kind="posix_dir",
                     memory_path_=memory_path, budget=12, max_depth=3, seed=5,
                     unseen_instances=instances,
                     fresh_act=(lambda i, a: i.act(a)) if instances else None,
                     fresh_state=(lambda i: i.state()) if instances else None,
                     fresh_reset=(lambda i: i.reset()) if instances else None,
                     goal_check=check, effect_contract=check.contract)
    steps = receipt.get("steps") or {}
    return {"tag": tag, "status": receipt.get("status"),
            "duration_s": receipt.get("duration_s"),
            "scanned": (steps.get("scan") or {}).get("states_seen"),
            "composition": (steps.get("composition") or {}).get("status"),
            "replay": (steps.get("memory_replay") or {}).get("status"),
            "plan": (steps.get("plan") or {}).get("plan")}


# ---- A: one exposure ---------------------------------------------------------
lesson_env = build(base / "a", "input.txt", "out.gz", "compress the input into out.gz")
fresh = [build(base / ("a-fresh-%d" % i), "input.txt", "out.gz",
               "compress the input into out.gz") for i in range(2)]
lesson = run(lesson_env, "compress the input into out.gz", "input.txt", memory,
             instances=fresh, tag="A learn out.gz")

# ---- B: a name the store has never seen, with and without the store ----------
def held_out(memory_path, tag):
    env = build(base / tag, "report.txt", "backup.gz", "pack the input into backup.gz")
    return run(env, "pack the input into backup.gz", "report.txt", memory_path, tag=tag)


with_store = held_out(memory, "b-with-store")
without = held_out(empty, "b-without-store")

# ---- the same store with the raw plan trace removed, operators kept ----------
# The brief's ablation: generalized entries versus raw traces. If the operator
# alone still reaches the goal without a scan, the trace was never the asset.
store = pa.load_memory(memory)
# keep every top-level key: a filtered store that loses its schema is not the
# same store, it is an empty one (measured the hard way)
operators_only = dict(store)
operators_only["rules"] = [r for r in (store.get("rules") or [])
                           if str(r.get("kind")) == "operator"]
operator_path = str(base / "operators_only.json")
pathlib.Path(operator_path).write_text(json.dumps(operators_only, indent=2))
operators_only_run = held_out(operator_path, "b-operators-only")

print(json.dumps({
    "lesson": lesson,
    "with_store": with_store,
    "without_store": without,
    "operators_only": operators_only_run,
    "memory_rules": [(r.get("program"), r.get("output_name"))
                     for r in (pa.load_memory(memory).get("rules") or [])],
}, default=str))
'''


def measure(*, keep: str | None = None) -> dict[str, Any]:
    probe = isolation.probe()
    base = pathlib.Path(keep) if keep else pathlib.Path(
        tempfile.mkdtemp(prefix="brain-knows-format-"))
    work, state = base / "work", base / "state"
    work.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    (base / "driver.py").write_text(_DRIVER, encoding="utf-8")
    try:
        result = isolation.run(
            [sys.executable, "/opt/probe/driver.py"], work_dir=work, budget_s=600.0,
            env={"PYTHONPATH": "/opt/brain"},
            extra_ro=[[str(pathlib.Path(__file__).resolve().parents[2] / "canonical"),
                       "/opt/brain/canonical"], [str(base), "/opt/probe"]],
            extra_rw=[[str(state), "/state"]])
        payload: dict[str, Any] = {}
        if result.get("stdout"):
            try:
                payload = json.loads(result["stdout"].strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError):
                payload = {"parse": "FAILED", "raw": result["stdout"][-1500:]}
        if not payload:
            payload = {"parse": "EMPTY", "stderr": (result.get("stderr") or "")[-1500:]}
        return {"schema": SCHEMA, "isolation": {"verdict": probe.get("verdict")},
                "isolated_run": {"ok": result.get("ok"),
                                 "isolated": result.get("isolated")},
                "result": payload,
                "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"}
    finally:
        if not keep:
            shutil.rmtree(base, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", default=None)
    parser.add_argument("--keep", default=None)
    args = parser.parse_args(argv)
    report = measure(keep=args.keep)
    body = report.get("result") or {}
    print("isolation:", report["isolation"]["verdict"])
    for key in ("lesson", "with_store", "operators_only", "without_store"):
        row = body.get(key) or {}
        print("  %-16s %-34s %ss scanned=%s" % (
            key, row.get("status"), row.get("duration_s"), row.get("scanned")))
    print("  memory:", body.get("memory_rules"))
    if args.json:
        pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.json).write_text(json.dumps(report, indent=2, default=str),
                                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
