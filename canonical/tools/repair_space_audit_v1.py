"""Was the answer inside the space the generator enumerated, or outside it?

THE QUESTION
------------
`grammar_closed_repair_v1` repaired 14 of 31 measurable QuixBugs bugs and refused 17 with
`NO_IMPROVING_CANDIDATE`. A refusal like that has exactly three possible causes, and they call for
three completely different next builds:

    A. SEARCH_TOO_WEAK   the published fix is a single edit, and the enumerated space CONTAINS it,
                         but the search did not reach it inside the budget. -> prune the search.
    B. SPACE_TOO_SMALL   the published fix is a single edit, and the space does NOT contain it.
                         -> widen the generator.
    C. MULTI_EDIT        the published fix needs more than one edit from the defective program.
                         -> the one-edit mechanism cannot express it at all.

Guessing which one dominates would waste a turn and, worse, would produce a mechanism nobody
needed. So this measures it: for every task, enumerate the same space the generator enumerates,
compare it against the corpus's own corrected program, and say which of the three it is.

WHAT THIS READS
---------------
It reads `correct_python_programs/`, which the repair generator is forbidden to see. That is the
point: this is an AUDIT of the target, not a solver. It writes no program and produces no patch
that could be mistaken for a repair. It only reports membership.

Usage
-----
    python3 canonical/tools/repair_space_audit_v1.py --quixbugs /path/to/QuixBugs \
        --receipt canonical/verification/THE_EDIT_SPACE_IS_THE_PROGRAM_NOT_A_LIST_20261116_V1.json \
        --out /tmp/space_audit.json
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import sys
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import grammar_closed_repair_v1 as organ  # noqa: E402
from canonical.tools import quixbugs_required_edit_taxonomy_v1 as taxonomy  # noqa: E402

SCHEMA = "BRAIN_REPAIR_SPACE_AUDIT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_AUDIT_OF_TARGET_NOT_A_SOLVER"


def normalised(source: str) -> str:
    """The same normal form the generator uses for candidates: unparse, inert strings removed."""
    return ast.unparse(taxonomy.strip_inert_strings(ast.parse(source)))


def function_source(source: str, name: str) -> str | None:
    """Just the target function, unparsed.

    Comparing whole modules is wrong here: QuixBugs' corrected files sometimes ship several
    implementations of the same function and the task description appended as a string, so a
    module-level comparison reports "not in the space" for fixes the space obviously has. The
    function is the unit the generator edits, so the function is the unit of comparison.
    """
    try:
        tree = taxonomy.strip_inert_strings(ast.parse(source))
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.unparse(node)
    return None


def audit_task(root: pathlib.Path, name: str) -> dict[str, Any]:
    buggy_path = root / "python_programs" / f"{name}.py"
    correct_path = root / "correct_python_programs" / f"{name}.py"
    row: dict[str, Any] = {"task": name, "kind": "task"}
    if not buggy_path.is_file() or not correct_path.is_file():
        row["verdict"] = "NO_TARGET_SOURCE"
        return row
    if not organ.examples_of(root, name):
        row["verdict"] = "NO_EXAMPLES__NOT_SEARCHABLE"
        return row
    buggy = buggy_path.read_text()
    correct = correct_path.read_text()
    tree = ast.parse(buggy)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if function is None:
        row["verdict"] = "NO_FUNCTION"
        return row

    answer_fn = function_source(correct, function.name)
    buggy_fn = ast.unparse(function)
    if answer_fn is None:
        row["verdict"] = "TARGET_FUNCTION_MISSING_IN_TARGET"
        return row
    shape = taxonomy.classify(buggy_fn, answer_fn)
    row["published_fix_kinds"] = shape["kinds"]
    row["published_fix_edits"] = shape.get("edit_count")
    row["answer"] = answer_fn

    space = organ._enumerate(tree, organ.atoms_of(function))
    row["space_size"] = len(space)
    inside = any(function_source(c["source"], function.name) == answer_fn for c in space)
    row["space_contains_published_fix"] = inside

    if row["published_fix_edits"] != 1:
        row["verdict"] = "C_MULTI_EDIT"
    elif inside:
        row["verdict"] = "A_SEARCH_TOO_WEAK"
    else:
        row["verdict"] = "B_SPACE_TOO_SMALL"
    # what the space would have to add to reach the answer, when it is one edit away
    if row["verdict"] == "B_SPACE_TOO_SMALL":
        row["nearest"] = _nearest(space, row["answer"], buggy)
    return row


def _nearest(space: Sequence[dict[str, Any]], answer: str, buggy: str) -> dict[str, Any]:
    """How close did the space get? Longest common prefix of the unparsed sources is a cheap proxy."""
    best, best_len = None, -1
    for candidate in space:
        source = candidate["source"]
        length = 0
        for a, b in zip(source, answer):
            if a != b:
                break
            length += 1
        if length > best_len:
            best, best_len = candidate, length
    if best is None:
        return {}
    strip = max(0, best_len)
    return {"candidate": best["site"], "replacement": best["replacement"],
            "common_prefix_chars": strip,
            "answer_at_divergence": answer[strip:strip + 60],
            "space_at_divergence": best["source"][strip:strip + 60]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--receipt", default=None, help="a grammar-closed run receipt, to join outcomes")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs).resolve()
    names = sorted(p.name[len("test_"):-len(".py")]
                   for p in (root / "python_testcases").glob("test_*.py"))
    solved: set[str] = set()
    if args.receipt and pathlib.Path(args.receipt).is_file():
        solved = set(json.loads(pathlib.Path(args.receipt).read_text()).get("repaired_tasks") or [])

    rows = []
    for name in names:
        row = audit_task(root, name)
        row["was_repaired_in_the_run"] = name in solved
        rows.append(row)
        print(f"{name:<26} {row['verdict']:<24} inside_space={row.get('space_contains_published_fix')} "
              f"edits={row.get('published_fix_edits')} space={row.get('space_size')}", flush=True)

    tally = collections.Counter(r["verdict"] for r in rows)
    refused = [r for r in rows if not r["was_repaired_in_the_run"]]
    refused_tally = collections.Counter(r["verdict"] for r in refused)
    receipt = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "corpus": {"upstream": "https://github.com/jkoppel/QuixBugs", "tasks": len(rows)},
        "verdict_tally_all_tasks": dict(sorted(tally.items())),
        "verdict_tally_refused_only": dict(sorted(refused_tally.items())),
        "refused_tasks": [r["task"] for r in refused],
        "reading": ("A_SEARCH_TOO_WEAK: the published fix is one edit and the enumerated space contains "
                    "it, so the refusal was search, not expressiveness. B_SPACE_TOO_SMALL: one edit, but "
                    "not in the space -- the generator must widen. C_MULTI_EDIT: the published fix is more "
                    "than one edit from the defective program, so a one-edit mechanism cannot express it "
                    "at all. NO_EXAMPLES: nothing to search against."),
        "rows": rows,
    }
    pathlib.Path(args.out).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"all": receipt["verdict_tally_all_tasks"],
                      "refused": receipt["verdict_tally_refused_only"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
