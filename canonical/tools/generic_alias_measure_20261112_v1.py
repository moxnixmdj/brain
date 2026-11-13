#!/usr/bin/env python3
"""What the PEP 585 family operator buys on the repeated-change corpus.

One example per pull request, every other file a target. Two arms:

    base    the organ as shipped
    alias   the organ's result (or the target when it refused), then the family the example's
            one annotation showed: list <-> List, dict <-> Dict, set <-> Set, tuple <-> Tuple

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

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as E
from canonical.swe_kernel.taught_actions import generic_alias_v1 as G
from canonical.tools.repeated_change_one_example_measure_v1 import score

SCHEMA = "GENERIC_ALIAS_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
OPERATOR = "canonical/swe_kernel/taught_actions/generic_alias_v1.py"
CORPUS_RECORD = "canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json"
COLLECT = ("python3 canonical/tools/repeated_change_one_example_measure_v1.py "
           "--collect /tmp/pulls.json --as-recorded-in " + CORPUS_RECORD)
ARMS = ("base", "alias")


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _empty() -> dict[str, int]:
    return {"right": 0, "developers": 0, "organ": 0, "asked": 0, "edited": 0,
            "wrong": 0, "whole": 0, "changed_files": 0}


def _add(total: dict[str, int], row: Mapping[str, Any], edited: bool, changed: bool = False) -> None:
    total["right"] += int(row["right_not_imports"])
    total["developers"] += int(row["developers_changes_not_imports"])
    total["organ"] += int(row["organ_changes"])
    total["asked"] += 1
    total["edited"] += int(edited)
    total["wrong"] += int(row["not_what_the_developers_did"])
    total["whole"] += int(bool(row["the_whole_file_as_the_developers_left_it"]))
    total["changed_files"] += int(changed)


def _rate(total: Mapping[str, int]) -> dict[str, Any]:
    return {
        "asked": total["asked"],
        "edited": total["edited"],
        "changed_files": total["changed_files"],
        "right": total["right"],
        "developers_changes": total["developers"],
        "organ_changes": total["organ"],
        "coverage": round(total["right"] / total["developers"], 6) if total["developers"] else None,
        "precision": round(total["right"] / total["organ"], 6) if total["organ"] else None,
        "wrong_changes": total["wrong"],
        "whole_files": total["whole"],
    }


def _text(value):
    if isinstance(value, tuple):
        return value[0]
    return value


def one_pull_request(files: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    arms = {name: _empty() for name in ARMS}
    for example_number, example in enumerate(files):
        try:
            rules = E.learn(example["before"], example["after"])
        except Exception:
            rules = None
        for target_number, target in enumerate(files):
            if target_number == example_number:
                continue
            base = _text(_attempt(E.rewrite, rules, target["before"], "target")) if rules is not None else None
            _add(arms["base"], score(target["before"], target["after"], base), base is not None)
            try:
                alias, _ = G.apply(base if base is not None else target["before"],
                                   example["before"], example["after"])
            except Exception:
                alias = None
            _add(arms["alias"], score(target["before"], target["after"],
                                      alias if alias is not None else base),
                 (alias if alias is not None else base) is not None, alias is not None)
    return {"files": len(files), **{name: _rate(arms[name]) for name in ARMS}}


def _attempt(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception:
        return None


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
            totals[name]["changed_files"] += row[name]["changed_files"]
            totals[name]["right"] += row[name]["right"]
            totals[name]["developers"] += row[name]["developers_changes"]
            totals[name]["organ"] += row[name]["organ_changes"]
            totals[name]["wrong"] += row[name]["wrong_changes"]
            totals[name]["whole"] += row[name]["whole_files"]
        say("%-45s base %3d  alias %3d" % (pull["name"], row["base"]["right"], row["alias"]["right"]))
    summary = {name: _rate(totals[name]) for name in ARMS}
    summary["alias"]["gain_right"] = summary["alias"]["right"] - summary["base"]["right"]
    summary["alias"]["gain_coverage"] = round(
        (summary["alias"]["coverage"] or 0) - (summary["base"]["coverage"] or 0), 6)
    summary["alias"]["gain_precision"] = round(
        (summary["alias"]["precision"] or 0) - (summary["base"]["precision"] or 0), 6)
    summary["alias"]["pull_requests_improved"] = sum(
        1 for row in per_pull.values() if row["alias"]["right"] > row["base"]["right"])
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
            "The family is knowledge (the PEP 585 pairs); the example supplies only the "
            "direction. A project that changes one pair and deliberately keeps another is not "
            "distinguished.",
            "Only bare-name subscripts are changed; `typing.List[...]` written qualified, and "
            "`Callable`/`Iterable` moved to `collections.abc`, are not this operator.",
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
    print(f"{'arm':8} {'right':>6} {'developers':>11} {'coverage':>9} {'precision':>10} "
          f"{'wrong':>6} {'whole':>6} {'gain':>6}")
    for name in ARMS:
        row = rep["summary"][name]
        print(f"{name:8} {row['right']:6d} {row['developers_changes']:11d} "
              f"{100 * (row['coverage'] or 0):8.2f}% {100 * (row['precision'] or 0):9.2f}% "
              f"{row['wrong_changes']:6d} {row['whole_files']:6d} {row.get('gain_right', ''):>6}")
    row = rep["summary"]["alias"]
    print(f"alias: {row['pull_requests_improved']} pull requests improved, "
          f"coverage {100 * row['gain_coverage']:+.2f} pp, precision {100 * row['gain_precision']:+.2f} pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
