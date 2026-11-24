#!/usr/bin/env python3
"""Literal action list vs lifted operator, on a real computer: which transfers?

THE QUESTION THIS MEASURES
--------------------------
The owner's question, in his words: *"saving his exact experience must be in a
very sufficient way, not just saving the exact experience in a dumb way... maybe
we should do generalization."* The Perfect Algorithm's durable unit is a plan
sketch -- the action names that worked. This probe asks what that unit is worth
when the next instance differs, and whether a lifted contract is worth more.

FOUR TRANSFER CONDITIONS, SAME GOAL ("compress the input into out.gz")
----------------------------------------------------------------------
  b  same vocabulary, different bytes, RENAMED source      (report.txt)
  c  different vocabulary that still NAMES the program     (pack_with_gzip)
  d  different vocabulary that names nothing               (alpha / beta / gamma)

For each, the same three contenders see the same environment:
  literal   replay the stored action names
  lifted    bind the stored contract by program + role, then verify the effect
  system    the Perfect Algorithm, given the memory, as it actually runs

Every contender's success is decided by the SAME external judge: the machine's
gzip reader must return exactly the source bytes AND the header must be what
this machine's gzip writes. A contender that produces a file called out.gz and
nothing else scores zero -- that was the 2026-11-24 defect.

Everything runs inside `os_isolation_v1`; nothing acts on the host.

What this does not claim: not a benchmark, not a held-out dataset, one goal
family, one machine. It is a producer-run measurement of a mechanism against its
own alternative, and the receipt says so.
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

SCHEMA = "PROJECT_BRAIN_LITERAL_OR_LIFTED_V1"
GOAL = "compress the input into out.gz"

_DRIVER = r'''
import json, pathlib, shutil, sys, time
sys.path.insert(0, "/opt/brain")

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import effect_oracle_v1 as oracle
from canonical.runtime import lifted_operator_v1 as lifted
from canonical.swe_kernel import perfect_algorithm_v1 as pa

spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
base = pathlib.Path("/state/exp")
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True, exist_ok=True)
programs = [p for p in ("gzip", "xz", "bzip2") if shutil.which(p)]

VOCAB = {
    "a": lambda p: "run_" + p,
    "b": lambda p: "run_" + p,
    "c": lambda p: "pack_with_" + p,
    "d": lambda index, p=None: "abcdefgh"[index],
}


def make(tag, source_name, payload):
    root = base / tag
    root.mkdir(parents=True, exist_ok=True)
    (root / source_name).write_bytes(payload)
    env = cenv.ComputerEnv(root=root, seed={source_name: payload})
    registered = []
    for index, program in enumerate(programs):
        for _name, fn in cenv.program_actions(env, programs=[program],
                                              target="out.gz", goal=spec["goal"]):
            if tag == "d":
                name = VOCAB["d"](index)
            else:
                name = VOCAB[tag](program)
            env.register([(name, fn)])
            registered.append(name)
    return env, registered


def _fresh_instances(tag, source_name, payload):
    """Fresh copies in the writable state mount: admission needs instances the
    rule was not taught on, and a host path means nothing inside the chroot."""
    out = []
    for index in range(2):
        root = pathlib.Path("/state/exp-%s-fresh-%d" % (tag, index))
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        (root / source_name).write_bytes(payload)
        env = cenv.ComputerEnv(root=root, seed={source_name: payload})
        for program in programs:
            for name, fn in cenv.program_actions(env, programs=[program],
                                                 target="out.gz", goal=spec["goal"]):
                env.register([(name, fn)])
        out.append(env)
    return out


def judge(env, source_name):
    root = pathlib.Path(env.root)
    return oracle.verify_roundtrip(root, "out.gz", source_name, programs=programs)


rows = []
rule = None

# ---- learn once, on instance A ------------------------------------------------
env_a, vocab_a = make("a", "input.txt", b"the first instance\n")
effect_a = oracle.oracle_from_goal(spec["goal"], programs=programs)
started = time.monotonic()
receipt_a = pa.run(env_a, spec["goal"], env_a.action_names,
                   goal_predicate=lambda s: "out.gz:" in str(s),
                   goal_family="compress_to_named_file", env_kind="posix_dir",
                   memory_path_="/state/memory.json", budget=40, max_depth=4,
                   unseen_instances=_fresh_instances("a", "input.txt",
                                                     b"the first instance\n"),
                   fresh_act=lambda i, act: i.act(act),
                   fresh_state=lambda i: i.state(),
                   fresh_reset=lambda i: i.reset(),
                   seed=11, goal_check=effect_a,
                   effect_contract=effect_a.contract)
learn_seconds = round(time.monotonic() - started, 3)
plan_a = (receipt_a.get("steps", {}).get("plan") or {}).get("plan")
verdict_a = judge(env_a, "input.txt")

rule = lifted.lift(
    goal=spec["goal"], goal_family="compress_to_named_file", env_kind="posix_dir",
    action=(plan_a or ["?"])[0], program=(plan_a or ["?"])[0].split("_")[-1],
    observation={"root": str(env_a.root)}, source_name="input.txt",
    output_name="out.gz",
    evidence={"learn_states": (receipt_a.get("steps", {}).get("scan") or {}).get("states_seen"),
              "learn_transitions": (receipt_a.get("steps", {}).get("scan") or {}).get("transitions_seen")})

conditions = [("b", "report.txt", b"a second instance with a different name\n"),
              ("c", "input.txt", b"a third instance on a differently spelled machine\n"),
              ("d", "input.txt", b"a fourth instance whose vocabulary names nothing\n")]

for tag, source_name, payload in conditions:
    env, vocab = make(tag, source_name, payload)
    row = {"condition": tag, "vocabulary": vocab, "source": source_name}

    # literal: replay the stored action names
    literal_ok, literal_detail = False, "no action of that name here"
    for name in plan_a or []:
        if name in (env.action_names or []):
            env.reset()
            env.act(name)
            literal_detail = judge(env, source_name)
            literal_ok = literal_detail.get("verdict") == "EFFECT_VERIFIED"
            break
    else:
        literal_detail = {"verdict": "NO_ACTION_WITH_THAT_NAME"}
    row["literal"] = {"ok": literal_ok, "detail": literal_detail}

    # lifted: bind by program + role, then verify the effect HERE
    lifted_out = lifted.apply_rule(rule, env, source_hint=None)
    lifted_out["effect_ok"] = bool(lifted_out.get("applied"))
    row["lifted"] = lifted_out

    # the system as it runs: memory + oracle, no help
    effect = oracle.oracle_from_goal(spec["goal"], programs=programs)
    started = time.monotonic()
    receipt = pa.run(env, spec["goal"], env.action_names,
                     goal_predicate=lambda s: "out.gz:" in str(s),
                     goal_family="compress_to_named_file", env_kind="posix_dir",
                     memory_path_="/state/memory.json", budget=40, max_depth=4,
                     unseen_instances=None, seed=11, goal_check=effect,
                     effect_contract=effect.contract)
    row["system"] = {
        "seconds": round(time.monotonic() - started, 3),
        "status": receipt.get("status"),
        "plan": (receipt.get("steps", {}).get("plan") or {}).get("plan"),
        "scan_ran": bool((receipt.get("steps", {}).get("scan") or {}).get("states_seen")),
        "effect": judge(env, source_name),
    }
    rows.append(row)

print(json.dumps({
    "learn": {"seconds": learn_seconds, "plan": plan_a,
              "status": receipt_a.get("status"), "effect": verdict_a,
              "rule": rule},
    "conditions": rows,
    "programs": programs,
}, default=str))
'''


def measure(*, keep: str | None = None) -> dict[str, Any]:
    probe = isolation.probe()
    base = pathlib.Path(keep) if keep else pathlib.Path(
        tempfile.mkdtemp(prefix="brain-literal-or-lifted-"))
    state = base / "state"
    state.mkdir(parents=True, exist_ok=True)
    work = base / "work"
    work.mkdir(parents=True, exist_ok=True)
    driver = base / "driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    spec = base / "spec.json"
    spec.write_text(json.dumps({"goal": GOAL}), encoding="utf-8")
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
        return {
            "schema": SCHEMA,
            "goal": GOAL,
            "isolation": {"verdict": probe.get("verdict"), "reasons": probe.get("reasons")},
            "isolated_run": {"ok": result.get("ok"), "isolated": result.get("isolated"),
                             "seconds": result.get("seconds")},
            "result": payload,
            "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        }
    finally:
        if not keep:
            shutil.rmtree(base, ignore_errors=True)


def _summary(report: dict[str, Any]) -> str:
    body = report.get("result") or {}
    learn = body.get("learn") or {}
    lines = ["isolation: %s" % (report["isolation"]["verdict"],),
             "learn once (A): %s in %ss, plan=%s, effect=%s" % (
                 learn.get("status"), learn.get("seconds"), learn.get("plan"),
                 (learn.get("effect") or {}).get("verdict"))]
    for row in body.get("conditions") or []:
        lift = row.get("lifted") or {}
        system = row.get("system") or {}
        lines.append(
            "  {c}: vocabulary={v}\n"
            "     literal  ok={lit:5} {litv}\n"
            "     lifted   ok={lok:5} {lst}\n"
            "     system   {sec}s {status} effect={eff}".format(
                c=row.get("condition"), v=row.get("vocabulary"),
                lit=row["literal"]["ok"], litv=(row["literal"]["detail"] or {}).get("verdict"),
                lok=lift.get("applied"), lst=lift.get("status"),
                sec=system.get("seconds"), status=system.get("status"),
                eff=(system.get("effect") or {}).get("verdict")))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", default=None)
    parser.add_argument("--keep", default=None)
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
