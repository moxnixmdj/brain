#!/usr/bin/env python3
"""Choose the two demonstrations that apply, not the two that are nearby.

The owner's question is generalization: the same kind of task comes back on a different file,
and one demonstration does not carry. The tree's record already shows the shape -- one example
recovers 15.8% of a repeated change at 95.5% precision, two recover 24.0% -- but the record
averages over **every pair** of demonstrations. It never asks which pair.

This module asks it. For each of the fifteen pull requests in
``REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json`` it enumerates every pair of changed files,
learns the pair's rules with the shipped learner, and measures what those rules do to the four
remaining files. Then it compares four ways of choosing the pair:

    all pairs   the record's own average: every pair, including the pairs that cannot be learned
    path        the first two files in path order -- an arbitrary, reproducible choice
    largest     the two largest files -- a plausible but outcome-blind choice
    chosen      the pair whose rules change the most places when run on the four target files,
                before any target outcome is seen (self-simulation)
    best        the pair that actually recovers the most -- an oracle, not a policy

The point is not that "chosen" beats a straw man. The point is that **the choice of the two
demonstrations moves coverage more than the second demonstration does**: the all-pair average is
23.1%, an arbitrary pair is 18-20%, and the pair chosen by self-simulation is 61.8% -- 97% of the
oracle-best 63.7%. No model, no outcome, no new operator.

WHY IT IS ALLOWED TO LOOK AT THE TARGET FILES.

A demonstration is spent to teach a rule that will be applied somewhere. The agent can see the
files it will edit; it cannot see what the developers did to them. So it may run its own learner
on those files and count where the rule applies. That is what "chosen" does. It never reads a
target's after-text to choose. "best" does, and is reported only as a ceiling.

WHAT THIS DOES NOT SAY.

That the chosen pair is right: its precision is 87.4%, below the all-pair 92.9%, because a pair
that applies in more places also makes more changes. That the five pull requests at zero are a
selection failure: no pair recovers anything there; the algebra cannot express the change. That
this is generalization in general: it is generalization inside one repeated change kind, where a
second, different use of the changed code makes the rule wider.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import itertools
import json
import pathlib
import re
import statistics
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as E
from canonical.tools.repeated_change_one_example_measure_v1 import score, statement_lines

SCHEMA = "DEMONSTRATION_PAIR_SELECTION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
RECORD = "canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json"
COLLECT = ("python3 canonical/tools/repeated_change_one_example_measure_v1.py "
           "--collect /tmp/pulls.json --as-recorded-in " + RECORD)


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _empty() -> dict[str, int]:
    return {"right_not_imports": 0, "developers_changes_not_imports": 0,
            "organ_changes": 0, "right": 0, "not_what_the_developers_did": 0}


def pair_row(files: Sequence[Mapping[str, str]], first: int, second: int) -> dict[str, Any]:
    """One pair as the demonstrations, every other file as the target.

    ``pred`` is the number of places the rules change when run on the target files BEFORE their
    after-text is read. ``pred_files`` is how many target files they change at all. Both are
    available to a policy; ``right`` and ``coverage`` are the outcome and are not.
    """
    total = _empty()
    predicted_places = 0
    predicted_files = 0
    refused = None
    try:
        rules = E.learn_all([(files[first]["before"], files[first]["after"]),
                             (files[second]["before"], files[second]["after"])])
    except Exception as exc:                       # the learner's own refusal is the record
        rules, refused = None, type(exc).__name__ + ": " + str(exc)[:160]
    for target in range(len(files)):
        if target in (first, second):
            continue
        got = None
        if rules is not None:
            try:
                got, places = E.rewrite(rules, files[target]["before"], "target")
                if got is not None:
                    predicted_places += int(places or 0)
                    predicted_files += 1
            except Exception:
                got = None
        try:
            row = score(files[target]["before"], files[target]["after"], got)
        except Exception:
            row = {}
        for key in total:
            total[key] += int(row.get(key) or 0)
    developers = total["developers_changes_not_imports"]
    return {
        "pair": [first, second],
        "learnable": rules is not None,
        "refused": refused,
        "pred": predicted_places,
        "pred_files": predicted_files,
        **total,
        "coverage": round(total["right_not_imports"] / developers, 6) if developers else 0.0,
        "precision": (round(total["right_not_imports"] / total["organ_changes"], 6)
                      if total["organ_changes"] else None),
    }


def choose(pairs: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """The pair whose rules reach the most target places, using nothing but self-simulation.

    Ties go to the pair that reaches more files, then to the lower indices. No outcome key is
    consulted, so this function cannot see the answer.
    """
    return max(pairs, key=lambda row: (row["pred"], row["pred_files"],
                                       -row["pair"][0], -row["pair"][1]))


def best(pairs: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """The oracle: the pair that actually recovers the most. A ceiling, not a policy."""
    return max(pairs, key=lambda row: (row["coverage"], row["right"],
                                       -row["pair"][0], -row["pair"][1]))


def _named_pair(pairs: Sequence[Mapping[str, Any]], indices: Sequence[int]) -> Mapping[str, Any]:
    wanted = set(indices)
    for row in pairs:
        if set(row["pair"]) == wanted:
            return row
    raise KeyError("no pair %s" % sorted(wanted))


def one_pull_request(files: Sequence[Mapping[str, str]], name: str = "") -> dict[str, Any]:
    pairs = [pair_row(files, a, b) for a, b in itertools.combinations(range(len(files)), 2)]
    by_path = sorted(range(len(files)), key=lambda index: files[index]["path"])
    by_size = sorted(range(len(files)), key=lambda index: -len(files[index]["before"]))
    return {
        "name": name,
        "files": [file["path"] for file in files],
        "pairs": pairs,
        "path": _named_pair(pairs, by_path[:2]),
        "largest": _named_pair(pairs, by_size[:2]),
        "chosen": choose(pairs),
        "best": best(pairs),
    }


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def pooled(selected):
        right = sum(row["right_not_imports"] for row in selected)
        developers = sum(row["developers_changes_not_imports"] for row in selected)
        organ = sum(row["organ_changes"] for row in selected)
        return {"right": right, "developers_changes": developers, "organ_changes": organ,
                "coverage": round(right / developers, 6) if developers else None,
                "precision": round(right / organ, 6) if organ else None}

    every_pair = [pair for row in rows for pair in row["pairs"]]
    out = {
        "pull_requests": len(rows),
        "pairs": len(every_pair),
        "all_pairs": pooled(every_pair),
        "path": pooled([row["path"] for row in rows]),
        "largest": pooled([row["largest"] for row in rows]),
        "chosen": pooled([row["chosen"] for row in rows]),
        "best": pooled([row["best"] for row in rows]),
    }
    out["mean_coverage_per_pull_request"] = {
        "all_pairs": round(statistics.mean(statistics.mean([p["coverage"] for p in row["pairs"]])
                                           for row in rows), 6),
        "chosen": round(statistics.mean(row["chosen"]["coverage"] for row in rows), 6),
        "best": round(statistics.mean(row["best"]["coverage"] for row in rows), 6),
    }
    out["chosen_is_oracle_best"] = sum(1 for row in rows if row["chosen"]["pair"] == row["best"]["pair"])
    out["chosen_over_all_pairs"] = round(out["chosen"]["coverage"] / out["all_pairs"]["coverage"], 4)
    out["chosen_over_oracle"] = round(out["chosen"]["coverage"] / out["best"]["coverage"], 4)
    return out


def measure(pulls: Sequence[Mapping[str, Any]],
            say=lambda line: None) -> list[dict[str, Any]]:
    rows = []
    for pull in pulls:
        started = time.time()
        row = one_pull_request(pull["files"], pull["name"])
        row.update(kind=pull.get("kind"), query=pull.get("query"), title=pull.get("title"),
                   seconds=round(time.time() - started, 1))
        rows.append(row)
        say("%-45s path %.3f  largest %.3f  chosen %.3f  best %.3f  (%s places, %.1f s)"
            % (pull["name"], row["path"]["coverage"], row["largest"]["coverage"],
               row["chosen"]["coverage"], row["best"]["coverage"],
               row["chosen"]["pred"], row["seconds"]))
    return rows


def report(pulls_path: pathlib.Path) -> dict[str, Any]:
    pulls = json.loads(pulls_path.read_text(encoding="utf-8"))
    rows = measure(pulls, say=lambda line: print(line, flush=True))
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "organ": ORGAN,
        "organ_sha256": _sha(ROOT / ORGAN),
        "corpus_sha256": _sha(pulls_path),
        "baseline_record": RECORD,
        "baseline_two_example_coverage": 0.2396,
        "collect": COLLECT,
        "summary": aggregate(rows),
        "per_pull_request": rows,
        "limits": [
            "One corpus: 15 merged pull requests found because they repeat one change, six "
            "files each, no test of any of the fifteen projects run.",
            "The corpus was re-fetched from GitHub at the commits the record names and every "
            "file checked against its recorded SHA-256 before measurement.",
            "Precision is agreement with the developers, not correctness.",
            "The chosen pair is selected by running the shipped learner on the target files' "
            "before-text only; the oracle 'best' reads their after-text and is a ceiling.",
            "'chosen' is not the pair that is right, only the pair that applies most; its "
            "precision is lower than an arbitrary pair's.",
            "Refusals are the learner's; the five pull requests at zero are an algebra gap, "
            "not a selection failure.",
            "The organ is the one in this tree; its hash is recorded. A later change to it "
            "needs this measurement re-run.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pulls", type=pathlib.Path, required=True,
                        help="the corpus written by the collect command in this file")
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    rep = report(args.pulls)
    if args.json:
        args.json.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    summary = rep["summary"]
    print()
    print(f"{'policy':12} {'right':>6} {'developers':>11} {'coverage':>9} {'precision':>10}")
    for name in ("all_pairs", "path", "largest", "chosen", "best"):
        row = summary[name]
        print(f"{name:12} {row['right']:6d} {row['developers_changes']:11d} "
              f"{100 * row['coverage']:8.2f}% {100 * row['precision']:9.2f}%")
    print(f"\nchosen / all pairs {summary['chosen_over_all_pairs']}x   "
          f"chosen / oracle {summary['chosen_over_oracle']}   "
          f"chosen == oracle best on {summary['chosen_is_oracle_best']} of "
          f"{summary['pull_requests']}")
    print("mean per pull request: "
          + "  ".join(f"{k} {100 * v:.2f}%"
                      for k, v in summary["mean_coverage_per_pull_request"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
