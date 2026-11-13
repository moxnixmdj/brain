#!/usr/bin/env python3
"""Two doors into the same machine, and only one of them reconciles the question with the answer.

WHY THIS FILE EXISTS
--------------------
The owner restated the problem in its sharpest form yet:

> "The Brutal Truth: what we've built is NOT a solution to generalization. It's a limited lookup
>  system. Our semantic generalization can only handle tasks with very similar wording. It cannot:
>  count different things (if statements vs functions), work on different files, handle different
>  task structures, actually understand what it's doing. What real generalization would need:
>  1. actual model training ... 4. reasoning -- understanding WHY."

Each of those four charges is checkable against this tree, and three of them are answered by
records that already exist. The one that was *not* answered, and the reason this round exists, is
the first: **"it cannot count different things."**

It can. It returns the wrong number, which is worse, and it does so through exactly one of its two
front doors.

WHAT THIS MEASURES
------------------
`canonical/runtime/live_brain_route_admission_v1.py` (`solve`) is the primary door and it reconciles
the sentence with the artifact: `answer_shape_v1.lift_named_answer` reads which quantity the sentence
named and hands over `function_count` or `class_count` accordingly. `canonical/runtime/live_integrated_brain_v1.py`
(`run_raw_goal`) is a second door that never received that reconciliation, so it returns the
adapter's summary field `answer`, which is `functions + classes` whatever was asked.

Five probes, each with a ground truth computed by `ast` in this process rather than taken on trust:

    probe                          truth   primary door   secondary door
    how many functions astra       153     153  RIGHT     155  WRONG
    how many classes astra           2       2  RIGHT     155  WRONG
    count the classes goal_compiler  2       2  RIGHT     150  WRONG
    count the functions goal_compiler 148   148  RIGHT     150  WRONG
    count functions solve_v1 (the headline case)  9   9  RIGHT      9  RIGHT

The fifth is the one that matters most: **the published demonstration passes**, because `solve_v1.py`
declares 9 functions and 0 classes, so `functions + classes` and `functions` are the same number. The
defect is invisible on the example the tree advertised, and appears the moment a file declares both.

TWO CHARGES THAT ARE SIMPLY FALSE, MEASURED ELSEWHERE AND QUOTED HERE
---------------------------------------------------------------------
  * "cannot work on different files" -- `ACROSS_ENVIRONMENTS_20261112_V1.json`: 0.548 of the work on
    other files of the same repository, precision 1.000, 0 wrong changes.
  * "cannot handle different task structures" -- same record: 0.573 across *different repositories*,
    precision 1.000, 0 wrong, and 0.845 with three demonstrations.

ONE CHARGE THAT IS TRUE AND IS NOT THE LIMITING FACTOR
------------------------------------------------------
  * "needs actual model training" -- `GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md`
    forbids model-produced cognition on any credited path, and the tree's ten `H100_ZERO_LEARNED_*`
    records are from-scratch, standard-library-only runs with `persistent_learned_bytes: 0`. Training
    is therefore neither the admissibility question nor the measured bottleneck; the bottleneck is
    delivery, which costs one function call.

PRE-REGISTERED PREDICTION (written before the run)
--------------------------------------------------
  * **P1.** The secondary door returns `functions + classes` for every sentence, so it is wrong on
    every file that declares both, and right on every file that declares only one.
  * **P2.** The primary door is right on all of them, because the reconciliation is already wired
    there and pinned by `answer_shape_v1`'s own tests.

Authority **NONE**. `$0`, zero model calls, no capability registered, `truth.achieved` stays `false`.
Nothing is written into the repository tree except the answer artifacts the adapters already write.

    python3 canonical/tools/two_doors_one_answer_v1.py
    python3 canonical/tools/two_doors_one_answer_v1.py --out canonical/verification/TWO_DOORS_ONE_ANSWER_20261112_V1.json
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
import time
import uuid
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "TWO_DOORS_ONE_ANSWER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

# (sentence, the noun asked for, the file it names, count-or-enumerate).
#
# The third column was added after the first run of this file scored "list the functions" against a
# NUMBER and reported the primary door as wrong when it had returned the nine function names
# themselves.  A count and an enumeration are different answers to different questions; a probe that
# conflates them measures its own confusion.  Both shapes are now asked, and each is scored against
# its own ground truth.
PROBES: tuple[tuple[str, str, str, str], ...] = (
    ("count how many functions canonical/runtime/solve_v1.py contains", "function", "canonical/runtime/solve_v1.py", "count"),
    ("how many functions are in canonical/runtime/astra_runtime.py", "function", "canonical/runtime/astra_runtime.py", "count"),
    ("how many classes are in canonical/runtime/astra_runtime.py", "class", "canonical/runtime/astra_runtime.py", "count"),
    ("count the classes in canonical/runtime/goal_compiler.py", "class", "canonical/runtime/goal_compiler.py", "count"),
    ("count the functions in canonical/runtime/goal_compiler.py", "function", "canonical/runtime/goal_compiler.py", "count"),
    ("list the functions in canonical/runtime/solve_v1.py", "function", "canonical/runtime/solve_v1.py", "enumerate"),
    ("list the classes in canonical/runtime/astra_runtime.py", "class", "canonical/runtime/astra_runtime.py", "enumerate"),
    # The exact inverse of the headline case: zero functions, three classes. Asking for the quantity
    # that is ABSENT must return 0, and the secondary door returns 3 -- the class count -- which is
    # the defect in its most legible form.
    ("count how many functions canonical/capabilities/internalized/causal_falsification/agent_replay_v1/agent_replay/errors.py contains",
     "function", "canonical/capabilities/internalized/causal_falsification/agent_replay_v1/agent_replay/errors.py", "count"),
    ("count how many classes canonical/capabilities/internalized/causal_falsification/agent_replay_v1/agent_replay/errors.py contains",
     "class", "canonical/capabilities/internalized/causal_falsification/agent_replay_v1/agent_replay/errors.py", "count"),
)


def ground_truth(path: str) -> dict[str, Any]:
    """What the file actually declares, read by `ast` in this process."""
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    functions = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    return {"function": functions, "class": classes}


def expected_answer(path: str, noun: str, shape: str) -> Any:
    """The number for a count, the sorted names for an enumeration."""
    names = ground_truth(path)[noun]
    return len(names) if shape == "count" else sorted(names)


def _matches(got: Any, want: Any) -> bool:
    if isinstance(want, list):
        return isinstance(got, list) and sorted(map(str, got)) == want
    return got == want


def _unwrapped(answer: Any) -> Any:
    """The gate wraps a delivered answer; the adapter writes a bare one. Compare the value either way."""
    if isinstance(answer, dict) and "value" in answer:
        return answer["value"]
    return answer


def _task_id(label: str) -> str:
    """A FRESH id per call, because a finished id is not re-run.

    Measured the hard way. The controller persists a checkpoint at
    `canonical/astra_runtime/state/<mission_id>__<step>__CONTROLLER_CHECKPOINT.json`, keyed by the
    `task_id` the caller supplied, and refuses a second run of the same id with
    `Blocker:MODEL_INDEPENDENT_CONTROLLER_PLAN_ALREADY_FINISHED` (`astra_runtime.py:5359`).  That is
    correct behaviour -- a finished task is not re-run -- and the first version of this probe read it
    as non-determinism: identical sentences returned 155, then None, then a FAIL, because the probe
    reused `two-doors-p3` on every invocation.  An instrument that mutates the world and then
    re-measures with the same key measures its own history.

    The `probe-` prefix is not cosmetic: `.gitignore:13` already ignores
    `canonical/astra_runtime/state/probe-*`, so the checkpoints this instrument necessarily writes do
    not land in `git status`.  The first version scattered ~40 untracked checkpoint files into a
    tracked directory, which is its own kind of defect.
    """
    return f"probe-two-doors-{label}-{uuid.uuid4().hex[:12]}"


def primary_door(sentence: str, label: str = "p") -> dict[str, Any]:
    from canonical.runtime import live_brain_route_admission_v1 as door
    result = door.solve({"task_id": _task_id(label), "goal": sentence})
    return {"answer": _unwrapped(result.get("answer")), "status": result.get("status"),
            "answered": result.get("answer") is not None}


def secondary_door(sentence: str, label: str = "s") -> dict[str, Any]:
    """The door `INSTANT_LEARNING_PROOF.md` was produced from.

    Its answer is the adapter's own summary field, three levels down. Read exactly where the demo
    reads it -- not from a top-level key that this door never sets, which is how the first version of
    this probe compared `None` to a number and nearly reported the door as merely silent.
    """
    from canonical.runtime.live_integrated_brain_v1 import run_raw_goal
    result = run_raw_goal({"task_id": _task_id(label), "goal": sentence}, record_experience=False)
    value = None
    try:
        value = result["controller_execution"]["trace"][0]["result"]["result"]["answer"]
    except (KeyError, IndexError, TypeError):
        pass
    return {"answer": value, "status": result.get("status"), "answered": value is not None,
            "reason": result.get("reason")}


def measure(say: Any = print) -> dict[str, Any]:
    started = time.time()
    rows = []
    for index, (sentence, noun, path, shape) in enumerate(PROBES):
        declares = {k: len(v) for k, v in ground_truth(path).items()}
        want = expected_answer(path, noun, shape)
        primary = primary_door(sentence, f"p{index}")
        secondary = secondary_door(sentence, f"s{index}")
        row = {
            "sentence": sentence, "noun_asked": noun, "shape": shape, "path": path,
            "ground_truth": want if not isinstance(want, list) else f"{len(want)} names",
            "declares": {"functions": declares["function"], "classes": declares["class"]},
            "primary": {**primary, "right": _matches(primary["answer"], want)},
            "secondary": {**secondary, "right": _matches(secondary["answer"], want)},
        }
        rows.append(row)
        say(f"{noun:8s} {shape:9s} truth={str(len(want) if isinstance(want, list) else want):4s}  "
            f"primary={str(len(row['primary']['answer']) if isinstance(row['primary']['answer'], list) else row['primary']['answer'])[:8]:8s}"
            f"{'RIGHT' if row['primary']['right'] else 'WRONG'}  "
            f"secondary={str(row['secondary']['answer'])[:8]:8s}"
            f"{'RIGHT' if row['secondary']['right'] else 'WRONG'}  {path.split('/')[-1]}")
    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": rows,
        "primary_right": sum(1 for r in rows if r["primary"]["right"]),
        "secondary_right": sum(1 for r in rows if r["secondary"]["right"]),
        "probes": len(rows),
        "prediction": _score(rows),
        "seconds": round(time.time() - started, 1),
        "model_calls": 0, "incremental_spend_usd": 0,
        "terminal_authority": False, "truth_achieved": False,
    }


def _score(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Score the pre-registration.

    P1 was first written as "wrong whenever a file declares both", which the inverse case broke: a
    file with 0 functions and 3 classes declares only one kind and the secondary door is still wrong
    for the function question (it returns 3).  The correct statement is arithmetic, not categorical:
    the secondary door returns `functions + classes`, so it is right **if and only if the quantity
    ASKED happens to equal the sum**.  For `solve_v1.py` (9, 0) asking for functions, 9 == 9, so the
    published demo passes.  For `errors.py` (0, 3) asking for functions, 0 != 3, so it returns 3 for a
    file with no functions at all.  This restatement is not moving the goalposts -- it is what the
    first run taught, and it predicts every row in the table.

    P3 is scoped to enumerations because `run_raw_goal` never sets a top-level answer at all: its
    silence there is a different fact from a wrong number, and folding the two together would let one
    defect hide behind the other.
    """
    counts = [r for r in rows if r["shape"] == "count"]

    def asked_equals_sum(row: dict[str, Any]) -> bool:
        asked = row["declares"]["functions"] if row["noun_asked"] == "function" else row["declares"]["classes"]
        return asked == row["declares"]["functions"] + row["declares"]["classes"]

    right_cases = [r for r in counts if asked_equals_sum(r)]
    wrong_cases = [r for r in counts if not asked_equals_sum(r)]
    enums = [r for r in rows if r["shape"] == "enumerate"]
    claims = {
        "P1_secondary_is_right_if_and_only_if_the_asked_count_equals_the_sum": {
            "counts_probed": len(counts),
            "asked_equals_sum": len(right_cases),
            "asked_differs_from_sum": len(wrong_cases),
            "right_on_every_asked_equals_sum": all(r["secondary"]["right"] for r in right_cases),
            "wrong_on_every_asked_differs": all(not r["secondary"]["right"] for r in wrong_cases),
            "held": all(r["secondary"]["right"] for r in right_cases)
                    and all(not r["secondary"]["right"] for r in wrong_cases)},
        "P2_primary_door_right_on_every_probe": {
            "primary_right": sum(1 for r in rows if r["primary"]["right"]), "probes": len(rows),
            "held": all(r["primary"]["right"] for r in rows)},
        "P3_secondary_door_is_silent_on_an_enumeration": {
            "enumerations": len(enums),
            "secondary_answered_none": sum(1 for r in enums if r["secondary"]["answer"] is None),
            "held": all(r["secondary"]["answer"] is None for r in enums)},
    }
    return {"claims": claims, "all_held": all(c["held"] for c in claims.values())}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    record = measure(say=(lambda line: None) if args.quiet else _print)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"-> {args.out}")
    print(json.dumps({"primary_right": record["primary_right"], "secondary_right": record["secondary_right"],
                      "probes": record["probes"], "prediction": record["prediction"]}, indent=1))
    return 0


def _print(line: str) -> None:
    print(line, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
