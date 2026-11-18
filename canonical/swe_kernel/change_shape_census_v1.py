"""What shape is a real change? The census that decides which mechanism can possibly help.

WHY THIS EXISTS
---------------
Rounds 9-12 built and measured four mechanisms against real commits: replay of seen edits, anti-unified
shape rewrites, edit-kind votes learned from other repositories, and predicates invented from a failing
input partition. Every one of them addresses the same narrow shape -- a check that is missing, or a value
that is wrong -- and every one of them was measured on a mixed corpus without ever asking what fraction of
that corpus its shape covers.

That omission made every zero ambiguous. A mechanism can return zero because it is broken, or because the
shape it addresses is rare in the sample. This module removes the ambiguity by classifying every changed
site in the committed corpus by the shape of the change itself, from the two texts the corpus already
holds -- before any repair is attempted, and independently of any mechanism's output.

THE SHAPES, AND WHAT EACH ONE DEMANDS
-------------------------------------
    GUARD_ADDED                      a raise inside a condition that did not exist: needs a predicate and
                                     a seat. This is the only shape rounds 11-12 address.
    VALUE_OR_OPERATOR_SUBSTITUTION   same tree shape, different literal or operator: the memorisable shape.
    VALUE_ADDED                      a new literal in an existing construct: memorisable, literal unseen.
    FEATURE_NEW_DEFINITION           a function or class that did not exist: needs NEW CODE, which no
                                     learned action and no predicate supplies.
    STRUCTURAL_OTHER                 control flow or module shape rewritten: needs synthesis.
    UNREADABLE                       a text the parser rejects; counted, never hidden.

A classification is lexical and therefore a lower bound on precision: it reads the change, not the intent.
It is used to size the addressable share, never to claim a repair.

Model calls 0, network calls 0. Authority NONE.
"""

from __future__ import annotations

import ast
import collections
import json
import pathlib
import sys
from typing import Any, Mapping

SCHEMA = "BRAIN_CHANGE_SHAPE_CENSUS_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0

GUARD = "GUARD_ADDED"
SUBSTITUTION = "VALUE_OR_OPERATOR_SUBSTITUTION"
VALUE_ADDED = "VALUE_ADDED"
FEATURE = "FEATURE_NEW_DEFINITION"
STRUCTURAL = "STRUCTURAL_OTHER"
UNREADABLE = "UNREADABLE"

ADDRESSABLE_BY_PREDICATE = {GUARD}
ADDRESSABLE_BY_REPLAY = {SUBSTITUTION, VALUE_ADDED}


def _count(tree: ast.AST, kind: type) -> int:
    return sum(1 for node in ast.walk(tree) if isinstance(node, kind))


def _names(tree: ast.AST) -> set[str]:
    return {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def shape_of(before: str, after: str) -> str:
    """The shape of the change that turns one text into the other."""
    try:
        old, new = ast.parse(before), ast.parse(after)
    except (SyntaxError, ValueError, RecursionError):
        return UNREADABLE
    if _names(new) - _names(old):
        return FEATURE
    if _count(new, ast.Raise) > _count(old, ast.Raise) and _count(new, ast.If) >= _count(old, ast.If):
        return GUARD
    old_literals = [node.value for node in ast.walk(old) if isinstance(node, ast.Constant)]
    new_literals = [node.value for node in ast.walk(new) if isinstance(node, ast.Constant)]
    if len(new_literals) == len(old_literals) and ast.dump(new) != ast.dump(old):
        return SUBSTITUTION
    if len(new_literals) > len(old_literals):
        return VALUE_ADDED
    return STRUCTURAL


def census(grammar: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts: collections.Counter = collections.Counter()
    per_repository: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for entry in grammar:
        verdict = shape_of(entry["defective"], entry["repaired"])
        counts[verdict] += 1
        per_repository[entry["name"]][verdict] += 1
    total = sum(counts.values())
    predicate_share = sum(counts[shape] for shape in ADDRESSABLE_BY_PREDICATE) / total if total else 0.0
    replay_share = sum(counts[shape] for shape in ADDRESSABLE_BY_REPLAY) / total if total else 0.0
    return {
        "schema": SCHEMA,
        "model_calls": MODEL_CALLS,
        "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {"sites": total, "shapes": dict(counts),
                   "predicate_addressable": dict(counts.most_common()) and {
                       shape: counts[shape] for shape in ADDRESSABLE_BY_PREDICATE},
                   "predicate_addressable_share": round(predicate_share, 4),
                   "replay_addressable_share": round(replay_share, 4),
                   "new_code_required_share": round(
                       (counts[FEATURE] + counts[STRUCTURAL]) / total if total else 0.0, 4)},
        "per_repository": {name: dict(counter) for name, counter in per_repository.items()},
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    shapes = totals["shapes"]
    ordered = ", ".join(f"{name} {count}" for name, count in sorted(shapes.items(), key=lambda x: -x[1]))
    return (f"{totals['sites']} real changed sites: {ordered}. A missing check -- the only shape a predicate "
            f"can supply -- is {totals['predicate_addressable_share']:.1%}; replay of a seen edit covers "
            f"{totals['replay_addressable_share']:.1%}; new code is required by "
            f"{totals['new_code_required_share']:.1%}.")


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--json", type=pathlib.Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = census(payload.get("grammar", []))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
