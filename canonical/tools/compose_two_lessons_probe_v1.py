#!/usr/bin/env python3
"""Two lessons, one format neither of them makes.

WHAT THIS MEASURES
------------------
Measured 2026-11-24: the goal `archive the input into out.tar.gz` is verifiable --
the chain oracle proves a real tar.gz through [gzip, tar] -- and unreachable,
because the only actions the environment offers write a plain tar or a plain
gzip. The loop said OPEN, which was correct and useless.

So: teach the two halves, then ask for the whole.

  stage 1  `archive the input into out.tar`      -- learns tar, admits, saves
  stage 2  `compress the input into out.bin.gz`  -- learns gzip, admits, saves
  stage 3  `archive the input into out.tar.gz`   -- NO action does both

Stage 3 can only succeed by composing the two stored contracts: tar writes an
intermediate, gzip carries it to the final name, and the chain oracle decides
whether the result is really a tar.gz. The judge is external to all of it:
`gzip -dc out.tar.gz | tar -xO` must return the source's bytes exactly.

WHAT THIS DOES NOT CLAIM
------------------------
Not a benchmark, one format family, one machine, producer-run. A composition
that verifies here is a capability with a receipt, not general competence.
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

SCHEMA = "PROJECT_BRAIN_COMPOSED_LESSONS_V1"

_DRIVER = r'''
import json, pathlib, shutil, subprocess, sys
sys.path.insert(0, "/opt/brain")

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import effect_oracle_v1 as oracle
from canonical.swe_kernel import perfect_algorithm_v1 as pa

spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
base = pathlib.Path("/state/lessons")
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True, exist_ok=True)
programs = [p for p in ("tar", "gzip") if shutil.which(p)]
seed = {"input.txt": b"two lessons, composed\n"}
memory = "/state/lessons/memory.json"


def fresh(tag, target, count=2):
    out = []
    for index in range(count):
        root = base / ("%s-fresh-%d" % (tag, index))
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        (root / "input.txt").write_bytes(seed["input.txt"])
        env = cenv.ComputerEnv(root=root, seed=dict(seed))
        for program in programs:
            for name, fn in cenv.program_actions(env, programs=[program],
                                                 target=target, goal=""):
                env.register([(name, fn)])
        out.append(env)
    return out


def lesson(tag, goal, target):
    root = base / ("lesson-" + tag)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    (root / "input.txt").write_bytes(seed["input.txt"])
    env = cenv.ComputerEnv(root=root, seed=dict(seed))
    for program in programs:
        for name, fn in cenv.program_actions(env, programs=[program], target=target,
                                             goal=goal):
            env.register([(name, fn)])
    check = oracle.oracle_from_goal(goal, programs=programs)
    instances = fresh(tag, target)
    receipt = pa.run(env, goal, env.action_names,
                     goal_predicate=lambda s: target + ":" in str(s),
                     goal_family=goal.split()[0], env_kind="posix_dir",
                     memory_path_=memory, budget=12, max_depth=2, seed=7,
                     unseen_instances=instances,
                     fresh_act=lambda i, a: i.act(a),
                     fresh_state=lambda i: i.state(),
                     fresh_reset=lambda i: i.reset(),
                     goal_check=check, effect_contract=check.contract)
    return {"goal": goal, "status": receipt.get("status"),
            "plan": (receipt.get("steps", {}).get("plan") or {}).get("plan"),
            "admit": (receipt.get("steps", {}).get("admit") or {}).get("verdict"),
            "lift": (receipt.get("steps", {}).get("lift") or {}).get("status")}


stages = [lesson("tar", "archive the input into out.tar", "out.tar"),
          lesson("gz", "compress the input into out.gz", "out.gz")]

# ---- the whole, which no action can make -------------------------------------
goal = "archive the input into out.tar.gz"
root = base / "composed"
shutil.rmtree(root, ignore_errors=True)
root.mkdir(parents=True, exist_ok=True)
(root / "input.txt").write_bytes(seed["input.txt"])
env = cenv.ComputerEnv(root=root, seed=dict(seed))
for program in programs:
    for name, fn in cenv.program_actions(env, programs=[program], target="out.tar.gz",
                                         goal=goal):
        env.register([(name, fn)])
offered = list(env.action_names)
check = oracle.oracle_from_goal(goal, programs=programs)
whole = pa.run(env, goal, env.action_names,
               goal_predicate=lambda s: "out.tar.gz:" in str(s),
               goal_family="archive", env_kind="posix_dir", memory_path_=memory,
               budget=12, max_depth=3, seed=7, goal_check=check,
               effect_contract=check.contract)

# the judge: is out.tar.gz really a tar.gz of input.txt?
raw = subprocess.run(["gzip", "-dc", "out.tar.gz"], cwd=str(root), capture_output=True)
inner = subprocess.run(["tar", "-xOf", "-"], cwd=str(root), input=raw.stdout,
                       capture_output=True)
truth = {"gzip_rc": raw.returncode, "tar_rc": inner.returncode,
         "bytes_equal_source": inner.stdout == (root / "input.txt").read_bytes()}

print(json.dumps({
    "stages": stages,
    "composed_goal": goal,
    "offered_actions": offered,
    "status": whole.get("status"),
    "composition": whole.get("steps", {}).get("composition"),
    "truth": truth,
    "memory_rules": [(r.get("program"), r.get("argv_shape"))
                     for r in (pa.load_memory(memory).get("rules") or [])],
}, default=str))
'''


def measure(*, keep: str | None = None) -> dict[str, Any]:
    probe = isolation.probe()
    base = pathlib.Path(keep) if keep else pathlib.Path(
        tempfile.mkdtemp(prefix="brain-composed-lessons-"))
    state = base / "state"
    state.mkdir(parents=True, exist_ok=True)
    work = base / "work"
    work.mkdir(parents=True, exist_ok=True)
    (base / "driver.py").write_text(_DRIVER, encoding="utf-8")
    (base / "spec.json").write_text(json.dumps({"unused": True}), encoding="utf-8")
    try:
        result = isolation.run(
            [sys.executable, "/opt/probe/driver.py", "/opt/probe/spec.json"],
            work_dir=work, budget_s=600.0, env={"PYTHONPATH": "/opt/brain"},
            extra_ro=[[str(pathlib.Path(__file__).resolve().parents[2] / "canonical"),
                       "/opt/brain/canonical"], [str(base), "/opt/probe"]],
            extra_rw=[[str(state), "/state"]])
        payload: dict[str, Any] = {}
        if result.get("stdout"):
            try:
                payload = json.loads(result["stdout"].strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError):
                payload = {"parse": "FAILED", "raw": result["stdout"][-1200:]}
        if not payload:
            payload = {"parse": "EMPTY", "stderr": (result.get("stderr") or "")[-1200:]}
        return {"schema": SCHEMA,
                "isolation": {"verdict": probe.get("verdict")},
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
    for stage in body.get("stages") or []:
        print("  lesson %-28s %s (plan=%s, lift=%s)" % (
            stage.get("goal"), stage.get("status"), stage.get("plan"),
            stage.get("lift")))
    print("  composed %-28s %s" % (body.get("composed_goal"), body.get("status")))
    print("  composition:", json.dumps(body.get("composition"), default=str)[:300])
    print("  truth:", body.get("truth"))
    if args.json:
        pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.json).write_text(json.dumps(report, indent=2, default=str),
                                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
