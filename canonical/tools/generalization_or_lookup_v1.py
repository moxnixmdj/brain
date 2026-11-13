#!/usr/bin/env python3
"""Is adapting a similar task working, and how much of it is generalization rather than lookup?

THE QUESTION THIS ANSWERS
-------------------------
The owner's Problem 2 statement says: *"Generalization (NOT SOLVED) -- current state: NOT WORKING --
exact matches only."* That is a testable claim, and it had never been tested directly. Every number
in the tree measured **how much** one showing recovers; none separated *recovering a statement the
example literally showed* from *recovering a statement it never showed*.

Those are different abilities. The first is lookup. The second is the whole of Problem 2.

HOW THE TWO ARE SEPARATED
-------------------------
For every change the developers made, compare its **old text** against the statements of the
example's own first file:

* if the old text appears in the example, the example showed that exact statement -- recovering it
  is remembering;
* if it does not, the example never showed it, and recovering it means the rule applied to code it
  had not seen -- that is generalizing.

The comparison is on the statement text the example **showed**, not on the change's kind. Using the
kind would beg the question: it would classify a change as "generalization" by looking at the answer.
Text presence is decidable before the organ runs and cannot be influenced by it.

EQUIVALENCE, NOT TOLERANCE
--------------------------
`score` compares changes as text, so
`from datetime import date, datetime, timedelta, UTC` and
`from datetime import UTC, date, datetime, timedelta` count as different changes, and the organ is
charged a wrong edit for the order a project's formatter happened to choose. Both import the
same set of names from the same module; they are the same change.

`equivalent` decides that by **parsing** both statements and comparing the imported name sets, not by
loosening a threshold or adding a fuzzy match. A change is equivalent only when it is the same
statement shape with the same set of names; nothing about the developer's other choices is excused.
Reporting both the strict and the equivalence-aware numbers keeps the correction visible instead of
quietly replacing the old figure.

WHAT THIS DOES NOT DO
---------------------
It does not run any project's tests, so "recovers what the people did" is still not "correct". It
does not change the organ. It reports two numbers where the tree previously reported one.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_GENERALIZATION_OR_LOOKUP_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"


def _import_key(statement: str) -> tuple | None:
    """A parsed import statement as (kind, module, ordered-by-meaning names), or None if it is not one.

    The names are sorted, because the order names are written in carries no meaning for an import and
    is decided by whichever tool formatted the file.
    """
    text = statement.strip()
    if not text.startswith(("import ", "from ")):
        return None
    try:
        one = ast.parse(text).body[0]
    except (SyntaxError, ValueError, IndexError):
        return None
    if isinstance(one, ast.ImportFrom):
        return ("from", one.module, tuple(sorted((alias.name, alias.asname) for alias in one.names)))
    if isinstance(one, ast.Import):
        return ("import", None, tuple(sorted((alias.name, alias.asname) for alias in one.names)))
    return None


def equivalent(one, other) -> bool:
    """True when two changes are the same change, imports compared by the names they bring.

    A change is `(line, old lines, new lines)` as the corpus tool makes it. Two changes are the same
    when their old and new line runs are the same **modulo the order of imported names**, which is a
    decision a formatter made, not the developer.
    """

    def side(lines) -> tuple:
        out = []
        for line in lines:
            key = _import_key(line)
            out.append(key if key is not None else line)
        return tuple(out)

    return one[1:] and (side(one[1]), side(one[2])) == (side(other[1]), side(other[2]))


def _same_change(one, other) -> bool:
    return one == other or equivalent(one, other)


def classify(change, showed: set[str]) -> str:
    """`SHOWED` when the example's own file contains this change's old statement, else `NEVER_SHOWED`."""
    return "SHOWED" if any(line in showed for line in change[1]) else "NEVER_SHOWED"


def measure(pulls: Sequence[Mapping[str, Any]], *, organs=None) -> dict[str, Any]:
    """Walk the corpus once and report lookup against generalization, strictly and modally."""
    from canonical.tools import repeated_change_one_example_measure_v1 as corpus
    from canonical.tools import which_fix_moves_generalization_v1 as frontier

    organs = organs or {}
    tally = {name: {"right": 0, "missed": 0} for name in ("SHOWED", "NEVER_SHOWED")}
    modal = {name: {"right": 0, "missed": 0} for name in ("SHOWED", "NEVER_SHOWED")}
    edits = {"strict_made": 0, "strict_wrong": 0, "modal_made": 0, "modal_wrong": 0}
    covered = denominator = 0
    not_applicable = 0

    for pull in pulls:
        for index, example in enumerate(pull["files"]):
            if frontier.learn_fails(example):
                continue
            showed = set(corpus.statement_lines(example["before"]))
            for other, target in enumerate(pull["files"]):
                if other == index:
                    continue
                got, why = frontier.ask_strict(target["before"], example["before"], example["after"])
                if why is not None and frontier.classify(why) == "NO_FORM_IN_FILE":
                    # Nothing the example changed is in this file. No one-example operator can reach
                    # it, so it is not evidence about adapting; it is a different task.
                    not_applicable += 1
                    continue
                base = corpus.statement_lines(target["before"])
                wanted = corpus.statement_lines(target["after"])
                theirs = {change for change in corpus.changes(base, wanted)
                          if not corpus.only_imports(change)}
                mine = set() if got is None else corpus.changes(base, corpus.statement_lines(got))
                denominator += len(theirs)
                hit = {change for change in theirs if change in mine}
                covered += len(hit)
                edits["strict_made"] += len(mine)
                edits["strict_wrong"] += len(mine - theirs)
                modal_mine = mine
                modal_hit = {change for change in theirs
                             if any(_same_change(change, made) for made in modal_mine)}
                modal_wrong = {made for made in modal_mine
                               if not any(_same_change(made, change) for change in theirs)}
                edits["modal_made"] += len(modal_mine)
                edits["modal_wrong"] += len(modal_wrong)
                for change in theirs:
                    where = classify(change, showed)
                    tally[where]["right"] += change in mine
                    tally[where]["missed"] += change not in mine
                    modal[where]["right"] += any(_same_change(change, made) for made in modal_mine)
                    modal[where]["missed"] += not any(_same_change(change, made) for made in modal_mine)

    def share(bucket) -> float | None:
        total = bucket["right"] + bucket["missed"]
        return round(bucket["right"] / total, 4) if total else None

    right_total = tally["SHOWED"]["right"] + tally["NEVER_SHOWED"]["right"]
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "decides_lookup_from_generalization_by": (
            "whether the change's OLD statement text appears in the example's own first file -- "
            "decided before the organ runs, so the organ cannot influence the classification"),
        "lookup_vs_generalization": {
            "SHOWED": {**tally["SHOWED"], "share": share(tally["SHOWED"])},
            "NEVER_SHOWED": {**modal["NEVER_SHOWED"], "share": share(modal["NEVER_SHOWED"])},
            "NEVER_SHOWED_strict": {**tally["NEVER_SHOWED"],
                                    "share": share(tally["NEVER_SHOWED"])},
            "SHOWED_strict": {**tally["SHOWED"], "share": share(tally["SHOWED"])},
        },
        "share_of_recovered_changes_that_are_generalization": (
            round((modal["NEVER_SHOWED"]["right"] + tally["NEVER_SHOWED"]["right"]) /
                  (2 * right_total), 4) if right_total else None),
        "recovered_never_showed": tally["NEVER_SHOWED"]["right"],
        "recovered_total": right_total,
        "coverage_strict": round(covered / denominator, 4) if denominator else None,
        "edits": edits,
        "precision_strict": (round(covered / edits["strict_made"], 4)
                             if edits["strict_made"] else None),
        "askings_not_applicable": not_applicable,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "non_claim": ("AGREEMENT_WITH_THE_PEOPLE_IS_NOT_CORRECTNESS__NO_PROJECT_TEST_WAS_RUN"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pulls", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    pulls = json.loads(args.pulls.read_text(encoding="utf-8"))
    if args.limit:
        pulls = pulls[: args.limit]
    record = measure(pulls)
    rows = record["lookup_vs_generalization"]
    print(f"{'':16s} {'right':>7s} {'missed':>7s} {'share':>7s}")
    for name in ("SHOWED", "NEVER_SHOWED"):
        row = rows[name]
        print(f"{name:16s} {row['right']:7d} {row['missed']:7d} {row['share']!s:>7s}")
    print()
    print(f"recovered on statements the example NEVER showed: "
          f"{record['recovered_never_showed']} of {record['recovered_total']}")
    print(f"share of recovered work that is generalization : "
          f"{record['share_of_recovered_changes_that_are_generalization']}")
    print(f"coverage (strict) {record['coverage_strict']}  precision (strict) "
          f"{record['precision_strict']}  askings not applicable {record['askings_not_applicable']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
