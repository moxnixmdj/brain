#!/usr/bin/env python3
"""Do the operators transfer to pull requests they were not designed on?

Every measurement before this one used the same fifteen pull requests that the operators were
chosen on. That is an in-sample number. This tool collects a *separate* set of merged pull
requests, found by the same kind of title search, and runs the shipped organ and the PEP 585
operator on them with no change and no tuning:

    base    the organ as shipped
    alias   the organ's result, then the family the example's annotation showed

Two classes are collected:

    pep585  PEP 585 / built-in generics migrations (list <-> List, ...)
    utc     "replace utcnow" migrations

The second is included because the in-sample corpus had one spectacular success on it; the
question is whether that success was the class or the repository.

Collection is reproducible: `--collect` searches GitHub and writes the pull requests with their
file texts; `--record` writes the same pull requests without the texts, enough for anyone to
fetch the files again and check their hashes.
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
from canonical.tools import repeated_change_one_example_measure_v1 as R
from canonical.tools.repeated_change_one_example_measure_v1 import score

SCHEMA = "HELD_OUT_TRANSFER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
OPERATOR = "canonical/swe_kernel/taught_actions/generic_alias_v1.py"
ARMS = ("base", "alias")
QUERIES = (
    ("pep585", '"PEP 585"'),
    ("pep585", "built-in generics"),
    ("utc", "utcnow"),
    ("utc", "datetime.now(UTC)"),
)
DESIGN = frozenset({
    "openimis/openimis-be-core_py#414", "torproject/stem#155", "testing-cabal/testtools#335",
    "kuangjiafa/automagician#55", "RedHatInsights/advisor-backend#80",
    "Cytomine-ULiege/Cytomine-python-client#61", "unifyai/ivy#26932",
    "InterDigitalInc/CompressAI-Vision#40", "inveniosoftware/invenio-pidstore#189",
    "nipy/nibabel#1609", "jupyter/jupyter-sphinx#301", "fulcrumgenomics/fgpyo#300",
    "Prekzursil/env-inspector#72", "apache/libcloud#2217",
    "arigatoexpress/Project-Go-Forward#483",
})
PER_QUERY = 2


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _empty() -> dict[str, int]:
    return {"right": 0, "developers": 0, "organ": 0, "asked": 0, "edited": 0,
            "wrong": 0, "whole": 0, "changed_files": 0}


def _add(total: dict[str, int], row: Mapping[str, Any], edited: bool, changed: bool) -> None:
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
    return value[0] if isinstance(value, tuple) else value


def _attempt(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception:
        return None


def one_pull_request(files: Sequence[Mapping[str, str]],
                     check_names: bool = True) -> dict[str, Any]:
    arms = {name: _empty() for name in ARMS}
    for example_number, example in enumerate(files):
        rules = _attempt(E.learn, example["before"], example["after"])
        for target_number, target in enumerate(files):
            if target_number == example_number:
                continue
            base = _text(_attempt(E.rewrite, rules, target["before"], "target",
                                  check_names=check_names)) if rules is not None else None
            _add(arms["base"], score(target["before"], target["after"], base), base is not None, False)
            alias = None
            try:
                alias, did = G.apply(base if base is not None else target["before"],
                                     example["before"], example["after"])
            except Exception:
                alias, did = None, {}
            _add(arms["alias"], score(target["before"], target["after"],
                                      alias if alias is not None else base),
                 (alias if alias is not None else base) is not None, bool(did))
    return {"files": len(files), **{name: _rate(arms[name]) for name in ARMS}}


def measure(pulls: Sequence[Mapping[str, Any]], say=lambda line: None,
            check_names: bool = True) -> dict[str, Any]:
    per_pull = {}
    totals: dict[str, dict[str, dict[str, int]]] = {}
    for pull in pulls:
        started = time.time()
        row = one_pull_request(pull["files"], check_names=check_names)
        row.update(name=pull["name"], kind=pull.get("kind"), query=pull.get("query"),
                   title=pull.get("title"), seconds=round(time.time() - started, 1))
        per_pull[pull["name"]] = row
        kind = pull.get("kind", "unknown")
        totals.setdefault(kind, {name: _empty() for name in ARMS})
        for arm in ARMS:
            totals[kind][arm]["asked"] += row[arm]["asked"]
            totals[kind][arm]["edited"] += row[arm]["edited"]
            totals[kind][arm]["changed_files"] += row[arm]["changed_files"]
            totals[kind][arm]["right"] += row[arm]["right"]
            totals[kind][arm]["developers"] += row[arm]["developers_changes"]
            totals[kind][arm]["organ"] += row[arm]["organ_changes"]
            totals[kind][arm]["wrong"] += row[arm]["wrong_changes"]
            totals[kind][arm]["whole"] += row[arm]["whole_files"]
        base, alias = row["base"], row["alias"]
        say("%-50s %-7s base %3d/%3d  alias %3d  changed %2d  %4.1f s"
            % (pull["name"], kind, base["right"], base["developers_changes"],
               alias["right"], alias["changed_files"], row["seconds"]))
    by_kind = {}
    for kind, arms in totals.items():
        by_kind[kind] = {arm: _rate(arms[arm]) for arm in ARMS}
        for arm in ARMS:
            by_kind[kind][arm]["pull_requests"] = sum(1 for row in per_pull.values()
                                                      if row["kind"] == kind)
        alias = by_kind[kind]["alias"]
        alias["gain_right"] = alias["right"] - by_kind[kind]["base"]["right"]
        alias["gain_coverage"] = round((alias["coverage"] or 0) - (by_kind[kind]["base"]["coverage"] or 0), 6)
    return {"by_kind": by_kind, "per_pull_request": per_pull}


def collect(record: pathlib.Path | None = None, say=print) -> list[dict[str, Any]]:
    pulls = []
    for kind, words in QUERIES:
        found = R.gh("-X", "GET", "search/issues", "-f",
                     f"q=is:pr is:merged language:Python in:title {words}",
                     "-f", f"per_page={R.RESULTS_READ}") or {}
        taken = 0
        for item in found.get("items", []):
            repo = item["repository_url"].split("/repos/")[1]
            name = f"{repo}#{item['number']}"
            if repo == "moxnixmdj/brain" or name in DESIGN:
                continue
            pull = R.one_pull(repo, item["number"])
            say("%-7s %-55s %s  %s" % (kind, name, "USED" if pull else "passed", item["title"][:50]))
            if pull:
                pulls.append(dict(pull, kind=kind, query=words))
                taken += 1
            if taken >= PER_QUERY:
                break
            time.sleep(1)
    if record is not None:
        record.write_text(json.dumps(R.without_texts(pulls), indent=1) + "\n", encoding="utf-8")
    return pulls


def report(pulls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    strict = measure(pulls, say=lambda line: print("strict   " + line, flush=True), check_names=True)
    print()
    assumed = measure(pulls, say=lambda line: print("assumed  " + line, flush=True), check_names=False)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "organ": ORGAN,
        "organ_sha256": _sha(ROOT / ORGAN),
        "operator": OPERATOR,
        "operator_sha256": _sha(ROOT / OPERATOR),
        "queries": [{"kind": kind, "words": words} for kind, words in QUERIES],
        "excluded_as_design": sorted(DESIGN),
        "by_mode": {
            "strict": {"what_it_is": "the organ's own name and import checks; a project-local "
                                     "module is not on this sandbox's path, so the edit is refused",
                       "by_kind": strict["by_kind"], "per_pull_request": strict["per_pull_request"]},
            "assumed": {"what_it_is": "the same run with `check_names=False`: every project-local "
                                      "import is assumed to resolve, as it would in the file's own "
                                      "checkout. An upper bound, not a verified edit.",
                        "by_kind": assumed["by_kind"], "per_pull_request": assumed["per_pull_request"]},
        },
        "by_kind": strict["by_kind"],
        "per_pull_request": strict["per_pull_request"],
        "limits": [
            "A pilot: eight merged pull requests found by title search, two per query; not a "
            "random sample and not a benchmark.",
            "The class titles are noisy: some pull requests also use PEP 604 unions or a "
            "project-local utcnow helper, which this operator does not read.",
            "No project's tests were run; precision is agreement with the developers.",
            "The pull requests were not used to choose the operator, but the operator's family "
            "was chosen on the earlier corpus; this measures transfer of that choice.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--collect", type=pathlib.Path, default=None,
                        help="search GitHub and write the held-out pull requests here")
    parser.add_argument("--record", type=pathlib.Path, default=None,
                        help="with --collect: write the same pull requests without their texts")
    parser.add_argument("--pulls", type=pathlib.Path, default=None)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    if args.collect:
        pulls = collect(record=args.record)
        args.collect.write_text(json.dumps(pulls) + "\n", encoding="utf-8")
        print("pulled", len(pulls), "->", args.collect)
        return 0
    if not args.pulls:
        parser.error("--collect or --pulls")
    rep = report(json.loads(args.pulls.read_text(encoding="utf-8")))
    if args.json:
        args.json.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print()
    print(f"{'mode':9} {'kind':8} {'arm':6} {'right':>6} {'developers':>11} {'coverage':>9} "
          f"{'precision':>10} {'wrong':>6}")
    for mode, body in rep["by_mode"].items():
        for kind, arms in body["by_kind"].items():
            for arm in ARMS:
                row = arms[arm]
                print(f"{mode:9} {kind:8} {arm:6} {row['right']:6d} {row['developers_changes']:11d} "
                      f"{100 * (row['coverage'] or 0):8.2f}% {100 * (row['precision'] or 0):9.2f}% "
                      f"{row['wrong_changes']:6d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
