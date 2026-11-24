#!/usr/bin/env python3
"""Learn a goal in a real computer, inside a real kernel sandbox. Measured.

WHAT THIS ANSWERS
-----------------
Every capability in this repository sat above one refusal:
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`. Not because
the code could not plan, but because nothing could be allowed to act on a
computer until a confinement the kernel enforces existed. This probe is the
first run of the Perfect Algorithm that ACTS -- real programs, real files, a
real subprocess -- with the boundary measured rather than asserted.

The whole run happens inside `os_isolation_v1`: fresh user/mount/pid/net/ipc/uts
namespaces, a read-only system bind, a chroot, and no capabilities in the
payload. The engine is mounted read-only at /opt/brain; the computer under study
is /work; the host is not on the map at all.

WHAT IS MEASURED (three runs, each its own sandbox)
---------------------------------------------------
  A  learn the goal on instance A       -- scan, plan, act, verify, learn, admit
  B  the same goal on a NEW instance with the same file names but different
     bytes, seeded with A's memory       -- does the stored rule replay, or is
     every instance learned again?
  C  the same goal with the input file RENAMED -- does what was stored survive a
     name it was never taught?

B and C are the honest question the owner asked: what exactly is saved, and is
it a generalization or a cache. The receipt reports whichever happens.

WHAT THIS DOES NOT CLAIM
------------------------
Not a benchmark score. Not Terminal-Bench, not OSWorld, not SWE-bench. It is a
producer-run measurement of this engine on this machine, and it says so in
`authority`. A rule admitted here is a hypothesis that survived replay on two
fresh instances; it is not proof of arbitrary competence.

Zero model calls. Zero network. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile
import time
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import os_isolation_v1 as isolation

SCHEMA = "PROJECT_BRAIN_REAL_COMPUTER_LEARNING_V1"
GOAL = "compress the input into out.gz"

# Runs INSIDE the sandbox. It is copied to a read-only mount, never to /work.
_DRIVER = r'''
import json, os, pathlib, shutil, sys
sys.path.insert(0, "/opt/brain")

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import effect_oracle_v1 as oracle
from canonical.swe_kernel import perfect_algorithm_v1 as pa

spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
root = pathlib.Path(spec["root"])
goal = spec["goal"]

programs = [p for p in ("gzip", "bzip2", "xz", "zip") if shutil.which(p)]
env = cenv.ComputerEnv(root=root, seed={k: v.encode() for k, v in spec["seed"].items()})
env.register(cenv.program_actions(env, programs=programs, target="out.gz", goal=goal))


def is_goal(state) -> bool:
    """The thin check: a file with the goal's NAME appeared."""
    return "out.gz:" in str(state)


# The real check: the input's bytes come back out of out.gz through the
# machine's own gzip reader. Computed live, while the world is in front of us.
effect = oracle.compress_oracle("input.txt", "out.gz", programs=programs)


fresh = []
for name in spec.get("fresh_roots") or []:
    fresh_env = cenv.ComputerEnv(root=name, seed={k: v.encode() for k, v in spec["seed"].items()})
    fresh_env.register(cenv.program_actions(fresh_env, programs=programs,
                                            target="out.gz", goal=goal))
    fresh.append(fresh_env)

receipt = pa.run(
    env, goal, env.action_names,
    goal_predicate=is_goal,
    goal_family="compress_to_named_file",
    env_kind="posix_dir",  # one kind: the rule must be able to leave this instance
    memory_path_=spec["memory"],
    budget=int(spec.get("budget", 40)),
    max_depth=4,
    unseen_instances=fresh,
    fresh_act=lambda instance, action: instance.act(action),
    fresh_state=lambda instance: instance.state(),
    fresh_reset=lambda instance: instance.reset(),
    seed=11,
    goal_check=effect,
)
# the goal predicate the learner was given only says "a file called out.gz
# exists". Whether the file IS a gzip of the input is a stricter question, asked
# here so a name-satisfying plan cannot pass as a job done.
truth = {"out_gz_exists": (root / "out.gz").is_file()}
try:
    import gzip
    data = gzip.open(root / "out.gz", "rb").read()
    truth["gzip_ok"] = True
    truth["gzip_matches_input"] = data == (root / "input.txt").read_bytes()
except Exception as error:  # noqa: BLE001 - a wrong artifact is data
    truth["gzip_ok"] = False
    truth["gzip_error"] = type(error).__name__
truth["oracle_verdict"] = (effect.last or {}).get("verdict")
truth["oracle_reader"] = (effect.last or {}).get("reader")
receipt["artifact_truth"] = truth
print(json.dumps({"receipt": receipt, "programs": programs,
                  "listing": env.listing()}, default=str))
'''


def _seed_text(tag: str) -> dict[str, bytes]:
    if tag == "renamed":
        return {"report.txt": b"ledger 2026-11-24: twelve entries, none missing\n"}
    return {"input.txt": (b"brain computer env sample\n" if tag == "a"
                          else b"a different instance entirely\n")}


def _stage(tag: str, state: pathlib.Path, base: pathlib.Path,
           fresh_count: int = 2) -> dict[str, Any]:
    work = base / tag
    work.mkdir(parents=True, exist_ok=True)
    seed = _seed_text(tag if tag != "b" else "b")
    for name, data in seed.items():
        (work / name).write_bytes(data)
    # Fresh instances live in the writable state mount, addressed by their
    # SANDBOX paths: a host path handed to a process inside the chroot names
    # nothing there, and ComputerEnv would silently create it in /tmp instead.
    fresh_roots = []
    for index in range(fresh_count):
        holder = state / ("%s-fresh-%d" % (tag, index))
        holder.mkdir(parents=True, exist_ok=True)
        for name, data in seed.items():
            (holder / name).write_bytes(data)
        fresh_roots.append("/state/" + holder.name)
    driver = base / "driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    memory = state / "memory.json"
    spec_path = base / ("spec-%s.json" % tag)
    spec_path.write_text(json.dumps(
        {"root": "/work", "goal": GOAL, "seed": {k: v.decode("utf-8", "replace")
                                                   for k, v in seed.items()},
         "memory": "/state/memory.json", "fresh_roots": fresh_roots, "budget": 40, "tag": tag}),
        encoding="utf-8")
    started = time.time()
    result = isolation.run(
        [sys.executable, "/opt/probe/driver.py", "/opt/probe/" + spec_path.name],
        work_dir=work, budget_s=600.0,
        env={"PYTHONPATH": "/opt/brain"},
        extra_ro=[[str(pathlib.Path(__file__).resolve().parents[2] / "canonical"),
                   "/opt/brain/canonical"],
                  [str(base), "/opt/probe"]],
        extra_rw=[[str(state), "/state"]],
    )
    elapsed = round(time.time() - started, 3)
    payload: dict[str, Any] = {}
    if result.get("stdout"):
        try:
            payload = json.loads(result["stdout"].strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            payload = {"parse": "FAILED", "raw": result["stdout"][-1500:]}
    if not payload:
        payload = {"parse": "EMPTY", "stderr": (result.get("stderr") or "")[-1500:]}
    return {"tag": tag, "elapsed_s": elapsed, "isolated": result.get("isolated"),
            "refused": result.get("refused"), "payload": payload}


def measure(*, keep: str | None = None) -> dict[str, Any]:
    probe = isolation.probe()
    base = pathlib.Path(keep) if keep else pathlib.Path(
        tempfile.mkdtemp(prefix="brain-real-computer-"))
    state = base / "state"
    state.mkdir(parents=True, exist_ok=True)
    memory = state / "memory.json"
    try:
        stages = [_stage(tag, state, base) for tag in ("a", "b", "renamed")]
        stored = {}
        if memory.is_file():
            try:
                stored = json.loads(memory.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                stored = {"refused": "MEMORY_CORRUPT"}
        return {
            "schema": SCHEMA,
            "goal": GOAL,
            "isolation_probe": {"verdict": probe.get("verdict"),
                                "reasons": probe.get("reasons"),
                                "caps_after_drop": probe.get("caps_after_drop")},
            "stages": stages,
            "memory": {
                "path": str(memory),
                "rules": len((stored.get("rules") or [])),
                "rule_scopes": [r.get("scope") for r in (stored.get("rules") or [])],
                "prior_kinds": sorted((stored.get("priors") or {}).keys()),
            },
            "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        }
    finally:
        if not keep:
            shutil.rmtree(base, ignore_errors=True)


def _summary(report: dict[str, Any]) -> str:
    lines = [f"isolation: {report['isolation_probe']['verdict']}"]
    for stage in report.get("stages", []):
        receipt = (stage.get("payload") or {}).get("receipt") or {}
        steps = receipt.get("steps") or {}
        scan = steps.get("scan") or {}
        plan = steps.get("plan") or {}
        admit = steps.get("admit") or {}
        lines.append(
            "  {tag:8s} isolated={iso} {sec:7.2f}s status={status} "
            "states={states} transitions={trans} plan={plan} admit={admit}".format(
                tag=stage["tag"], iso=stage.get("isolated"), sec=stage["elapsed_s"],
                status=receipt.get("status"), states=scan.get("states_seen"),
                trans=scan.get("transitions_seen"),
                plan=(plan.get("plan") or receipt.get("plan")),
                admit=admit.get("verdict")))
    lines.append("  memory: %d rule(s), priors=%s" % (
        report["memory"]["rules"], report["memory"]["prior_kinds"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", default=None, help="write the receipt here")
    parser.add_argument("--keep", default=None, help="keep the scratch tree here")
    args = parser.parse_args(argv)
    report = measure(keep=args.keep)
    if args.json:
        pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.json).write_text(json.dumps(report, indent=2, default=str),
                                           encoding="utf-8")
    print(_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
