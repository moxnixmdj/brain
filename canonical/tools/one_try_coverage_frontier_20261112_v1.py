#!/usr/bin/env python3
"""One example of a repeated change covers a fraction, and the refusals name the frontier.

The question the owner keeps asking is whether one experience is enough. The tree already
contains the closest thing to a fair test: fifteen merged pull requests in which other people
made one kind of change in many files. One changed file is the demonstration; every other
changed file is a place to repeat it; what the developers did there is the answer.

This module does not run the organ again. It reads the record the organ already produced
(``canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json``) and asks three
questions the prose kept answering in different units:

1. DOSE. What share of the developers' changes does one example recover, at what precision,
   and what does a second example add? Coverage is ``right / developers' changes``; precision
   is ``right / the organ's changes``. They are different fractions and have been conflated.

2. SPREAD. One example is not one number. Per pull request, how often does it recover nothing,
   and how far apart are the best and worst change kinds?

3. FRONTIER. Why did it refuse? The record keeps the learner's own words for every refusal.
   Grouped, they say which operator classes are missing -- and an operator class is bought in
   code, never in experience.

WHAT THIS DOES NOT SAY.

That fixing a refusal class recovers every change in the files it refused: the counts are
ASKINGS, not changes, and the record does not carry the text of refused files. That the
organ's precision is correctness: no test was run; precision is agreement with the developers.
That one example is useless: it is highly precise where it applies, and that is the part worth
keeping.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORD = ROOT / "canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json"
SCHEMA = "ONE_TRY_COVERAGE_FRONTIER_V1"

# The record's six runs, named by what they are rather than by their position.
RUNS = {
    "older_organ_whole_file": "1_the_organ_before_main_changed_it__the_whole_file_or_nothing",
    "current_whole_file": "2_the_organ_as_main_has_it_now__the_whole_file_or_nothing",
    "current_leave_unshown": "3_the_organ_as_main_has_it_now__what_was_not_shown_is_left_alone",
    "current_after_6699_whole_file": "4_the_organ_after_pull_request_6699__the_whole_file_or_nothing",
    "current_after_6699_leave_unshown": "5_the_organ_after_pull_request_6699__what_was_not_shown_is_left_alone",
    "ceiling_every_try_kept": "6_the_organ_after_pull_request_6699__every_try_kept__the_ceiling_of_repeat_tried",
}

# Refusal classes, matched by a stable phrase in the learner's own sentence. Order matters:
# the first phrase that matches names the class.
REFUSALS = (
    ("NO_FORM_IN_FILE", "nothing in the file has the form"),
    ("IMPORT_ONLY_EXAMPLE", "hold the same code, apart from import"),
    ("BLOCK_SHAPE", "adds, removes or reshapes whole statements"),
    ("NAME_NOT_AVAILABLE", "does not define, import or receive"),
    ("CALL_SHAPE_NOT_SHOWN", "examples showed it called"),
    ("CONFLICTING_CONTEXT", "was changed, but the same code was left alone"),
    ("PARSE_MISMATCH", "does not parse to the intended code"),
    ("OVERLAP", "two places to change overlap"),
    # The record truncates some sentences, so the "the examples showed it called" phrase is
    # not always present; what remains still names the use. This is a fallback, last.
    ("CALL_SHAPE_NOT_SHOWN", "called with"),
)
# NO_FORM_IN_FILE is not an operator gap: the demonstration's change simply does not occur in
# that file. EDITED is not a refusal. Everything else is a place an operator could, in
# principle, reach -- and must then be judged by a check.
NOT_AN_OPERATOR_GAP = frozenset({"NO_FORM_IN_FILE", "EDITED"})


def load(path: pathlib.Path = RECORD) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _arm(run: dict[str, Any], name: str) -> dict[str, Any]:
    arm = run[name]
    dev = arm["developers_changes_not_imports"]
    right = arm["right_not_imports"]
    organ = arm["organ_changes"]
    good = arm["right"]
    return {
        "asked": arm["asked"],
        "edited": arm["edited"],
        "developers_changes": dev,
        "right": right,
        "coverage": round(right / dev, 6) if dev else None,
        "organ_changes": organ,
        "organ_right": good,
        "precision": round(good / organ, 6) if organ else None,
        "not_what_the_developers_did": arm.get("not_what_the_developers_did"),
    }


def dose(record: dict[str, Any], run_key: str = "current_whole_file") -> dict[str, Any]:
    """One example and two examples on the same change kind, and what the second buys."""
    run = record["the_runs"][RUNS[run_key]]
    one = _arm(run, "one_example")
    two = _arm(run, "two_examples")
    marginal = None
    if one["coverage"] is not None and two["coverage"] is not None:
        marginal = round(two["coverage"] - one["coverage"], 6)
    return {
        "run": run_key,
        "one": one,
        "two": two,
        "second_example_buys_coverage": marginal,
        "second_example_buys_precision": (
            round(two["precision"] - one["precision"], 6)
            if one["precision"] is not None and two["precision"] is not None else None
        ),
    }


def spread(record: dict[str, Any], run_name: str = "run_2") -> dict[str, Any]:
    """Per pull request: one example's coverage, and how often it recovers nothing."""
    rows = []
    for pull, data in record["per_pull_request"][run_name].items():
        arm = data["one_example"]
        dev = arm["developers_changes_not_imports"]
        rows.append({
            "pull_request": pull,
            "coverage": round(arm["right_not_imports"] / dev, 6) if dev else None,
            "precision": arm.get("of_the_organs_changes_right"),
            "edited": arm.get("edited"),
            "asked": arm.get("asked"),
            "developers_changes": dev,
        })
    scored = [row["coverage"] for row in rows if row["coverage"] is not None]
    return {
        "run": run_name,
        "pull_requests": len(rows),
        "rows": rows,
        "zero": sum(1 for value in scored if value == 0.0),
        "at_most_one_percent": sum(1 for value in scored if value <= 0.01),
        "median": round(statistics.median(scored), 6) if scored else None,
        "mean": round(statistics.mean(scored), 6) if scored else None,
        "best": max(scored) if scored else None,
    }


def classify(reason: str) -> str:
    if reason == "edited":
        return "EDITED"
    for name, phrase in REFUSALS:
        if phrase in reason:
            return name
    return "OTHER"


def frontier(record: dict[str, Any], run_key: str = "current_whole_file") -> dict[str, Any]:
    """The learner's refusals, grouped, as a ranked list of missing operator classes."""
    run = record["the_runs"][RUNS[run_key]]
    why = run["one_example"].get("why_not") or {}
    counts: dict[str, int] = {}
    examples: dict[str, str] = {}
    for reason, count in why.items():
        name = classify(reason)
        counts[name] = counts.get(name, 0) + int(count)
        examples.setdefault(name, reason[:150])
    asked = int(run["one_example"]["asked"])
    addressable = sum(count for name, count in counts.items() if name not in NOT_AN_OPERATOR_GAP)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {
        "run": run_key,
        "asked": asked,
        "counts": counts,
        "share": {name: round(count / asked, 6) for name, count in counts.items()},
        "examples": examples,
        "operator_gap_askings": addressable,
        "operator_gap_share": round(addressable / asked, 6),
        "ranked_operator_gaps": [
            {"class": name, "askings": count, "share": round(count / asked, 6)}
            for name, count in ranked if name not in NOT_AN_OPERATOR_GAP and name != "OTHER"
        ],
    }


def report(record: dict[str, Any] | None = None) -> dict[str, Any]:
    record = record or load()
    return {
        "schema": SCHEMA,
        "record": str(RECORD.relative_to(ROOT)),
        "generated_utc": record.get("generated_utc"),
        "authority": record.get("authority"),
        "dose": {
            key: dose(record, key)
            for key in ("older_organ_whole_file", "current_whole_file",
                        "current_leave_unshown", "ceiling_every_try_kept")
        },
        "spread": spread(record),
        "frontier": frontier(record),
        "limits": [
            "The counts are the record's, not a new run; the organ was not re-measured.",
            "The record is a snapshot at 2026-11-12T17:19:18Z. edit_by_example_v1.py changed "
            "again in PR #6778 (+122 lines), so 'run 2' is not the organ now; re-run the writer "
            "before quoting these as current rates.",
            "No test was run in the record: precision is agreement with the developers.",
            "One record of fifteen pull requests, found because they repeat one change.",
            "Refusal counts are askings, not changes: fixing a class does not recover every "
            "change in the files it refused.",
            "The classes are the learner's own sentences grouped by a fixed phrase table; an "
            "unmatched sentence is OTHER and is printed, never hidden.",
        ],
    }


def _percent(value: float | None) -> str:
    return "  n/a " if value is None else f"{100.0 * value:6.2f}%"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", type=pathlib.Path, default=None,
                        help="write the whole report here")
    parser.add_argument("--record", type=pathlib.Path, default=RECORD)
    args = parser.parse_args(argv)

    rep = report(load(args.record))
    if args.json:
        args.json.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")

    print("ONE EXAMPLE RECOVERS A FRACTION -- coverage and precision are different fractions")
    print(f"record {rep['record']}   generated {rep['generated_utc']}")
    print()
    print(f"{'run':28} {'arm':13} {'coverage':>8} {'precision':>9} "
          f"{'edited/asked':>14} {'organ changes':>13}")
    names = {
        "older_organ_whole_file": "older organ (run 1)",
        "current_whole_file": "record run 2 (17:19Z)",
        "current_leave_unshown": "record run 3 (17:19Z)",
        "ceiling_every_try_kept": "every try kept (run 6)",
    }
    for key, row in rep["dose"].items():
        for arm in ("one", "two"):
            a = row[arm]
            print(f"{names[key]:28} {(arm + ' example') if arm == 'one' else 'two examples':13} {_percent(a['coverage']):>8} "
                  f"{_percent(a['precision']):>9} "
                  f"{str(a['edited']) + '/' + str(a['asked']):>14} {a['organ_changes']:>13}")
        print(f"{'':28} second example buys {_percent(row['second_example_buys_coverage'])} "
              f"of the developers' changes")
    print()

    sp = rep["spread"]
    print(f"PER PULL REQUEST (current organ, one example): {sp['pull_requests']} changes")
    print(f"  recovers nothing: {sp['zero']} of {sp['pull_requests']}   "
          f"at most 1%: {sp['at_most_one_percent']}   "
          f"median {_percent(sp['median'])}   best {_percent(sp['best'])}")
    print()

    fr = rep["frontier"]
    print(f"WHY IT REFUSED (current organ, one example, {fr['asked']} askings)")
    for row in sorted(fr["counts"].items(), key=lambda item: (-item[1], item[0])):
        name, count = row
        print(f"  {name:24} {count:4d}  {_percent(count / fr['asked'])}")
    print(f"  {'ORDINARY REFUSALS':24} {fr['operator_gap_askings']:4d}  "
          f"{_percent(fr['operator_gap_share'])}  <- operator classes, bought in code")
    if fr["counts"].get("OTHER"):
        print(f"  {'UNMATCHED (OTHER)':24} {fr['counts']['OTHER']:4d}  "
              f"{_percent(fr['share']['OTHER'])}  <- inspect by hand, not ranked")
    print()
    print("RANKED OPERATOR FRONTIER (askings, not changes)")
    for row in fr["ranked_operator_gaps"]:
        print(f"  {row['class']:24} {row['askings']:4d}  {_percent(row['share'])}")
    print()
    print("A class is a hypothesis about the next line of code, not a recovered change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
