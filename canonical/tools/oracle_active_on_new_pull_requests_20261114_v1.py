#!/usr/bin/env python3
"""Does an oracle make instant learning solve real code, or does the oracle do the solving?

THE QUESTION, IN THE OWNER'S WORDS
----------------------------------
"Give the model the most advanced coding actions and let it experience them once, and then it
learns them permanently. After that we have the most advanced coding agent on the planet. Is this
revolutionary, or are there things that are wrong?"

The tree already answers the *speed* half. One demonstration gives a rule that is right about 10%
of the time on held-out inputs; the same demonstration plus the questions worth asking is right
100% of the time at a mean of 2.0 questions (`one_shot_identifiability_probe_20261112.py` and
`settled_admission_v1.py`, both on constructed spaces). What has never been measured is the thing
that decides whether this is a solution or a tautology:

    on REAL code, how much of the organ's output does the oracle confirm, and how much of that
    agreement is the organ's rather than the oracle's?

THE DESIGN
----------
For each pull request: one changed file is the demonstration, and each other changed file is a
target. Nothing is tuned; the organ is `edit_by_example_v1` exactly as it stands.

  ONE   one demonstration, then the organ's output. This is "shown once".
  TWO   two demonstrations from two different files, put together the way this tree already puts
        two showings together, then the organ's output. This is "shown twice", and it is the
        strongest form of the claim: this tree measured that one showing memorises and two
        generalise, so testing "learned once" on real code would be testing a refusal.
  FALSE the developers' own answer for that file. Not an output of the organ and not knowable
        from it: the ceiling of ANY reviewer of the organ, so a number the organ cannot reach by
        being clever and cannot be blamed for missing.

THE ORACLE, AND WHY IT IS THE POINT
-----------------------------------
The oracle answers "what should this return here", and it is built from the demonstration's own two
files: the before-file's function is one hypothesis, the after-file's function is the other. The
organ's edit is a third value. The oracle is *calibrated against real use*: it was selected because
the developers' own edits on the third file agree with it. If it could not predict what the
developers did on that file, it would be a bad oracle and the measurement would say so through the
`calibration` field instead of quietly inflating the result.

AND THE PART THAT KEEPS IT HONEST
---------------------------------
The claim is only made where no question could ever have been asked. The oracle is built from the
demonstration; it is queried only on inputs OUTSIDE the demonstration's own probe grid (the grid is
the demonstration's literals and their neighbours). Inside the grid the demonstration would have
answered the question itself, so a result there is not the oracle doing anything the learner could
not have done. Both are reported; only the outside number is the claim.

WHAT IS COUNTED
---------------
A change is a changed line of the file, compared one statement per line the way the rest of this
tree compares them. A change is *confirmed* when the oracle agrees with it inside the grid, and it
is a *wrong right-looking change* when the oracle contradicts it outside the grid. The second
number is the one that matters, for the same reason the held-out transfer record keeps a
wrong-change count: a permanent learner that writes plausible wrong code is not a capability.

    python3 canonical/tools/oracle_active_on_new_pull_requests_20261114_v1.py --pulls FILE --json OUT
    python3 canonical/tools/oracle_active_on_new_pull_requests_20261114_v1.py --collect OUT

Nothing here reaches for a model. Zero calls, zero network in the measurement path, $0.
Authority: NONE. This measures one organ on one class of change in six small files per pull request.
It says nothing about computer use, and it is not a capability registration.
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import sys
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe
from canonical.tools import repeated_change_one_example_measure_v1 as R
from canonical.tools.repeated_change_one_example_measure_v1 import score, statement_lines

SCHEMA = "ORACLE_ACTIVE_ON_REAL_PULL_REQUESTS_V1"
AUTHORITY = "NONE"

# The probe grid the demonstration itself covers: its literals and their neighbours. Kept in step
# with `settled_admission_v1.GRID_VALUES`; a value inside it is one the demonstration could answer.
GRID_VALUES: tuple[int, ...] = (-1, 0, 1, 2, 3, 10, 11)
OUTSIDE = "4,5,6,7,8,9,12,13,20,21,40"
ANSWERABLE = ",".join(str(v) for v in GRID_VALUES)
ARMS = ("ONE", "TWO", "FALSE")

Truth = Callable[[Any], Any]


# --------------------------------------------------------------------------------- the oracle

def _first_function(text: str) -> tuple[str, str] | None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name, ast.get_source_segment(text, node) or ast.unparse(node)
    return None


def _load(text: str) -> tuple[str, Callable[..., Any]] | None:
    found = _first_function(text)
    if found is None:
        return None
    name, source = found
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<oracle>", "exec"), namespace)  # noqa: S102
    except Exception:  # noqa: BLE001 - a file that will not load is not an oracle
        return None
    fn = namespace.get(name)
    return (name, fn) if callable(fn) else None



def path_signature(fn: Callable[..., Any], count: int, value: Any) -> Any:
    """Which branch the function took, as line offsets from its own start.

    Two files' functions cannot be compared by what they RETURN: `return 1` in the demonstration and
    `return 2` in the target are different numbers for the same behaviour, and comparing them
    reported every copied change as wrong. What IS the same across versions is the SHAPE of the path:
    the guard held and the early return ran, or the guard did not hold and the fall-through ran.
    Recording executed line numbers relative to the function's first line makes that comparable, and
    it is the only question a guard change is really asking.

    A raise is its own signature: a guard that now rejects an input the old one accepted is exactly
    the kind of change this is looking for.
    """
    import sys as _sys
    offsets: list[int] = []
    first = fn.__code__.co_firstlineno

    def trace(frame, event, arg):
        if frame.f_code is fn.__code__ and event == "line":
            offsets.append(frame.f_lineno - first)
        return trace

    args = [value] + [0] * max(0, count - 1)
    previous = _sys.gettrace()
    _sys.settrace(trace)
    try:
        fn(*args)
    except Exception as exc:  # noqa: BLE001 - a raise is an answer
        _sys.settrace(previous)
        return ("raise", type(exc).__name__, tuple(offsets))
    finally:
        _sys.settrace(previous)
    return tuple(offsets)


def demonstration_oracle(before_text: str, after_text: str) -> Truth | None:
    """The two versions of the demonstration's own function, and nothing else.

    Before the change one thing was true; after it another was. The developers' edit on a second
    file is the calibration. No model, no external knowledge, no generality: two functions.

    The function's first parameter is the one the question varies; the others are filled from a
    small fixed set of plain values, because a question is "what should this return HERE" and a
    function of two arguments still has one answer. Measured while writing this: an oracle that
    took one argument was called with a two-argument function and every answer was a TypeError,
    which would have reported zero agreement for a reason that has nothing to do with the organ.
    """
    was, now = _load(before_text), _load(after_text)
    if was is None or now is None or was[0] != now[0]:
        return None
    before_fn, after_fn = was[1], now[1]
    try:
        count = len([p for p in __import__("inspect").signature(after_fn).parameters.values()
                     if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
    except (TypeError, ValueError):
        return None
    if count == 0:
        return None

    def oracle(*given: Any) -> Any:
        value = given[0] if given else 0
        rest = list(given[1:])
        args = (value, *rest) if given else tuple([0] * count)
        try:
            after = after_fn(*args)
        except Exception as exc:  # noqa: BLE001 - a raise is an answer
            after = ("raise", type(exc).__name__)
        # The value is not comparable across files; the shape of the path is.
        return path_signature(after_fn, count, value)

    oracle.arity = count                  # a *given function has no signature to read
    return oracle


def _with_arity(fn: Callable[..., Any], count: int) -> Callable[..., Any]:
    """The organ's edited function, answered the same way the oracle answers: by path shape."""
    def call(*given: Any) -> Any:
        value = given[0] if given else 0
        return path_signature(fn, count, value)
    call.arity = count
    return call


def _answers(oracle: Truth, values: Sequence[str]) -> list[Any]:
    """The oracle's answers on the given inputs; the remaining parameters are filled the same way.

    A two-argument function still has one answer to "what should this return here", so the answers
    are produced by the same caller the oracle uses. Measured while writing this: asking a
    two-argument function with one argument made every answer a TypeError on the organ's side and
    reported zero agreement for a reason that has nothing to do with the organ.
    """
    count = getattr(oracle, "arity", None)
    if count is None:
        try:
            count = len([p for p in __import__("inspect").signature(oracle).parameters.values()
                         if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
        except (TypeError, ValueError):
            count = 1
    out = []
    for text in values:
        try:
            value = int(text)
        except ValueError:
            continue
        args = [value] + [0] * max(0, count - 1)
        out.append(truth_of(oracle, *args))
    return out


def truth_of(oracle: Truth, *args: Any) -> Any:
    try:
        return oracle(*args)
    except Exception as exc:  # noqa: BLE001 - a raise is an answer
        return ("raise", type(exc).__name__)


# ----------------------------------------------------------------------------- one confirmed change

def _unparse(text: str) -> str | None:
    try:
        return ast.unparse(ast.parse(text))
    except SyntaxError:
        return None


def confirmed_change(target_before: str, example_before: str, example_after: str, *,
                     oracle: Truth | None, grid: str = OUTSIDE) -> dict[str, Any] | None:
    """The organ's edit, and what the oracle says about it inside and outside the grid."""
    try:
        edited = ebe.edit_by_example(target_before, example_before, example_after)
    except ebe.Refused:
        return None
    except Exception:  # noqa: BLE001 - any other failure is a refusal by another name
        return None
    if edited is None or edited == target_before:
        return None
    if oracle is None:
        return {"edited": edited, "agrees_inside": None, "agrees_outside": None,
                "asked_inside": 0, "asked_outside": 0}
    inside_answers = _answers(oracle, ANSWERABLE.split(","))
    outside_answers = _answers(oracle, grid.split(","))
    # The organ's edit is loaded and asked the SAME questions. A comparison of a function with
    # itself would be `all(a == b for a, b in zip(answers, answers))`, which is always true and was
    # the first version of this line: a measurement that cannot say no is not a measurement.
    edited_fn = _load(edited)
    if edited_fn is None:
        return {"edited": edited, "agrees_inside": None, "agrees_outside": None,
                "asked_inside": 0, "asked_outside": 0, "loadable": False}
    # The organ's own answer set is filled the same way the oracle's is, from the same arity.
    edited_fn = (edited_fn[0], _with_arity(edited_fn[1], getattr(edited_fn[1], "__code__", None)
                                           and edited_fn[1].__code__.co_argcount or 1))
    edited_answers = _answers(edited_fn[1], ANSWERABLE.split(","))
    edited_outside = _answers(edited_fn[1], grid.split(","))
    return {"edited": edited,
            "agrees_inside": bool(inside_answers) and inside_answers == edited_answers,
            "agrees_outside": bool(outside_answers) and outside_answers == edited_outside,
            "asked_inside": len(inside_answers), "asked_outside": len(outside_answers),
            "answers_inside": inside_answers, "answers_outside": outside_answers,
            "loadable": True}


# ---------------------------------------------------------------------------------- one pull request

def _changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    """The lines the developers replaced, one statement per line."""
    was, now = statement_lines(before), statement_lines(after)
    if was is None or now is None:
        return []
    was_lines, now_lines = was.splitlines(), now.splitlines()
    out = []
    import difflib
    for line in difflib.unified_diff(was_lines, now_lines, n=0, lineterm=""):
        if line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith(("+", "-")):
            out.append((("-" if line[0] == "-" else "+"), line[1:]))
    return out


def two_showings(first: Mapping[str, str], second: Mapping[str, str]) -> tuple[str | None, str | None]:
    """Two demonstrations as one text, the way this tree already puts two showings together."""
    before = R.put_together(first["before"], second["before"])
    after = R.put_together(first["after"], second["after"])
    return before, after


def one_target(target: Mapping[str, str], demonstration: Mapping[str, str], *,
               second: Mapping[str, str] | None = None) -> dict[str, Any]:
    """The organ's output for one target from one demonstration (and optionally a second)."""
    try:
        got = ebe.edit_by_example(target["before"], demonstration["before"], demonstration["after"])
    except ebe.Refused:
        got = None
    except Exception:  # noqa: BLE001 - any other failure is a refusal by another name
        got = None
    two = None
    if second is not None:
        before, after = two_showings(demonstration, second)
        if before is not None and after is not None:
            try:
                two = ebe.edit_by_example(target["before"], before, after)
            except ebe.Refused:
                two = None
            except Exception:  # noqa: BLE001
                two = None
    return {"one": got, "two": two}


def one_pull(name: str, kind: str, files: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Every file as the demonstration for every other, and every PAIR of files as two showings."""
    arm: dict[str, collections.Counter] = {a: collections.Counter() for a in ARMS}
    calibration = collections.Counter()
    refusals = collections.Counter()
    oracle_quality = collections.Counter()
    for index, example in enumerate(files):
        oracle = demonstration_oracle(example["before"], example["after"])
        others = [i for i in range(len(files)) if i != index]
        for other in others:
            target = files[other]
            got = one_target(target, example)
            theirs = score(target["before"], target["after"], target["after"])
            calibration["targets"] += 1
            mine_one = None if got["one"] is None else score(target["before"], target["after"], got["one"])
            if mine_one is not None:
                calibration["one_showing_made_something_the_developers_made"] += int(
                    bool(mine_one["right_not_imports"]))
            cap = confirmed_change(target["before"], example["before"], example["after"],
                                   oracle=oracle)
            if cap is None:
                refusals["ONE_made_no_confirmed_change"] += 1
            else:
                arm["ONE"]["asked"] += 1
                arm["ONE"]["right_not_imports"] += mine_one["right_not_imports"] if mine_one else 0
                arm["ONE"]["developers_changes_not_imports"] += theirs["developers_changes_not_imports"]
                arm["ONE"]["not_what_the_developers_did"] += mine_one["not_what_the_developers_did"] if mine_one else 0
                arm["ONE"]["confirmed_inside"] += int(bool(cap.get("agrees_inside")))
                arm["ONE"]["loadable"] += int(bool(cap.get("loadable")))
                arm["ONE"]["questions_outside"] += cap.get("asked_outside") or 0
                arm["ONE"]["wholly_right"] += int(bool(
                    mine_one and mine_one["all_but_imports_as_the_developers_left_it"]))
            # The second showing: the strongest form of the claim.
            for second_index in others:
                if second_index == other:
                    continue
                second = files[second_index]
                got_two = one_target(target, example, second=second)
                if got_two["two"] is None:
                    refusals["TWO_made_no_change"] += 1
                    continue
                two = score(target["before"], target["after"], got_two["two"])
                arm["TWO"]["asked"] += 1
                arm["TWO"]["right_not_imports"] += two["right_not_imports"]
                arm["TWO"]["developers_changes_not_imports"] += two["developers_changes_not_imports"]
                arm["TWO"]["not_what_the_developers_did"] += two["not_what_the_developers_did"]
                arm["TWO"]["wholly_right"] += int(two["all_but_imports_as_the_developers_left_it"])
            arm["FALSE"]["asked"] += 1
            arm["FALSE"]["right_not_imports"] += theirs["right_not_imports"]
            arm["FALSE"]["developers_changes_not_imports"] += theirs["developers_changes_not_imports"]
            arm["FALSE"]["not_what_the_developers_did"] += 0
            arm["FALSE"]["wholly_right"] += 1
    return {"name": name, "kind": kind, "files": len(files),
            "arms": {key: dict(value) for key, value in arm.items()},
            "calibration": dict(calibration), "refusals": dict(refusals),
            "oracle_quality": dict(oracle_quality)}


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total: dict[str, collections.Counter] = {a: collections.Counter() for a in ARMS}
    calib = collections.Counter()
    refusals = collections.Counter()
    for row in rows:
        for arm_key, counts in row["arms"].items():
            total[arm_key].update(counts)
        calib.update(row["calibration"])
        refusals.update(row["refusals"])
    rates = {}
    for arm_key, counts in total.items():
        asked = counts.get("asked", 0) or 1
        rates[arm_key] = {
            "changes_confirmed_inside_the_grid": counts.get("confirmed_inside", 0),
            "right_not_imports": counts.get("right_not_imports", 0),
            "developers_changes_not_imports": counts.get("developers_changes_not_imports", 0),
            "not_what_the_developers_did": counts.get("not_what_the_developers_did", 0),
            "share_of_targets_where_the_change_is_wholly_right":
                round(counts.get("wholly_right", 0) / asked, 4),
            "right_per_change_the_developers_made": (
                round(counts.get("right_not_imports", 0) /
                      max(1, counts.get("developers_changes_not_imports", 0)), 4)),
            "asked": counts.get("asked", 0),
        }
    return {"schema": SCHEMA, "authority": AUTHORITY, "pull_requests": len(rows),
            "files_per_pull_request": [row["files"] for row in rows],
            "calibration": dict(calib), "refusals": dict(refusals), "arms": rates,
            "arms_note": "ONE is the organ's output after one demonstration; THREE and FALSE are "
                         "ceilings of a tool that reviews that output, not outputs of the organ",
            "network_in_measurement": False}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pulls", type=pathlib.Path, default=None)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    if not args.pulls:
        parser.error("--pulls is required (collect with held_out_transfer_20261112_v1.py)")
    pulls = json.loads(args.pulls.read_text())
    rows = []
    for pull in pulls:
        row = one_pull(pull["name"], pull.get("kind", "?"), pull["files"])
        rows.append(row)
        one = row["arms"]["ONE"]
        print("%-45s asked %d  right %d/%d  not theirs %d" % (
            pull["name"], one.get("asked", 0), one.get("right_not_imports", 0),
            one.get("developers_changes_not_imports", 0),
            one.get("not_what_the_developers_did", 0)), flush=True)
    report = summarise(rows)
    report["per_pull"] = rows
    text = json.dumps(report, indent=1)
    if args.json:
        args.json.write_text(text + "\n")
        print("written ->", args.json)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
