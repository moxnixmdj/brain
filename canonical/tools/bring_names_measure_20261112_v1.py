#!/usr/bin/env python3
"""What bringing a name the file already imports buys on the repeated-change corpus.

One example per pull request, every other file a target. Two arms:

    base            the organ as shipped
    brought         bring the names the lesson needs into the target's existing import line,
                    then run the organ's own gate (``leave_unshown=False``)
    brought_shown   the same, with the organ's ``leave_unshown=True``

No model, no network, no test of any of the fifteen projects. Precision is agreement with the
developers, not correctness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.taught_actions import bring_names_v1 as B
from canonical.swe_kernel.taught_actions import edit_by_example_v1 as E
from canonical.tools.repeated_change_one_example_measure_v1 import score

SCHEMA = "BRING_NAMES_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
OPERATOR = "canonical/swe_kernel/taught_actions/bring_names_v1.py"
CORPUS_RECORD = "canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json"
COLLECT = ("python3 canonical/tools/repeated_change_one_example_measure_v1.py "
           "--collect /tmp/pulls.json --as-recorded-in " + CORPUS_RECORD)
ARMS = ("base", "brought", "brought_shown")


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _empty() -> dict[str, int]:
    return {"right": 0, "developers": 0, "organ": 0, "asked": 0, "edited": 0, "brought_files": 0,
            "wrong": 0, "whole": 0, "all_but_imports": 0}


def _add(total: dict[str, int], row: Mapping[str, Any], edited: bool, brought: bool = False) -> None:
    total["right"] += int(row["right_not_imports"])
    total["developers"] += int(row["developers_changes_not_imports"])
    total["organ"] += int(row["organ_changes"])
    total["asked"] += 1
    total["edited"] += int(edited)
    total["brought_files"] += int(brought)
    total["wrong"] += int(row["not_what_the_developers_did"])
    total["whole"] += int(bool(row["the_whole_file_as_the_developers_left_it"]))
    total["all_but_imports"] += int(bool(row["all_but_imports_as_the_developers_left_it"]))


def _rate(total: Mapping[str, int]) -> dict[str, Any]:
    return {
        "asked": total["asked"],
        "edited": total["edited"],
        "brought_files": total["brought_files"],
        "right": total["right"],
        "developers_changes": total["developers"],
        "organ_changes": total["organ"],
        "coverage": round(total["right"] / total["developers"], 6) if total["developers"] else None,
        "precision": round(total["right"] / total["organ"], 6) if total["organ"] else None,
        "wrong_changes": total["wrong"],
        "whole_files": total["whole"],
        "all_but_imports_files": total["all_but_imports"],
    }


def _attempt(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception:
        return None


def _text(value):
    if isinstance(value, tuple):
        return value[0]
    return value


def one_pull_request(files: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    arms = {name: _empty() for name in ARMS}
    for example_number, example in enumerate(files):
        rules = _attempt(E.learn, example["before"], example["after"])
        for target_number, target in enumerate(files):
            if target_number == example_number:
                continue
            base = _text(_attempt(E.rewrite, rules, target["before"], "target")) if rules is not None else None
            _add(arms["base"], score(target["before"], target["after"], base), base is not None)
            brought_text, brought = _attempt(B.bring, target["before"], rules) if rules is not None else (None, {})
            if brought_text is not None:
                got = _text(_attempt(B.rewrite_with_brought_names, rules, target["before"], "target",
                                     leave_unshown=False))
                if got is None:
                    got = _text(_attempt(E.rewrite, rules, brought_text, "target"))
            else:
                got = base
            _add(arms["brought"], score(target["before"], target["after"], got), got is not None,
                 bool(brought))
            got_shown = _text(_attempt(B.rewrite_with_brought_names, rules, target["before"], "target",
                                       leave_unshown=True)) if rules is not None else None
            _add(arms["brought_shown"],
                 score(target["before"], target["after"], got_shown), got_shown is not None,
                 bool(brought))
    return {"files": len(files), **{name: _rate(arms[name]) for name in ARMS}}


def measure(pulls: Sequence[Mapping[str, Any]], say=lambda line: None) -> dict[str, Any]:
    per_pull, totals = {}, {name: _empty() for name in ARMS}
    for pull in pulls:
        started = time.time()
        row = one_pull_request(pull["files"])
        row.update(name=pull["name"], kind=pull.get("kind"), seconds=round(time.time() - started, 1))
        per_pull[pull["name"]] = row
        for name in ARMS:
            totals[name]["asked"] += row[name]["asked"]
            totals[name]["edited"] += row[name]["edited"]
            totals[name]["brought_files"] += row[name]["brought_files"]
            totals[name]["right"] += row[name]["right"]
            totals[name]["developers"] += row[name]["developers_changes"]
            totals[name]["organ"] += row[name]["organ_changes"]
            totals[name]["wrong"] += row[name]["wrong_changes"]
            totals[name]["whole"] += row[name]["whole_files"]
            totals[name]["all_but_imports"] += row[name]["all_but_imports_files"]
        say("%-45s base %3d  brought %3d  brought_shown %3d"
            % (pull["name"], row["base"]["right"], row["brought"]["right"],
               row["brought_shown"]["right"]))
    summary = {name: _rate(totals[name]) for name in ARMS}
    for name in ARMS[1:]:
        summary[name]["gain_right"] = summary[name]["right"] - summary["base"]["right"]
        summary[name]["gain_coverage"] = round(
            (summary[name]["coverage"] or 0) - (summary["base"]["coverage"] or 0), 6)
        summary[name]["gain_precision"] = round(
            (summary[name]["precision"] or 0) - (summary["base"]["precision"] or 0), 6)
        summary[name]["pull_requests_improved"] = sum(
            1 for row in per_pull.values() if row[name]["right"] > row["base"]["right"])
    return {"summary": summary, "per_pull_request": per_pull}


def report(pulls_path: pathlib.Path) -> dict[str, Any]:
    pulls = json.loads(pulls_path.read_text(encoding="utf-8"))
    body = measure(pulls, say=lambda line: print(line, flush=True))
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "organ": ORGAN,
        "organ_sha256": _sha(ROOT / ORGAN),
        "operator": OPERATOR,
        "operator_sha256": _sha(ROOT / OPERATOR),
        "corpus_sha256": _sha(pulls_path),
        "collect": COLLECT,
        "summary": body["summary"],
        "per_pull_request": body["per_pull_request"],
        "limits": [
            "One corpus: 15 merged pull requests found because they repeat one change, six "
            "files each; no test of any of the fifteen projects was run.",
            "Precision is agreement with the developers, not correctness.",
            "Only a name imported by a `from module import ...` line the example wrote down is "
            "brought; a relative import or a module not importable from the tree is refused.",
            "The operator changes only an import line; the organ still decides whether the "
            "lesson applies.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pulls", type=pathlib.Path, required=True)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    rep = report(args.pulls)
    if args.json:
        args.json.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print()
    print(f"{'arm':14} {'right':>6} {'developers':>11} {'coverage':>9} {'precision':>10} "
          f"{'wrong':>6} {'whole':>6} {'gain':>6}")
    for name in ARMS:
        row = rep["summary"][name]
        print(f"{name:14} {row['right']:6d} {row['developers_changes']:11d} "
              f"{100 * (row['coverage'] or 0):8.2f}% {100 * (row['precision'] or 0):9.2f}% "
              f"{row['wrong_changes']:6d} {row['whole_files']:6d} {row.get('gain_right', ''):>6}")
    for name in ARMS[1:]:
        row = rep["summary"][name]
        print(f"{name}: {row['pull_requests_improved']} pull requests improved, "
              f"coverage {100 * row['gain_coverage']:+.2f} pp, "
              f"precision {100 * row['gain_precision']:+.2f} pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
