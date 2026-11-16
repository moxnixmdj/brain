"""What edit does a real bug actually require? Measured on QuixBugs, not assumed.

WHY THIS EXISTS
---------------
Before spending an hour of search on 40 real bugs, one cheap question decides everything:
what KIND of edit does each published bug need? If most need a statement the tree's search
vocabulary cannot emit, the search budget is irrelevant and the bottleneck is the vocabulary.
If most need a single operator change, the vocabulary is fine and the bottleneck is elsewhere.

So this diffs each published defective program against the corrected version the corpus ships,
compares the two as SYNTAX TREES (comments, formatting and trailing description strings cannot
influence the answer), and reports the atomic edits. Each edit is typed at the SHALLOWEST site
that fully explains it, so one changed operator is one OPERATOR edit and never also a STRUCTURE
edit:

    OPERATOR   a binary/augmented/comparison operator changed   (``/`` -> ``//``, ``<`` -> ``<=``)
    NEGATE     a ``not`` was added or removed
    CONSTANT   a literal value changed                          (``1`` -> ``0``)
    NAME       an identifier or attribute changed               (``outgoing_nodes`` -> ``incoming_nodes``)
    CALLEE     the function being called changed                (``any`` -> ``all``)
    ARGUMENT   the same call arguments, reordered               (``gcd(a % b, b)`` -> ``gcd(b, a % b)``)
    EXPRESSION a whole subexpression was replaced by one of a DIFFERENT shape
               (``len(arr)`` -> ``len(arr) - 1``, ``any(...)`` -> ``not any(...)``, ``BinOp`` -> ``Call``)
    STRUCTURE  a STATEMENT was added, removed, re-nested or retyped
               (a guard, an early return, an ``Expr`` becoming an ``Assign``)
    VALUE      any other field inequality (should be rare; reported, not hidden)

A fix needing more than one atomic edit is reported as MULTI with the set of kinds involved.

INTEGRITY AND SCOPE
-------------------
This reads the answer key, and that is the point of it: it is a TAXONOMY OF THE TARGET, not a
solver input. It writes no program, and the repair measurement is forbidden from seeing these
files (quixbugs_end_to_end_repair_measure_v1 does not copy the answer key into a task).
Reading the key to characterize the work is legitimate; copying it is not.

Usage
-----
    python3 canonical/tools/quixbugs_required_edit_taxonomy_v1.py --quixbugs /path/to/QuixBugs \
        --out /tmp/quixbugs_taxonomy.json
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import sys
from typing import Any, Sequence

UPSTREAM = "https://github.com/jkoppel/QuixBugs"


def strip_inert_strings(tree: ast.AST) -> ast.AST:
    """Remove every bare string expression statement.

    QuixBugs appends the task description to a program as a trailing bare string, and the
    corrected files do not all carry the same one. Such a statement has no effect at run time,
    so leaving it in would report every task as a structural rewrite of the module body.
    """
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            node.body = [s for s in body
                         if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                                 and isinstance(s.value.value, str))]
    return tree


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)[:48]
    except Exception:  # noqa: BLE001 -- cosmetic only
        return type(node).__name__


def classify_node(old: Any, new: Any, path: str = "") -> list[dict[str, str]]:
    """The shallowest edits that explain how ``old`` became ``new``."""
    if type(old) is not type(new):
        # A node was replaced wholesale. If the replacement is a negation of the same subtree,
        # that is a one-token edit, not a rewrite.
        if isinstance(new, ast.UnaryOp) and isinstance(new.op, ast.Not) and ast.dump(new.operand) == ast.dump(old) \
                and isinstance(old, ast.AST):
            return [{"kind": "NEGATE", "at": path, "was": _unparse(old), "now": _unparse(new)}]
        if isinstance(old, ast.UnaryOp) and isinstance(old.op, ast.Not) and isinstance(new, ast.AST) \
                and ast.dump(old.operand) == ast.dump(new):
            return [{"kind": "NEGATE", "at": path, "was": _unparse(old), "now": _unparse(new)}]
        # A retyped STATEMENT is structural; a retyped EXPRESSION is a substitution and stays inside
        # the expression grammar. Conflating them overstates how much work needs new syntax.
        kind = "STRUCTURE" if isinstance(old, ast.stmt) and isinstance(new, ast.stmt) else "EXPRESSION"
        return [{"kind": kind, "at": path, "was": type(old).__name__, "now": type(new).__name__}]
    if isinstance(old, (ast.BinOp, ast.AugAssign, ast.UnaryOp)) and type(old.op) is not type(new.op):
        return [{"kind": "OPERATOR", "at": path, "was": type(old.op).__name__, "now": type(new.op).__name__}]
    if isinstance(old, ast.Compare):
        before = [type(o).__name__ for o in old.ops]
        after = [type(o).__name__ for o in new.ops]
        if before != after:
            return [{"kind": "OPERATOR", "at": path, "was": ",".join(before), "now": ",".join(after)}]
    if isinstance(old, ast.Constant):
        if old.value != new.value:
            return [{"kind": "CONSTANT", "at": path, "was": repr(old.value), "now": repr(new.value)}]
        return []
    if isinstance(old, ast.Name):
        if old.id != new.id:
            return [{"kind": "NAME", "at": path, "was": old.id, "now": new.id}]
        return []
    if isinstance(old, ast.arg):
        if old.arg != new.arg:
            return [{"kind": "NAME", "at": path, "was": old.arg, "now": new.arg}]
        return []
    if isinstance(old, ast.Attribute):
        if old.attr != new.attr:
            return [{"kind": "NAME", "at": path, "was": old.attr, "now": new.attr}]
        return classify_node(old.value, new.value, f"{path}.value")
    if isinstance(old, ast.Call):
        if ast.dump(old.func) != ast.dump(new.func):
            return [{"kind": "CALLEE", "at": path, "was": _unparse(old.func), "now": _unparse(new.func)}]
        if len(old.args) == len(new.args) and sorted(ast.dump(a) for a in old.args) == sorted(ast.dump(a) for a in new.args) \
                and [ast.dump(a) for a in old.args] != [ast.dump(a) for a in new.args]:
            return [{"kind": "ARGUMENT", "at": path,
                     "was": ",".join(_unparse(a) for a in old.args),
                     "now": ",".join(_unparse(a) for a in new.args)}]

    out: list[dict[str, str]] = []
    for field, old_value in ast.iter_fields(old):
        if field in ("ctx", "op", "ops"):
            continue
        new_value = getattr(new, field, None)
        if isinstance(old_value, list):
            if len(old_value) != len(new_value):
                # Only a statement list growing or shrinking means new syntax. A literal or argument
                # list changing length is a different expression of the same grammar.
                statement_list = field in ("body", "orelse", "finalbody", "handlers")
                out.append({"kind": "STRUCTURE" if statement_list else "EXPRESSION",
                            "at": f"{path}.{field}",
                            "was": f"{len(old_value)} items", "now": f"{len(new_value)} items"})
                continue
            for index, (a, b) in enumerate(zip(old_value, new_value)):
                out += classify_node(a, b, f"{path}.{field}[{index}]")
        elif isinstance(old_value, ast.AST) and isinstance(new_value, ast.AST):
            out += classify_node(old_value, new_value, f"{path}.{field}")
        elif old_value != new_value:
            out.append({"kind": "VALUE", "at": f"{path}.{field}",
                        "was": repr(old_value)[:48], "now": repr(new_value)[:48]})
    return out


def classify(old_source: str, new_source: str) -> dict[str, Any]:
    try:
        old_tree = strip_inert_strings(ast.parse(old_source))
        new_tree = strip_inert_strings(ast.parse(new_source))
    except SyntaxError as error:
        return {"kinds": ["UNPARSEABLE"], "edits": [], "detail": str(error)}
    edits = classify_node(old_tree, new_tree)
    # One site can only be one edit; a re-nesting of the same statement list is one STRUCTURE.
    seen, unique = set(), []
    for edit in edits:
        key = (edit["kind"], edit["at"])
        if key not in seen:
            seen.add(key)
            unique.append(edit)
    return {"kinds": sorted({e["kind"] for e in unique}), "edit_count": len(unique), "edits": unique[:12]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs).resolve()
    tasks = sorted(p.name[len("test_"):-len(".py")]
                   for p in (root / "python_testcases").glob("test_*.py"))
    rows = []
    for name in tasks:
        bad = root / "python_programs" / f"{name}.py"
        good = root / "correct_python_programs" / f"{name}.py"
        if not bad.is_file() or not good.is_file():
            rows.append({"task": name, "kinds": ["MISSING_SOURCE"], "edit_count": None, "edits": []})
            continue
        rows.append({"task": name, **classify(bad.read_text(), good.read_text())})

    exact = collections.Counter()
    involved = collections.Counter()
    for row in rows:
        kinds = row.get("kinds") or []
        exact["MULTI:" + "+".join(kinds) if len(kinds) > 1 else (kinds[0] if kinds else "NO_AST_DIFFERENCE")] += 1
        for kind in kinds:
            involved[kind] += 1

    #: Kinds a single-token mutation vocabulary can emit. STRUCTURE needs statement insertion or
    #: re-nesting, which a token swap cannot express; that split is the whole point of the table.
    token_kinds = {"OPERATOR", "NEGATE", "CONSTANT", "NAME", "CALLEE", "ARGUMENT"}
    single_token = sum(1 for row in rows
                       if row.get("kinds") and set(row["kinds"]) <= token_kinds)
    expression_only = sum(1 for row in rows
                          if row.get("kinds") and set(row["kinds"]) <= token_kinds | {"EXPRESSION"}
                          and "EXPRESSION" in row["kinds"])
    needs_structure = sum(1 for row in rows if "STRUCTURE" in (row.get("kinds") or []))
    receipt = {
        "schema": "BRAIN_QUIXBUGS_REQUIRED_EDIT_TAXONOMY_V1",
        "authority": "NONE__PRODUCER_RUN_ANALYSIS_OF_PUBLIC_CORPUS",
        "upstream": UPSTREAM,
        "tasks": len(rows),
        "exact_fix_type_tally": dict(sorted(exact.items())),
        "kind_involvement_tally": dict(sorted(involved.items())),
        "fixable_by_token_mutation_only": single_token,
        "needs_an_expression_substitution": expression_only,
        "requires_a_structural_edit": needs_structure,
        "reading": ("exact_fix_type_tally counts tasks by the exact set of atomic edit kinds their "
                    "published fix requires. fixable_by_token_mutation_only counts tasks whose entire "
                    "fix is a token-level change (operator, negation, literal, identifier, callee, "
                    "argument order); those are inside a token-mutation vocabulary. needs_an_expression_"
                    "substitution counts tasks whose fix stays inside expression grammar but replaces a "
                    "subexpression with one of a different shape, which a single-token swap cannot emit "
                    "either. requires_a_structural_edit counts tasks involving a STATEMENT that must be "
                    "added, removed, re-nested or retyped. The three counts partition the corpus."),
        "rows": rows,
    }
    pathlib.Path(args.out).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in ("tasks", "exact_fix_type_tally", "kind_involvement_tally",
                                              "fixable_by_token_mutation_only",
                                              "needs_an_expression_substitution",
                                              "requires_a_structural_edit")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
