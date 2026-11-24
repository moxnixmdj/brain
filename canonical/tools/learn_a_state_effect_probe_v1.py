#!/usr/bin/env python3
"""Learn a lesson whose effect is a STORE, not an artifact.

WHY THIS EXISTS
---------------
Every effect this system could verify until now was a byte stream: the artifact's
reader had to carry the source out and bring it back. That covers compression and
repacking and nothing else. A database row, a GUI's accessibility tree, a DOM, a
sent request -- the things computer use is actually made of -- were unverifiable,
so the loop could act on them and had no way to know whether it had succeeded.

`effect_oracle_v1.verify_state` adds the second shape: read the store back,
without knowing the schema, and ask whether it reproduces the source. This probe
is the end-to-end evidence -- one exposure, a goal-derived contract, a verified
state effect, then a renamed source in a different directory replayed from memory.

WHAT THIS DOES NOT CLAIM
------------------------
Not a benchmark. SQLite is the store that happens to exist on this machine; the
mechanism is "structured state, queried back, compared to the goal", which is what
an accessibility tree or a DOM will need. Producer-run, one machine, one session.
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

SCHEMA = "PROJECT_BRAIN_STATE_EFFECT_LESSON_V1"

_DRIVER = r'''
import json, pathlib, shutil, sqlite3, sys
sys.path.insert(0, "/opt/brain")

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import effect_oracle_v1 as oracle
from canonical.swe_kernel import perfect_algorithm_v1 as pa

base = pathlib.Path("/state/state_lessons")
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True, exist_ok=True)
memory = str(base / "memory.json")
SOURCE = "one line\nsecond line\n"


def store_rows(env, roles=None):
    """The right way: one row per line, so the store reads back as the source.

    It reads the source by ROLE, never by name -- that is what lets the same
    lesson store `report.txt` tomorrow. A version that hardcoded `input.txt` was
    measured: it replayed into the held-out world, ran, and produced the wrong
    rows, and the oracle said so.
    """
    path = env.root / "out.db"
    if path.exists():
        path.unlink()
    source = (roles or {}).get("source") or "input.txt"
    lines = (env.root / source).read_text().splitlines()
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE notes(body TEXT)")
    connection.executemany("INSERT INTO notes VALUES (?)", [(line,) for line in lines])
    connection.commit()
    connection.close()
    return True


def store_one_row(env, roles=None):
    """Also right, and different: one row holding the whole text."""
    path = env.root / "out.db"
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE blob(all_of_it TEXT)")
    connection.execute("INSERT INTO blob VALUES (?)",
                       ((env.root / "input.txt").read_text(),))
    connection.commit()
    connection.close()
    return True


def store_wrong(env, roles=None):
    """Wrong on purpose: the store exists and the rows are not the source."""
    path = env.root / "out.db"
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE notes(body TEXT)")
    connection.execute("INSERT INTO notes VALUES (?)", ("nothing to do with it",))
    connection.commit()
    connection.close()
    return True


def copy_input(env):
    shutil.copyfile(env.root / "input.txt", env.root / "copy.txt")
    return True


def build(root, source_name):
    root.mkdir(parents=True, exist_ok=True)
    (root / source_name).write_text(SOURCE)
    env = cenv.ComputerEnv(root=root, seed={source_name: SOURCE.encode()})
    for name, fn in (("store_rows", store_rows), ("store_one_row", store_one_row),
                     ("store_wrong", store_wrong), ("copy_input", copy_input)):
        env.register([(name, fn)])
    return env


goal = "store the input in out.db"
lesson_root = base / "lesson"
env = build(lesson_root, "input.txt")
check = oracle.oracle_from_goal(goal)
# two fresh instances of the same family: without them nothing can be admitted,
# and an unadmitted lesson is not allowed into the store
fresh = [build(base / ("fresh-%d" % index), "input.txt") for index in range(2)]
receipt = pa.run(env, goal, env.action_names,
                 goal_predicate=lambda s: "out.db:" in str(s),
                 goal_family="store_in_a_database", env_kind="posix_dir",
                 memory_path_=memory, budget=16, max_depth=3, seed=11,
                 unseen_instances=fresh,
                 fresh_act=lambda i, a: i.act(a),
                 fresh_state=lambda i: i.state(),
                 fresh_reset=lambda i: i.reset(),
                 goal_check=check, effect_contract=check.contract)

# ---- held out: a different name in a different directory, from memory only ----
held_root = base / "held_out"
held = build(held_root, "report.txt")
held_check = oracle.oracle_from_goal("store the input in out.db")
replay = pa.run(held, "store the input in out.db", held.action_names,
                goal_predicate=lambda s: "out.db:" in str(s),
                goal_family="store_in_a_database", env_kind="posix_dir",
                memory_path_=memory, budget=8, max_depth=2, seed=11,
                goal_check=held_check, effect_contract=held_check.contract)

# ---- the judge: read the store with plain SQL, knowing nothing we learned ----
def judge(root, source_name):
    connection = sqlite3.connect(root / "out.db")
    rows = [row[0] for row in connection.execute(
        "SELECT body FROM notes")] if connection.execute(
            "SELECT count(*) FROM sqlite_master WHERE name='notes'").fetchone()[0] else None
    connection.close()
    if rows is None:
        return {"table": "blob", "judged_by": "the state oracle's own reading"}
    return {"table": "notes", "rows": rows,
            "bytes_equal_source": ("\n".join(rows) + "\n") ==
                                  (root / source_name).read_text()}


print(json.dumps({
    "lesson": {"status": receipt.get("status"),
               "plan": (receipt.get("steps", {}).get("plan") or {}).get("plan"),
               "act": receipt.get("steps", {}).get("act"),
               "effect": (receipt.get("steps", {}).get("act") or {}).get("oracle")
                         or check.last,
               "lift": (receipt.get("steps", {}).get("lift") or {}).get("status"),
               "admit": (receipt.get("steps", {}).get("admit") or {}).get("verdict"),
               "duration_s": receipt.get("duration_s")},
    "held_out": {"status": replay.get("status"),
                 "operator_replay": replay.get("steps", {}).get("operator_replay"),
                 "memory_replay": replay.get("steps", {}).get("memory_replay"),
                 "plan": (replay.get("steps", {}).get("plan") or {}).get("plan"),
                 # the verdict that decided the replay, not a later reading of
                 # the world: an honest receipt says what was judged when
                 "effect": ((replay.get("steps", {}).get("memory_replay") or {})
                            .get("effect") or held_check.last),
                 "duration_s": replay.get("duration_s")},
    "judge": {"lesson": judge(lesson_root, "input.txt"),
              "held_out": judge(held_root, "report.txt")},
    "memory_rules": [(r.get("program"), r.get("goal_family"), r.get("output_name"))
                     for r in (pa.load_memory(memory).get("rules") or [])],
}, default=str))
'''


def measure(*, keep: str | None = None) -> dict[str, Any]:
    probe = isolation.probe()
    base = pathlib.Path(keep) if keep else pathlib.Path(
        tempfile.mkdtemp(prefix="brain-state-lesson-"))
    work = base / "work"
    state = base / "state"
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
            payload = {"parse": "EMPTY",
                       "stderr": (result.get("stderr") or "")[-1500:]}
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
    lesson = body.get("lesson") or {}
    verdict = ((lesson.get("effect") or {}).get("verdict") or "?")
    print("  lesson    %s plan=%s effect=%s" % (lesson.get("status"),
                                               lesson.get("plan"), verdict))
    held = body.get("held_out") or {}
    print("  held out  %s plan=%s effect=%s" % (
        held.get("status"), held.get("plan"),
        (held.get("effect") or {}).get("verdict")))
    print("  judge:", json.dumps(body.get("judge"), default=str))
    print("  memory:", body.get("memory_rules"))
    if args.json:
        pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.json).write_text(json.dumps(report, indent=2, default=str),
                                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
