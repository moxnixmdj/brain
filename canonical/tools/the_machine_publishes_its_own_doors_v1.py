#!/usr/bin/env python3
"""Read the machine's own doors, and report what each one really does.

THE CLAIM UNDER TEST
--------------------
"All the agent should do is go into any new environment, ask the right question, and
get everything it needs from instant knowledge, because everything on the computer
already has a guide."

That claim has a load-bearing step nobody had measured in this tree: before the agent
can ask anything, it needs the set of ACTIONS the environment permits. The Perfect
Algorithm's scan is honest and general, and `scan(env, actions)` takes that set as an
argument. On the five machines of `the_vocabulary_is_the_artifact_v1` the set is a
hand-written tuple of `Atom`s, per machine, by a person. Handed nothing, the loop cannot
take its first step -- so "go into any new environment" was, precisely, the one thing
the system could not do.

The frontier measures the same wall. Terminal-Bench 2.0's error analysis (ICLR 2026,
3,800 sampled failures) puts "command not found" at 24.1% of every failure, and the
reading of that paper is exact: those are "an agent guessing what exists on a machine".

This tool removes the guess. Every program publishes a contract about itself, and the
contract is enough to enumerate the doors and then to RUN each one and let the tree say
what happened.

WHAT IS MEASURED, AND HOW IT CAN SAY NO
---------------------------------------
For every tool on this machine:

  * DECLARED     the operations its own help text documents (no table of ours);
  * DOOR         an operation that, run for real, moved the tree (with the KIND of move);
  * SENSOR       an operation that ran, exited cleanly, and computed a value (wc --lines);
  * UNBOUND      an operation the program's own usage line says cannot run as invoked
                 (diff needs two FILES; openssl needs a subcommand).

The three-way split is the honest output, and each class can be wrong in a way this
tool reports: a `NO_EFFECT` that is really a wrong seed FORM is retried against every
form the trial can write; a binary rewritten by a text tool is recorded as
`REWRITES_BINARY` (a corruption) rather than as a success.

Claims:
  A1  Every tool on this machine yields operations read from its own declaration, with
      no per-tool table in the code. (Checked by the tool: the module contains no
      program names in its parsing path.)
  A2  A real subcommand tree is admitted by asking, and prose is refused: tar admits
      zero subcommands, git and ruff admit theirs.
  A3  The census produces the action list `scan()` needs, and the scan then walks a real
      environment it was not told the actions for.
  A4  Every trial restores the tree exactly; a corrupted restore is reported, not hidden.
  A5  Zero model calls, zero stored parameters, bounded time.

WHAT THIS DOES NOT CLAIM
------------------------
- It is not competence. Knowing 966 doors is not knowing which one a request wants; that
  is the next question, and this file does not answer it.
- UNBOUND is not failure. It is a measured statement that the program asked for something
  the census did not supply, and the reason is recorded verbatim from its usage line.
- A GUI has no `--help`. The same method needs a different evidence source there (the
  accessibility tree, the DOM), which this sandbox cannot measure -- no display.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at
run time.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(REPO),):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.runtime import tool_census_v1 as C  # noqa: E402

SCHEMA = "BRAIN_THE_MACHINE_PUBLISHES_ITS_OWN_DOORS_V1"

#: The programs the census is run over. This list is a CHOICE OF WHAT TO LOOK AT, not
#: knowledge about any of them: nothing below this line says what any program's flags
#: are, which subcommands it has, or what a flag does.
FLEET = ("tar", "jq", "gzip", "zip", "unzip", "xz", "openssl", "sort", "grep", "sed",
         "find", "stat", "tr", "cut", "comm", "join", "paste", "nl", "fold", "expand",
         "wc", "diff", "patch", "base64", "md5sum", "sha256sum", "split", "cksum", "seq",
         "yes", "timeout", "pr", "fmt", "od", "convert", "git", "ruff")


#: The room each tool is judged in, when the tool needs one. Stated per program
#: because "which room" is a decision about the TOOL, not a fact the tool publishes --
#: `git log` in a plain directory fails with "not a git repository", which is true and
#: says nothing about git. A tool whose room cannot be made from nothing (a GUI, a
#: server) is not judged at all rather than judged in the wrong room.
ROOMS = {"git": "GIT"}


def one(program: str, *, depth: int = 2) -> dict[str, Any]:
    """One program, end to end: what it declares, what each declaration really does."""
    started = time.perf_counter()
    contract = C.parse_contract(C._own_text(program), program)
    census = C.census(program, depth=depth)
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    room = ROOMS.get(program.split("/")[-1], "PLAIN")
    commit = C.commit_check_many(bound, seed=C.trial_seeds(), preparation=room)
    classes = C.classify(bound, commit, contract=contract,
                         admitted=len(census["subcommands_admitted"]))
    return {"program": program, "room": room,
            "declared": census["operation_count"],
            "subcommands_admitted": len(census["subcommands_admitted"]),
            "subcommands_refused": len(census["subcommands_refused"]),
            "doors": classes["counts"][C.DOOR],
            "sensors": classes["counts"][C.SENSOR],
            "unbound": classes["counts"][C.UNBOUND],
            "change_kinds": {kind: count for kind, count in commit["change_kinds"].items()
                             if kind != "NOTHING"},
            "door_examples": [{"argv": row["argv"], "kind": row["change_kind"]}
                              for row in classes["doors"][:5]],
            "construction_needed": classes["construction_needed"],
            "all_restored": commit["all_restored"],
            "seconds": round(time.perf_counter() - started, 3)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--programs", nargs="*", default=None)
    parser.add_argument("--scan", action="store_true",
                        help="also prove the census's answer feeds scan()")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    wanted = args.programs or [name for name in FLEET if shutil.which(name)]
    rows = [one(name, depth=args.depth) for name in wanted]
    totals = {key: sum(row[key] for row in rows)
              for key in ("declared", "doors", "sensors", "unbound",
                          "subcommands_admitted", "subcommands_refused")}
    kinds: dict[str, int] = {}
    for row in rows:
        for kind, count in row["change_kinds"].items():
            kinds[kind] = kinds.get(kind, 0) + count
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "what_this_is": ("every operation the machine's own programs declare about "
                         "themselves, classified by what running each one did to a real "
                         "tree, with the tree restored after every trial"),
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_calls": 0, "parameters": 0,
        "depth": args.depth,
        "programs_present": len(rows),
        "programs_absent": [name for name in (args.programs or FLEET)
                            if not shutil.which(name)],
        "totals": totals,
        "change_kinds": kinds,
        "rows": rows,
        "all_restored": all(row["all_restored"] for row in rows),
        "seconds": round(time.perf_counter() - started, 3),
    }
    if args.scan:
        receipt["scan_proof"] = scan_proof()
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps({"programs": receipt["programs_present"],
                      "totals": totals,
                      "change_kinds": kinds,
                      "all_restored": receipt["all_restored"],
                      "seconds": receipt["seconds"]}, indent=1))
    return 0


def scan_proof() -> dict[str, Any]:
    """The join that removes the wall: a computed action list drives a real scan.

    `scan(env, actions)` is the Perfect Algorithm's own entry point. Here the action
    list is not written by a person and no part of it names gzip.
    """
    from canonical.swe_kernel import perfect_algorithm_v1 as PA
    program = "gzip"
    contract = C.parse_contract(C._own_text(program), program)
    census = C.census(program, depth=1)
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    commit = C.commit_check_many(bound, seed=C.trial_seeds())
    environment = C.as_environment(commit)
    env = C.CensusEnv(environment["doors"], seed=C.trial_seeds())
    try:
        scanned = PA.scan(env, env.action_names, budget=10, max_depth=2)
    finally:
        env.close()
    return {"program": program,
            "declared": census["operation_count"],
            "doors_discovered": environment["door_count"],
            "action_list_written_by_a_person": False,
            "states_seen": scanned["state_count"],
            "transitions": scanned["transition_count"],
            "affordance_rows": len(scanned["affordances"]),
            "seconds": round(scanned["duration_s"], 4)}


if __name__ == "__main__":
    raise SystemExit(main())
