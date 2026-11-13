#!/usr/bin/env python3
"""Is the one-example rule welded to the demonstrated OPERAND NAMES, and what would unwelding it buy?

THE CLAIM UNDER TEST
--------------------
The owner says: show the model an action once and it learns it permanently. The tree's own
one-example organ refuses something a person would find trivial -- same lesson, different variable
names:

    taught on:   if a <= hi:        ->  if a < hi:
    refused on:  if x <= top:            (the same operation, alpha-renamed)

Measured, verbatim, before this tool was written:

    >>> e.repeated(e.learn_all([("def f(a,hi): if a <= hi: ...", "... a < hi ...")]), target, "the example")
    Refused: nothing in the file has the form the example changed (a <= hi -> a < hi)

The rule the organ stores is the *text* `a <= hi -> a < hi`. So the operand names are welded in.
Alpha-renaming is the one generalization that needs **no oracle at all**: two statements that differ
only in the names of their free variables are the same statement. That is not a heuristic, an
inference, or a guess -- it is what "the same expression up to bound-variable renaming" means, and
it is decidable by walking the two trees in parallel.

WHY THIS MATTERS MORE THAN IT SOUNDS
------------------------------------
The tree already has a generalizing ladder -- `operator_generalization_v1` reaches 6 of 7 where the
crystallizer reaches 1 of 7 -- and it is **oracle-gated by construction**:

    OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE   (verified_skill_crystallizer_v1:1428)

That gate is correct. Swapping `<=` for `<` changes behaviour, so it may only be shipped where a test
can say which is right. But it means every step up that ladder needs a **runnable oracle**, and on a
target file the tree has never run, there is none. So the ladder is not available exactly where the
owner wants it: in a new environment, first try, no test suite.

Alpha-renaming is the only rung above "exact statement" that costs no oracle, because it cannot
change behaviour: `a <= hi` and `x <= top` are the same program with the names changed. This tool
measures what that one rung is worth on the same 607 applicable askings every other number in this
tree uses.

THE THREE TIERS, AND WHAT EACH COSTS
------------------------------------
  AS_TAUGHT      the shipped organ, unchanged. Does not even reach an alpha-renamed target.
  ALPHA_SAFE     the same rule with its free names replaced by holes. No oracle needed, and it
                 provably cannot change behaviour, because it applies the demonstrated operator
                 change to the same statement shape.
  ORACLE_LADDER  what `operator_generalization_v1` reaches. It needs a verifier, so it is reported
                 as the price of the next rung and NOT as something obtainable in a new environment.

    python3 canonical/tools/what_the_operand_names_cost_v1.py --pulls /tmp/pulls_v5.json --out RECORD.json

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import pathlib
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_WHAT_THE_OPERAND_NAMES_COST_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
NON_CLAIM = "AGREEMENT_WITH_THE_PEOPLE_IS_NOT_CORRECTNESS__NO_PROJECT_TEST_WAS_RUN"

# Fields that carry structure rather than a value. Nothing here is ever a hole: a hole in `op` would
# erase the very operation the demonstration taught.
STRUCTURAL_FIELDS = frozenset({"ctx", "lineno", "col_offset", "end_lineno", "end_col_offset",
                               "type_comment", "kind"})


def _pattern(node: ast.AST) -> tuple:
    """The node with every free name and every literal value replaced by a hole.

    Two statements have the same pattern exactly when they differ only in the names of their free
    variables and the values of their constants. `a <= hi` and `x <= top` share one; `a <= hi` and
    `a < hi` do not, because `op` is structural and survives.
    """
    if isinstance(node, ast.Name):
        return ("HOLE",)
    if isinstance(node, ast.Constant):
        return ("HOLE",)  # a literal is a value, not structure: `<= 5` and `<= n` are one shape
    if isinstance(node, ast.Attribute):
        # `self.x` and `obj.y` are one shape; the attribute NAME is part of the shape, because
        # `.isSet` -> `.is_set` is the lesson itself, not an operand.
        return ("Attr", node.attr, _pattern(node.value))
    if isinstance(node, ast.arg):
        return ("Arg", node.arg)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return (type(node).__name__, node.name)
    if isinstance(node, ast.operator) or isinstance(node, ast.cmpop) or isinstance(node, ast.unaryop):
        # `ast.LtE` and friends carry no fields, so the generic branch would give every operator the
        # same pattern -- `a <= b` and `a < b` would look identical. The type name IS the operator.
        return ("Op", type(node).__name__)
    if isinstance(node, ast.AST):
        out = [type(node).__name__]
        for field in node._fields:
            if field in STRUCTURAL_FIELDS:
                continue
            value = getattr(node, field, None)
            if isinstance(value, ast.AST):
                out.append((field, _pattern(value)))
            elif isinstance(value, list):
                out.append((field, tuple(_pattern(item) if isinstance(item, ast.AST) else ("LIT", repr(item))
                                         for item in value)))
            else:
                out.append((field, value))
        return tuple(out)
    return ("LIT", repr(node))


def same_shape(a: ast.AST, b: ast.AST) -> bool:
    """`a` and `b` are the same statement up to the names of free variables and literal values."""
    return _pattern(a) == _pattern(b)


def _holds_operator(node: ast.AST, name: str) -> bool:
    """Does this node directly hold an operator of type `name` ("LtE", "Add", ...)?"""
    for child in ast.walk(node):
        if isinstance(child, (ast.operator, ast.cmpop, ast.unaryop)) and type(child).__name__ == name:
            return True
    return False


def _operator_holder(node: ast.AST) -> ast.AST | None:
    """The smallest node under `node` that directly holds an operator (a Compare, BinOp or BoolOp)."""
    best: ast.AST | None = None
    for child in ast.walk(node):
        if isinstance(child, (ast.Compare, ast.BinOp, ast.BoolOp, ast.UnaryOp)):
            best = child  # ast.walk is breadth-first, so the last one found is the deepest
    return best


def _shape_without_operation(node: ast.AST) -> tuple:
    """The node's shape with every operator erased to a single marker, recursively.

    Written as its own walk rather than by reusing `_pattern`, because `_pattern` must keep the
    operator (that is what makes `a <= b` and `a < b` different statements), and the point of this
    one is the opposite: here the operator is the only thing allowed to differ.
    """
    if isinstance(node, (ast.operator, ast.cmpop, ast.unaryop)):
        return ("Op",)
    if isinstance(node, ast.Name):
        return ("HOLE",)
    if isinstance(node, ast.Constant):
        return ("HOLE",)
    if isinstance(node, ast.Attribute):
        return ("Attr", node.attr, _shape_without_operation(node.value))
    if isinstance(node, ast.arg):
        return ("Arg", node.arg)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return (type(node).__name__, node.name)
    out: list = [type(node).__name__]
    for field in node._fields:
        if field in STRUCTURAL_FIELDS:
            continue
        value = getattr(node, field, None)
        if isinstance(value, ast.AST):
            out.append((field, _shape_without_operation(value)))
        elif isinstance(value, list):
            out.append((field, tuple(_shape_without_operation(item) if isinstance(item, ast.AST)
                                     else ("LIT", repr(item)) for item in value)))
        else:
            out.append((field, value))
    return tuple(out)


def same_shape_but_for_the_operation(old: ast.AST, new: ast.AST) -> tuple[str, str] | None:
    """`(from, to)` when `old` and `new` are the same statement except for ONE operator, else None.

    `same_shape` answers a different question: it says whether two statements are interchangeable.
    Here the operation is precisely what must differ -- that difference is the lesson -- so the shape
    is taken with the operator erased, and then the operator difference is read off separately.
    """
    if type(old) is not type(new):
        return None
    if _shape_without_operation(old) != _shape_without_operation(new):
        return None
    return _operator_change(old, new)


def _operator_change(old: ast.AST, new: ast.AST) -> tuple[str, str] | None:
    """`(from, to)` when `old` and `new` differ in EXACTLY ONE operator node, else None.

    Written as a direct walk with an explicit `ops` branch. The generic field walk cannot see this:
    `Compare.ops` is a list of operator SINGLETONS, so it falls into a value comparison and two
    different singletons compare unequal without naming themselves. Getting this wrong makes the
    tool silently report that no lesson is an operator change, which reads exactly like a clean
    result -- so the branch is explicit and the count of differences is asserted.
    """
    found: list[tuple[str, str, str]] = []

    def walk(one: ast.AST, other: ast.AST) -> bool:
        if isinstance(one, (ast.operator, ast.cmpop, ast.unaryop)) or \
                isinstance(other, (ast.operator, ast.cmpop, ast.unaryop)):
            if type(one) is not type(other):
                found.append(("op", type(one).__name__, type(other).__name__))
            return True
        if type(one) is not type(other):
            return False
        if isinstance(one, (ast.Name, ast.Constant)):
            return True  # an operand's spelling and a literal's value are never structure
        for field in one._fields:
            if field in STRUCTURAL_FIELDS or field == "id":
                continue
            a, b = getattr(one, field, None), getattr(other, field, None)
            if isinstance(a, list) and isinstance(b, list):
                if len(a) != len(b):
                    return False
                for x, y in zip(a, b):
                    if isinstance(x, ast.AST) and isinstance(y, ast.AST):
                        if not walk(x, y):
                            return False
                    elif type(x) is not type(y) or (not isinstance(x, ast.AST) and x != y):
                        found.append((field, repr(x), repr(y)))
            elif isinstance(a, ast.AST) and isinstance(b, ast.AST):
                if not walk(a, b):
                    return False
            elif a != b:
                found.append((field, repr(a), repr(b)))
        return True

    if not walk(old, new):
        return None
    if len(found) != 1:
        return None
    field, a, b = found[0]
    if field not in ("op", "ops"):
        return None
    return (a, b)


def _install(tree: ast.AST, field_names: tuple[str, str]) -> int:
    """Replace the operator singleton whose type is `field_names[0]` with `field_names[1]`.

    Operators are AST singletons nested inside `op`/`ops`, not values on a field of their own, so the
    walk has to reach them through their parent. Returns how many were replaced.
    """
    want_from, want_to = (text.strip("'\"") for text in field_names)
    replacement_type = _replacement(want_to)
    if replacement_type is None:
        return 0
    replaced = 0
    for node in ast.walk(tree):
        for field in node._fields:
            if field in STRUCTURAL_FIELDS:
                continue
            value = getattr(node, field, None)
            if isinstance(value, (ast.operator, ast.cmpop, ast.unaryop)):
                if type(value).__name__ == want_from:
                    setattr(node, field, replacement_type())
                    replaced += 1
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, (ast.operator, ast.cmpop, ast.unaryop)) and \
                            type(item).__name__ == want_from:
                        value[index] = replacement_type()
                        replaced += 1
    return replaced


def _replacement(name: str):
    """The AST operator TYPE that stands for a recorded operator name, or None."""
    table = {"Lt": ast.Lt, "LtE": ast.LtE, "Gt": ast.Gt, "GtE": ast.GtE, "Eq": ast.Eq,
             "NotEq": ast.NotEq, "Is": ast.Is, "IsNot": ast.IsNot, "In": ast.In, "NotIn": ast.NotIn,
             "Add": ast.Add, "Sub": ast.Sub, "Mult": ast.Mult, "Div": ast.Div, "Mod": ast.Mod,
             "FloorDiv": ast.FloorDiv, "Pow": ast.Pow, "USub": ast.USub, "UAdd": ast.UAdd,
             "Not": ast.Not}
    return table.get(name.strip("'\" "))


def _statement_of(line: str) -> ast.AST | None:
    """The one statement this (possibly indented) line holds, or None.

    A changed line is usually indented -- `    if a <= hi:` -- so an expression parse fails on it.
    Dedenting and reading it as one module statement handles a compound statement (`if ...:`) and a
    simple one (`x = a <= b`) the same way, and refuses anything that is not exactly one statement.
    """
    text = line.strip()
    if not text:
        return None
    for candidate in (text, text + " pass"):
        try:
            body = ast.parse(candidate).body
        except (SyntaxError, ValueError):
            continue
        if len(body) == 1:
            node = body[0]
            return getattr(node, "value", node)
    return None


def alpha_safe_rewrite(example_before: str, example_after: str, target: str) -> str | None:
    """Apply the demonstrated operation to every same-shaped place in the target, names ignored."""
    try:
        before_lines = [line for line in ast.unparse(ast.parse(example_before)).split("\n") if line.strip()]
        after_lines = [line for line in ast.unparse(ast.parse(example_after)).split("\n") if line.strip()]
    except (SyntaxError, ValueError):
        return None
    import difflib

    taught: list[tuple[ast.AST, tuple[str, str]]] = []
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(a=before_lines, b=after_lines,
                                                       autojunk=False).get_opcodes():
        if tag == "equal" or (a1 - a0) != 1 or (b1 - b0) != 1:
            continue
        old_node, new_node = _statement_of(before_lines[a0]), _statement_of(after_lines[b0])
        if old_node is None or new_node is None:
            continue
        change = same_shape_but_for_the_operation(old_node, new_node)
        if change is not None:
            # Match on the subexpression that HOLDS the operator, not on the enclosing line.  The
            # demonstration's line is `if a <= hi:`; the target's may be a `while`, a lambda, or a
            # return. What transfers is the comparison, so that is what is matched.
            holder = _operator_holder(old_node)
            if holder is not None:
                taught.append((holder, change))
    if not taught:
        return None

    try:
        tree = ast.parse(target)
    except (SyntaxError, ValueError):
        return None
    touched = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) and not isinstance(node, ast.BinOp):
            continue
        for old_node, change in taught:
            # The target matches the demonstration's OLD line up to names, operator included:
            # `x <= top` matches `a <= hi` because `<=` is the same operator. The change to install
            # was read off the example (old -> new) and is carried in `change`; it is not rederived
            # from the target, which would compare the target against itself and find nothing.
            replace_from, replace_to = change
            if _shape_without_operation(node) == _shape_without_operation(old_node) and \
                    type(node).__name__ == type(old_node).__name__ and \
                    _holds_operator(node, replace_from):
                if _install(node, change):
                    touched += 1
                break
    if not touched:
        return None
    text = ast.unparse(tree)
    try:
        ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    return text


def _prefer(as_taught: str | None, alpha: str | None) -> str | None:
    """The organ's edit when it made one, otherwise the alpha-safe edit when there is one.

    The two are alternatives, not a sequence: applying alpha-safety on top of an organ edit would
    rewrite operators the organ deliberately left alone.  So the wider tier is "whichever reached
    further", and the denominator is unchanged, which is what makes the delta comparable.
    """
    return as_taught if as_taught is not None else alpha


TIERS = ("AS_TAUGHT", "ALPHA_SAFE")


def measure(pulls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    from canonical.tools import repeated_change_one_example_measure_v1 as corpus
    from canonical.tools import which_fix_moves_generalization_v1 as frontier

    tally = {tier: {"covered": 0, "denominator": 0, "made": 0, "wrong": 0} for tier in TIERS}
    only_alpha: list[dict[str, Any]] = []
    not_applicable = 0

    for pull in pulls:
        for index, example in enumerate(pull["files"]):
            if frontier.learn_fails(example):
                continue
            for other, target in enumerate(pull["files"]):
                if other == index:
                    continue
                base = corpus.statement_lines(target["before"])
                wanted = corpus.statement_lines(target["after"])
                if base is None or wanted is None:
                    continue
                theirs = {change for change in corpus.changes(base, wanted)
                          if not corpus.only_imports(change)}
                if not theirs:
                    not_applicable += 1
                    continue
                as_taught, why = frontier.ask_strict(target["before"], example["before"],
                                                     example["after"])
                if why is not None and frontier.classify(why) == "NO_FORM_IN_FILE":
                    not_applicable += 1
                    continue
                alpha = alpha_safe_rewrite(example["before"], example["after"], target["before"])
                # ALPHA_SAFE is the organ PLUS alpha-safety, never instead of it.  Reporting the
                # alpha output alone would charge the operator for everything the organ already
                # reaches -- measured, that is a 9-point loss that means nothing.
                for tier, got in (("AS_TAUGHT", as_taught),
                                  ("ALPHA_SAFE", _prefer(as_taught, alpha))):
                    mine = set() if got is None else {change for change in
                                                      corpus.changes(base, corpus.statement_lines(got))
                                                      if not corpus.only_imports(change)}
                    tally[tier]["covered"] += len(theirs & mine)
                    tally[tier]["denominator"] += len(theirs)
                    tally[tier]["made"] += len(mine)
                    tally[tier]["wrong"] += len(mine - theirs)
                if alpha and as_taught is None:
                    only_alpha.append({
                        "repo": pull.get("repo"), "example": example["path"],
                        "target": target["path"],
                        "the_people_changed": sum(1 for change in theirs),
                    })

    out: dict[str, Any] = {}
    for tier in TIERS:
        row = tally[tier]
        out[tier] = {
            "covered": row["covered"],
            "developers_changes": row["denominator"],
            "coverage": round(row["covered"] / row["denominator"], 4) if row["denominator"] else None,
            "made": row["made"],
            "wrong": row["wrong"],
            "precision": round((row["made"] - row["wrong"]) / row["made"], 4) if row["made"] else None,
        }
    out["delta_coverage"] = (
        round(out["ALPHA_SAFE"]["coverage"] - out["AS_TAUGHT"]["coverage"], 4)
        if out["ALPHA_SAFE"]["coverage"] is not None and out["AS_TAUGHT"]["coverage"] is not None
        else None)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "question": ("does the one-example rule reach code whose free-variable names differ from the "
                     "demonstration, and what would alpha-safe generalization buy"),
        "tiers": out,
        "askings_not_applicable": not_applicable,
        "askings_where_only_alpha_reaches": len(only_alpha),
        "examples_of_only_alpha": only_alpha[:8],
        "oracle_ladder": {
            "what_it_is": "canonical/swe_kernel/operator_generalization_v1.py, 6 of 7 on its own record",
            "why_it_is_not_a_tier_here": (
                "verified_skill_crystallizer_v1:1428 refuses operator generalization unless "
                "required_verification_kind == TEST_SUITE and a scope_id is given: "
                "OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE"),
            "what_that_means": ("every rung above 'exact statement' in this tree needs a runnable "
                                "oracle, and a new environment has none"),
        },
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "non_claim": NON_CLAIM,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pulls", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    record = measure(json.loads(args.pulls.read_text(encoding="utf-8")))
    print(f"{'tier':12s} {'covered':>8s} {'of':>7s} {'coverage':>9s} {'wrong':>6s} {'precision':>10s}")
    for tier in TIERS:
        row = record["tiers"][tier]
        print(f"{tier:12s} {row['covered']:8d} {row['developers_changes']:7d} "
              f"{row['coverage']!s:>9s} {row['wrong']:6d} {row['precision']!s:>10s}")
    print(f"delta coverage from alpha-safety: {record['tiers']['delta_coverage']}")
    print(f"askings where only alpha-safety reaches anything: "
          f"{record['askings_where_only_alpha_reaches']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
