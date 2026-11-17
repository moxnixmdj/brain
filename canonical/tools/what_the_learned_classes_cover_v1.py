#!/usr/bin/env python3
"""What is left for a lesson to buy now that the space is derived from the artifact?

THE QUESTION THIS ANSWERS
-------------------------
"Show the agent a fix once, it has learned it permanently, and everything else comes free." The
tree already measured that with the old solver and the old hand-written space: 5 of 40 with nothing
taught, 20 of 40 with 164 HumanEvalFix fixes taught first (`QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1`).
Then the space changed: it is no longer a hand-written list, it is the closure of the program's own
material under its own forms, and last session it took 8 of 8 published bugs.

So the question is not "does a lesson transfer" but **"what is left for a lesson to buy once the
space is derived from the artifact?"** That has an exact answer that needs no search:

    for every published bug, is the corpus's own published fix reachable by
      (a) the old hand-written space,
      (b) one of the classes read off other programs, or
      (c) neither -- it needs more than one edit?

A fix is "reachable" when a program in the space *is* the corpus's corrected program. That is a
membership fact about a set, computed exactly, with no execution and no verdict: this receipt says
which programs are *expressible*, not which are *solved*. The solve claim lives in
`AIMED_EDITS_FROM_THE_PROGRAM_AND_THE_FAILURE_20261117_V1`.

WHY THE SPACE ITSELF IS THE ONLY HONEST INSTRUMENT
--------------------------------------------------
The first version of this tool re-implemented the space's rules over the structural diff of the two
functions and asked whether the difference was one of them. It reported 25 of 40 as "needs more than
one edit" while the space demonstrably contained the published fix for sqrt and powerset: the space
writes `(approx) ** 2` and `rest_subsets + (X)`, a diff writes `approx ** 2`. It also knew nothing
about operator swaps or argument permutations, which the space performs. A second implementation of
a set is not a measurement of that set, it is a measurement of the second implementation.

So membership is decided here by walking the *real* space -- `space_builder`, the same function the
solver uses -- and comparing every candidate's function against the corpus's corrected function.
When the fix is not in the space, the structural diff still runs, because the honest next question
is whether one edit would have sufficed (a gap in the classes) or whether the fix is a composition.

WHY THE LEAVE-ONE-OUT MATTERS
-----------------------------
Every derived class was read off one specific program. If a class reaches only the program it was
read from, "learn it once and reuse it" is an illusion and the transfer number is zero. So the donor
of every class is named, and non-donor reach is counted separately.

Authority NONE, producer-run, zero model calls, zero network calls at run time.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import pathlib
import sys
import time
from typing import Any, Iterator

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import aimed_edits_from_the_program_and_the_failure_v1 as aimed  # noqa: E402
import grammar_closed_repair_v1 as gen  # noqa: E402

SCHEMA = "BRAIN_WHAT_THE_LEARNED_CLASSES_COVER_V2"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"

# Which program each class was read off. Without this table a transfer claim cannot be checked.
DONOR = {"COMMUTE": "to_base", "SLICE": "kheapsort", "NEST": "subsequences",
         "PREPEND_TERM": "powerset", "INSERT_STATEMENT": "shunting_yard",
         "ATTRIBUTE": "subsequences", "CALL": "powerset", "IF_EXPRESSION": None,
         "BOOLEAN_OP": "shunting_yard",
         "ENCLOSE": "the language, not a program", "RECOMBINE": "the language, not a program"}

# The classes that were read off another program, as opposed to the hand-written grammar.
DERIVED = set(aimed.RULES) | {"COMMUTE", "INSERT_STATEMENT"}


def function_of(source: str) -> ast.FunctionDef | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    return next((node for node in tree.body if isinstance(node, ast.FunctionDef)), None)


def strip_docstrings(node: ast.AST) -> ast.AST:
    """The corpus leaves the original body in a docstring; that is commentary, not code."""
    for owner in ast.walk(node):
        body = getattr(owner, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            owner.body = body[1:] or [ast.Pass()]
    return node


def bug_names(root: pathlib.Path) -> list[str]:
    """The buggy programs, excluding the corpus's own graph helper and the test programs."""
    names = []
    for path in sorted((root / "python_programs").glob("*.py")):
        if path.stem == "node" or path.stem.endswith("_test"):
            continue
        names.append(path.stem)
    return names


# --------------------------------------------------------------------------------------------------
# The space, walked for the corpus's own published fix.
# --------------------------------------------------------------------------------------------------

def find_in_space(buggy_tree: ast.AST, atoms: list[str], wanted: str,
                  extra_classes: bool = False) -> dict[str, Any] | None:
    """Which candidate of the real space is the corpus's corrected program, and who built it."""
    space = aimed.space_builder(buggy_tree, atoms, extra_classes=extra_classes)
    for candidate in space:
        # The candidate is the module re-rendered by the same unparser the target went through, so an
        # exact function is a substring of it. The substring test is the cheap filter; the parse below
        # is the proof, so this cannot produce a false claim.
        source = str(candidate.get("source", ""))
        if wanted not in source:
            continue
        function = function_of(source)
        if function is None:
            continue
        try:
            text = ast.unparse(function)
        except Exception:  # noqa: BLE001
            continue
        if text == wanted:
            return {"class": str(candidate.get("class")), "kind": str(candidate.get("kind")),
                    "site": candidate.get("site"), "replacement": candidate.get("replacement"),
                    "space_size": len(space)}
    return {"space_size": len(space)}


# --------------------------------------------------------------------------------------------------
# When the fix is not in the space: is it one edit the classes cannot make, or a composition?
# --------------------------------------------------------------------------------------------------

def _node_at(tree: ast.AST, path: tuple[tuple[str, int | None], ...]) -> ast.AST | None:
    node: Any = tree
    try:
        for field, index in path:
            node = getattr(node, field)
            if index is not None:
                node = node[index]
    except (AttributeError, IndexError, TypeError):
        return None
    return node if isinstance(node, ast.AST) else None


def _insert_at(tree: ast.AST, owner_path: tuple[tuple[str, int | None], ...], field: str,
               index: int, statement: ast.stmt) -> ast.AST:
    new = copy.deepcopy(tree)
    node: Any = new
    for sub_field, sub_index in owner_path:
        node = getattr(node, sub_field)
        if sub_index is not None:
            node = node[sub_index]
    block = list(getattr(node, field))
    block.insert(index, copy.deepcopy(statement))
    setattr(node, field, block)
    return new


def _statement_slots(tree: ast.AST) -> Iterator[tuple[tuple[tuple[str, int | None], ...], str, int]]:
    """Every place one statement could be put into, as (owner path, field, index)."""
    for path, node in gen._paths(tree):  # noqa: SLF001
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list) and all(isinstance(item, ast.stmt) for item in block):
                for index in range(len(block) + 1):
                    yield path, field, index


def single_edit(buggy: ast.AST, correct: ast.AST) -> dict[str, Any] | None:
    """Is this difference exactly one substitution or one inserted statement -- and where?

    Exact: substitute the site, unparse, compare the whole function. Two rules were learned the hard
    way: try the *deepest* site first (otherwise the "site" is an entire for-statement, which no
    expression space can express), and do not require the replacement to have the same node type as
    the site (every real fix replaces a Name with a Subscript).
    """
    target = ast.unparse(correct)
    if ast.unparse(buggy) == target:
        return {"kind": "SAME"}
    for path, node in sorted(gen._paths(buggy), key=lambda item: -len(item[0])):  # noqa: SLF001
        # Expressions only. "Replace the whole if-statement with the correct if-statement" explains
        # any difference and is not an edit any space could express -- counting it as one edit would
        # report zero composition for a corpus where the solver provably needs several steps.
        if not path or not isinstance(node, ast.expr):
            continue
        counterpart = _node_at(correct, path)
        if counterpart is None or not isinstance(counterpart, ast.expr):
            continue
        try:
            trial = ast.unparse(gen.replace_at(buggy, path, counterpart))
        except Exception:  # noqa: BLE001
            continue
        if trial == target:
            return {"kind": "replace", "site": ast.unparse(node),
                    "replacement": ast.unparse(counterpart)}
    present = {ast.unparse(item) for item in ast.walk(buggy) if isinstance(item, ast.stmt)}
    for statement in (item for item in ast.walk(correct)
                      if isinstance(item, ast.stmt) and not isinstance(item, ast.FunctionDef)):
        text = ast.unparse(statement)
        if text in present:
            continue
        for owner_path, field, index in _statement_slots(buggy):
            try:
                if ast.unparse(_insert_at(buggy, owner_path, field, index, statement)) == target:
                    return {"kind": "insert_statement", "statement": text}
            except Exception:  # noqa: BLE001
                continue
    return None


# --------------------------------------------------------------------------------------------------
# One bug.
# --------------------------------------------------------------------------------------------------

def inspect(root: pathlib.Path, name: str, extra_classes: bool = False) -> dict[str, Any]:
    row: dict[str, Any] = {"task": name}
    buggy_path = root / "python_programs" / f"{name}.py"
    correct_path = root / "correct_python_programs" / f"{name}.py"
    if not correct_path.is_file():
        row["status"] = "NO_CORRECTED_PROGRAM"
        return row
    buggy_tree = ast.parse(buggy_path.read_text())
    correct_tree = ast.parse(correct_path.read_text())
    buggy_function = next((n for n in buggy_tree.body if isinstance(n, ast.FunctionDef)), None)
    correct_function = next((n for n in correct_tree.body if isinstance(n, ast.FunctionDef)), None)
    if buggy_function is None or correct_function is None:
        row["status"] = "NO_FUNCTION"
        return row
    strip_docstrings(buggy_function)
    strip_docstrings(correct_function)
    target = ast.unparse(correct_function)
    atoms = gen.atoms_of(buggy_function)

    started = time.time()
    found = find_in_space(buggy_tree, list(atoms), target, extra_classes=extra_classes)
    row["status"] = "MEASURED"
    row["atoms"] = len(atoms)
    row["seconds"] = round(time.time() - started, 3)

    if found and "class" in found:
        row["space_size"] = found["space_size"]
        row["fix_in_the_space"] = True
        row["fix_class"] = found["class"]
        row["fix_kind"] = found["kind"]
        row["fix_site"] = found["site"]
        row["fix_replacement"] = found["replacement"]
        row["fix_in_the_old_space"] = found["class"] not in DERIVED
        row["fix_by_a_derived_class"] = found["class"] in DERIVED
        row["needs_composition"] = False
        return row

    row["space_size"] = found["space_size"] if found else None
    row["fix_in_the_space"] = False
    row["fix_class"] = None
    row["fix_in_the_old_space"] = False
    row["fix_by_a_derived_class"] = False
    difference = single_edit(buggy_function, correct_function)
    if difference is None:
        row["needs_composition"] = True
        row["difference"] = "more than one edit"
    elif difference["kind"] == "SAME":
        row["needs_composition"] = False
        row["difference"] = "no edit at all"
    elif difference["kind"] == "insert_statement":
        row["needs_composition"] = False
        row["difference"] = f"insert {difference['statement']}"
    else:
        row["needs_composition"] = False
        row["difference"] = f"{difference['site']} -> {difference['replacement']}"
    return row


def _normalise(text: str) -> str | None:
    try:
        return ast.unparse(ast.parse(text, mode="eval").body)
    except SyntaxError:
        return None


def probe_extra_classes(root: pathlib.Path, name: str) -> dict[str, Any]:
    """Would the language-grammar rungs build the one edit the shipped space cannot?

    This is a *membership probe at the site the difference names* -- cheaper and narrower than a walk
    of the whole widened space, and it is reported as exactly that. It answers "can the rung write
    the expression the fix needs where the fix needs it", which is the question the rungs were added
    for; it is not a solve and not a space walk.
    """
    buggy_tree = ast.parse((root / "python_programs" / f"{name}.py").read_text())
    correct_tree = ast.parse((root / "correct_python_programs" / f"{name}.py").read_text())
    buggy = next((n for n in buggy_tree.body if isinstance(n, ast.FunctionDef)), None)
    correct = next((n for n in correct_tree.body if isinstance(n, ast.FunctionDef)), None)
    if buggy is None or correct is None:
        return {"task": name, "status": "NO_FUNCTION"}
    strip_docstrings(buggy)
    strip_docstrings(correct)
    difference = single_edit(buggy, correct)
    if difference is None or difference.get("kind") != "replace":
        return {"task": name, "status": "NOT_ONE_EXPRESSION",
                "kind": None if difference is None else difference.get("kind")}
    atoms = gen.atoms_of(buggy)
    forms = aimed.forms_of(buggy_tree)
    attributes = aimed.attributes_of(buggy_tree)
    callables = aimed.callables_of(buggy_tree)
    symbols = aimed.binop_symbols_of(buggy_tree)
    wanted = _normalise(difference["replacement"])
    built: list[str] = []
    for class_name, rule in aimed.EXPERIMENTAL.items():
        produced = rule(difference["site"], atoms, forms, attributes, callables, symbols,
                        {"tree": buggy_tree})
        if any(_normalise(text) == wanted for text in produced):
            built.append(class_name)
    return {"task": name, "status": "PROBED", "site": difference["site"],
            "replacement": difference["replacement"], "built_by": built}


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [row for row in rows if row.get("status") == "MEASURED"]
    old = [row for row in measured if row.get("fix_in_the_old_space")]
    derived = [row for row in measured if row.get("fix_by_a_derived_class")]
    in_space = [row for row in measured if row.get("fix_in_the_space")]
    single_not_built = [row for row in measured
                        if not row.get("fix_in_the_space") and not row.get("needs_composition")]
    composition = [row for row in measured if row.get("needs_composition")]

    by_class: dict[str, dict[str, Any]] = {}
    for row in measured:
        name = row.get("fix_class")
        if not name or name not in DERIVED:
            continue
        entry = by_class.setdefault(name, {"reaches": [], "reaches_not_its_donor": [],
                                           "donor": DONOR.get(name)})
        entry["reaches"].append(row["task"])
        if DONOR.get(name) != row["task"]:
            entry["reaches_not_its_donor"].append(row["task"])
    for entry in by_class.values():
        entry["reaches"] = sorted(entry["reaches"])
        entry["reaches_not_its_donor"] = sorted(entry["reaches_not_its_donor"])

    only_their_donor = sorted(name for name, entry in by_class.items()
                              if not entry["reaches_not_its_donor"])
    transferred = sorted({task for entry in by_class.values()
                          for task in entry["reaches_not_its_donor"]})
    only_a_derived_class = sorted(row["task"] for row in derived
                                  if not row.get("fix_in_the_old_space"))

    return {
        "bugs_measured": len(measured),
        "fix_in_the_space": len(in_space),
        "fix_in_the_old_space": sorted(row["task"] for row in old),
        "fix_in_the_old_space_count": len(old),
        "fix_reached_by_a_derived_class": sorted(row["task"] for row in derived),
        "fix_reached_by_a_derived_class_count": len(derived),
        "fix_only_by_a_derived_class": only_a_derived_class,
        "fix_only_by_a_derived_class_count": len(only_a_derived_class),
        "in_the_space_but_nothing_taught": sorted(row["task"] for row in in_space
                                                 if not row.get("fix_in_the_old_space")
                                                 and not row.get("fix_by_a_derived_class")),
        "one_edit_the_space_cannot_make": sorted(row["task"] for row in single_not_built),
        "one_edit_the_space_cannot_make_count": len(single_not_built),
        "needs_composition": sorted(row["task"] for row in composition),
        "needs_composition_count": len(composition),
        "classes_and_what_they_reach": by_class,
        "reached_by_a_class_learned_on_another_program": transferred,
        "reached_by_a_class_learned_on_another_program_count": len(transferred),
        "classes_that_only_reach_their_donor": only_their_donor,
        "total_seconds": round(sum(row.get("seconds") or 0.0 for row in measured), 1),
        "model_dependent_tasks": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--extra-probe", action="store_true",
                        help="also probe the experimental rungs at the site of each missing fix")
    parser.add_argument("--extra-classes", action="store_true",
                        help="also measure the experimental language-grammar rungs")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.quixbugs)

    rows: list[dict[str, Any]] = []
    names = args.tasks or bug_names(root)
    for name in names:
        try:
            row = inspect(root, name, extra_classes=args.extra_classes)
        except Exception as error:  # noqa: BLE001
            row = {"task": name, "status": "RAISED", "error": repr(error)[:300]}
        rows.append(row)
        print(f"{name:26s} {str(row.get('status')):9s} space={str(row.get('space_size')):>6s} "
              f"class={str(row.get('fix_class') or '-'):16s} "
              f"comp={row.get('needs_composition')} {str(row.get('difference') or '')[:40]}",
              flush=True)

    probe = None
    if args.extra_probe:
        probe = []
        for row in rows:
            if row.get("status") != "MEASURED" or row.get("fix_in_the_space"):
                continue
            try:
                probe.append(probe_extra_classes(root, row["task"]))
            except Exception as error:  # noqa: BLE001
                probe.append({"task": row["task"], "status": "RAISED", "error": repr(error)[:200]})
        for item in probe:
            print(f"probe {item['task']:26s} {item['status']:20s} "
                  f"{','.join(item.get('built_by') or []) or '-'}", flush=True)

    summary = summarise(rows)
    if probe is not None:
        summary["experimental_probe"] = {
            "status": "MEMBERSHIP_AT_THE_SITE__NOT_A_SPACE_WALK",
            "probed": len(probe),
            "built_by_the_experimental_rungs": sorted(item["task"] for item in probe
                                                      if item.get("built_by")),
            "not_built": sorted(item["task"] for item in probe if not item.get("built_by")),
            "rows": probe,
        }
    receipt = {"schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "upstream": UPSTREAM,
               "tool": "canonical/tools/what_the_learned_classes_cover_v1.py",
               "measures": "reachability of the corpus's own published fix inside the real space; "
                           "not a solve, and no execution",
               "donors": DONOR, "derived_classes": sorted(DERIVED),
               "classes_in_the_shipped_space": sorted(aimed.RULES),
               "classes_experimental_only": sorted(aimed.EXPERIMENTAL),
               "summary": summary, "rows": rows}
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=2, default=str) + "\n")
    print(json.dumps({key: summary[key] for key in
                      ("bugs_measured", "fix_in_the_space", "fix_in_the_old_space_count",
                       "fix_reached_by_a_derived_class_count", "fix_only_by_a_derived_class_count",
                       "one_edit_the_space_cannot_make_count", "needs_composition_count",
                       "reached_by_a_class_learned_on_another_program_count", "total_seconds")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
