#!/usr/bin/env python3
"""What two expression operators buy on the tree's repeated-change corpus.

One example, every other file a target. The organ runs as it is; then each operator is applied to
the result (or to the target when the organ refused), and the developers' changes are the score.

Arms:

    base       the organ alone
    rename     + method rename (same receiver, same arguments)
    fstring    + string concatenation to an f-string (a candidate generator)
    both       rename, then f-string

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
from canonical.swe_kernel.taught_actions import expression_operator_pack_v1 as P
from canonical.tools.repeated_change_one_example_measure_v1 import score

SCHEMA = "EXPRESSION_OPERATOR_PACK_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
PACK = "canonical/swe_kernel/taught_actions/expression_operator_pack_v1.py"
CORPUS_RECORD = "canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json"
COLLECT = ("python3 canonical/tools/repeated_change_one_example_measure_v1.py "
           "--collect /tmp/pulls.json --as-recorded-in " + CORPUS_RECORD)
ARMS = ("base", "rename", "fstring", "both")


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _empty() -> dict[str, int]:
    return {"right": 0, "developers": 0, "organ": 0, "asked": 0, "edited": 0}


def _add(total: dict[str, int], row: Mapping[str, Any], edited: bool) -> None:
    total["right"] += int(row["right_not_imports"])
    total["developers"] += int(row["developers_changes_not_imports"])
    total["organ"] += int(row["organ_changes"])
    total["asked"] += 1
    total["edited"] += int(edited)


def _rate(total: Mapping[str, int]) -> dict[str, Any]:
    return {
        "asked": total["asked"],
        "edited": total["edited"],
        "right": total["right"],
        "developers_changes": total["developers"],
        "organ_changes": total["organ"],
        "coverage": round(total["right"] / total["developers"], 6) if total["developers"] else None,
        "precision": round(total["right"] / total["organ"], 6) if total["organ"] else None,
    }


def one_pull_request(files: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    arms = {name: _empty() for name in ARMS}
    for example_number, example in enumerate(files):
        got = None
        try:
            rules = E.learn(example["before"], example["after"])
            got, _ = E.rewrite(rules, example["before"], "the example")
        except Exception:
            rules = None
        base_text = None
        for target_number, target in enumerate(files):
            if target_number == example_number:
                continue
            base = None
            if rules is not None:
                try:
                    base, _ = E.rewrite(rules, target["before"], "target")
                except Exception:
                    base = None
            source = base if base is not None else target["before"]
            _add(arms["base"], score(target["before"], target["after"], base), base is not None)
            for arm, operators in (("rename", ("rename",)), ("fstring", ("fstring",)),
                                   ("both", ("rename", "fstring"))):
                packed = P.apply_pack(source, example["before"], example["after"], operators)
                text = packed["text"] if packed["text"] is not None else base
                _add(arms[arm], score(target["before"], target["after"], text), text is not None)
    return {"files": len(files), **{name: _rate(arms[name]) for name in ARMS}}


def measure(pulls: Sequence[Mapping[str, Any]],
            say=lambda line: None) -> dict[str, Any]:
    per_pull, totals = {}, {name: _empty() for name in ARMS}
    for pull in pulls:
        started = time.time()
        row = one_pull_request(pull["files"])
        row.update(name=pull["name"], kind=pull.get("kind"), seconds=round(time.time() - started, 1))
        per_pull[pull["name"]] = row
        for name in ARMS:
            totals[name]["asked"] += row[name]["asked"]
            totals[name]["edited"] += row[name]["edited"]
            totals[name]["right"] += row[name]["right"]
            totals[name]["developers"] += row[name]["developers_changes"]
            totals[name]["organ"] += row[name]["organ_changes"]
        say("%-45s base %.2f%%  +rename %.2f%%  +fstring %.2f%%  +both %.2f%%"
            % (pull["name"], 100 * (row["base"]["coverage"] or 0),
               100 * (row["rename"]["coverage"] or 0),
               100 * (row["fstring"]["coverage"] or 0),
               100 * (row["both"]["coverage"] or 0)))
    summary = {name: _rate(totals[name]) for name in ARMS}
    for name in ("rename", "fstring", "both"):
        summary[name]["gain_right"] = summary[name]["right"] - summary["base"]["right"]
        summary[name]["gain_coverage"] = round(
            (summary[name]["coverage"] or 0) - (summary["base"]["coverage"] or 0), 6)
        summary[name]["gain_precision"] = round(
            (summary[name]["precision"] or 0) - (summary["base"]["precision"] or 0), 6)
        summary[name]["pull_requests_improved"] = sum(
            1 for row in per_pull.values() if (row[name]["right"] > row["base"]["right"]))
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
        "pack": PACK,
        "pack_sha256": _sha(ROOT / PACK),
        "corpus_sha256": _sha(pulls_path),
        "collect": COLLECT,
        "summary": body["summary"],
        "per_pull_request": body["per_pull_request"],
        "limits": [
            "One corpus: 15 merged pull requests found because they repeat one change, six "
            "files each; no test of any of the fifteen projects was run.",
            "Precision is agreement with the developers, not correctness.",
            "The f-string arm is a candidate generator: it converts every string-constant "
            "concatenation, not only the developers'. Use it behind a test.",
            "The rename arm assumes a method rename keeps the arguments; a rename that also "
            "changes the signature is not this operator.",
            "The organ's hash is recorded; a later change to it needs this measurement re-run.",
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
    print(f"{'arm':8} {'right':>6} {'developers':>11} {'coverage':>9} {'precision':>10} {'gain':>6}")
    for name in ARMS:
        row = rep["summary"][name]
        gain = row.get("gain_right", "")
        print(f"{name:8} {row['right']:6d} {row['developers_changes']:11d} "
              f"{100 * (row['coverage'] or 0):8.2f}% {100 * (row['precision'] or 0):9.2f}% {gain:>6}")
    for name in ("rename", "fstring", "both"):
        row = rep["summary"][name]
        print(f"{name}: {row['pull_requests_improved']} pull requests improved, "
              f"coverage {100 * row['gain_coverage']:+.2f} pp, "
              f"precision {100 * row['gain_precision']:+.2f} pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
