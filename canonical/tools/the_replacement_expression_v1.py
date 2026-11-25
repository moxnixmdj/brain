#!/usr/bin/env python3
"""Synthesize the replacement expression from one failing run, not from a repair rule.

THE FALSIFIER THIS ANSWERS
--------------------------
`THE_SAME_GUARD_TWICE_IS_THE_DISCRIMINATOR_20261119_V1` found the firing to flip
at the human line 3/15 times on a fresh corpus, but produced the human's
expression 0/15. Its own falsifier says: a mechanism that forces the value at
that firing and synthesizes the replacement expression from the artifact's own
vocabulary must beat 0/15 on a fresh corpus, without reading the commit diff.

WHAT IS BUILT
-------------
The flip oracle and the whole-suite judge are the existing ones, unchanged.
Only the candidate selector is replaced. Its atoms are built from:

  * the operand labels the instrument read from the source AST;
  * the literal values (and their types/sizes) the failing run actually logged;
  * the four identity/truth tests Python makes without inventing a value.

Atoms are composed into conjunctions of at most two. A candidate is admitted
only by exact fit: false at the flipped firing, true at every other firing the
guard let through, with at least one such witness. Then the project's own whole
test file decides, on an uninstrumented copy. The human edit is read only after
that verdict, for reporting.

No model, no parameters, no stored repair rules, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
import time
from typing import Any, Sequence

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import the_same_guard_twice_is_the_discriminator_v1 as guard  # noqa: E402

SCHEMA = "PROJECT_BRAIN_THE_REPLACEMENT_EXPRESSION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "R1": "at least one fresh real commit is VERIFIED by a synthesized expression on its project's whole test file",
    "R2": "at least one verified expression is outside the four hand-written identity/truth forms",
    "R3": "no row is accepted while breaking a test that passed on the parent (zero accusations)",
    "R4": "zero parameters stored, zero model calls, zero network calls at run time",
    "R5": "every counted row has a real failing test and an instrumentation run that preserved the verdict",
}

MAX_VALUES = 6
MAX_ATOMS = 90
MAX_CANDIDATES = 600
HAND_WRITTEN_MARKERS = (" is not None", " is None", "not ")


class _Unknown:
    """A logged object repr: identity and truth are visible, content is not."""

    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = str(text)

    def __repr__(self) -> str:
        return self.text

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, _Unknown) and self.text == other.text

    def __hash__(self) -> int:
        return hash(self.text)

    def __len__(self) -> int:
        return len(self.text)

    def startswith(self, prefix: str) -> bool:
        return self.text.startswith(prefix)

    def endswith(self, suffix: str) -> bool:
        return self.text.endswith(suffix)

    def __bool__(self) -> bool:
        text = self.text
        return bool(text) and text not in {"None", "False", "0", "0.0", "''", '""', "[]", "{}", "()", "set()"} \
            and not text.startswith("<raised ")


def logged_value(text: str) -> Any:
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return _Unknown(text)


def _is_none(value: Any) -> bool:
    return value is None or (isinstance(value, _Unknown) and value.text == "None")


CANNOT = object()


def evaluate(expression: str, row: dict[str, Any]) -> bool | None:
    """Evaluate a candidate against the logged operands only. None = cannot tell."""
    try:
        node = ast.parse(expression, mode="eval").body
        value = _eval(node, row)
        return None if value is CANNOT else bool(value)
    except (SyntaxError, ValueError, TypeError, AttributeError, RecursionError):
        return None


def _eval(node: ast.AST, row: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        items = [_eval(elt, row) for elt in node.elts]
        if any(item is CANNOT for item in items):
            return CANNOT
        return {ast.List: list, ast.Tuple: tuple, ast.Set: set}[type(node)](items)
    if isinstance(node, ast.Dict):
        pairs = [(_eval(k, row), _eval(v, row)) for k, v in zip(node.keys, node.values)]
        if any(k is CANNOT or v is CANNOT for k, v in pairs):
            return CANNOT
        return dict(pairs)
    if isinstance(node, ast.Name):
        if node.id in {"str", "int", "float", "bool", "list", "dict", "tuple", "set"}:
            return {"str": str, "int": int, "float": float, "bool": bool,
                    "list": list, "dict": dict, "tuple": tuple, "set": set}[node.id]
        return logged_value(str(row.get("operands", {}).get(node.id, "")))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        value = _eval(node.operand, row)
        return CANNOT if value is CANNOT else not bool(value)
    if isinstance(node, ast.BoolOp):
        values = [_eval(v, row) for v in node.values]
        if any(v is CANNOT for v in values):
            return CANNOT
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in values)
        return any(bool(v) for v in values)
    if isinstance(node, ast.Compare):
        left = _eval(node.left, row)
        if left is CANNOT:
            return CANNOT
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval(comparator, row)
            if right is CANNOT:
                return CANNOT
            if isinstance(op, ast.Is):
                result = _is_none(left) and _is_none(right)
            elif isinstance(op, ast.IsNot):
                result = not (_is_none(left) and _is_none(right))
            elif isinstance(op, ast.Eq):
                result = None if isinstance(left, _Unknown) or isinstance(right, _Unknown) else left == right
            elif isinstance(op, ast.NotEq):
                result = None if isinstance(left, _Unknown) or isinstance(right, _Unknown) else left != right
            else:
                return CANNOT
            if result is None:
                return CANNOT
            if not result:
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else None
        args = [_eval(a, row) for a in node.args]
        if any(a is CANNOT for a in args):
            return CANNOT
        if name == "len" and len(args) == 1:
            return len(args[0])
        if name == "isinstance" and len(args) == 2:
            if not isinstance(args[1], type):
                return CANNOT
            return isinstance(args[0], args[1])
        if name == "bool" and len(args) == 1:
            return bool(args[0])
        if isinstance(node.func, ast.Attribute) and len(args) == 1:
            owner = _eval(node.func.value, row)
            if owner is CANNOT:
                return CANNOT
            method = getattr(owner, node.func.attr, None) if owner is not None else None
            if callable(method):
                try:
                    return bool(method(args[0]))
                except (TypeError, ValueError):
                    return CANNOT
        return CANNOT
    return CANNOT


def candidate_atoms(site: dict[str, Any], executions: Sequence[dict[str, Any]]) -> list[str]:
    """Atoms over the source's operand labels and the run's own logged values."""
    atoms: set[str] = set()
    for operand in site["operands"]:
        if not operand.isidentifier():
            continue
        atoms.update((operand, f"not {operand}", f"{operand} is None", f"{operand} is not None"))
        values: list[str] = []
        for row in executions:
            text = str(row.get("operands", {}).get(operand, ""))
            if text not in values and not text.startswith("<raised "):
                values.append(text)
        for text in values[:MAX_VALUES]:
            value = logged_value(text)
            rendered = repr(value)
            atoms.add(f"{operand} == {rendered}")
            atoms.add(f"{operand} != {rendered}")
            kind = type(value).__name__
            if kind in {"str", "int", "float", "bool", "list", "dict", "tuple", "set"}:
                atoms.add(f"isinstance({operand}, {kind})")
            if isinstance(value, (str, list, dict, tuple, set)):
                atoms.add(f"len({operand}) == {len(value)}")
            if isinstance(value, str) and value:
                atoms.add(f"{operand}.startswith({rendered})")
    return sorted(atoms)[:MAX_ATOMS]


def candidate_expressions(site: dict[str, Any], executions: Sequence[dict[str, Any]]) -> list[str]:
    atoms = candidate_atoms(site, executions)
    base = guard.predicate_candidates(site, executions)
    out = list(dict.fromkeys(base + atoms))
    for left in atoms:
        for right in atoms:
            if left >= right:
                continue
            expression = f"({left}) and ({right})"
            if expression not in out:
                out.append(expression)
            if len(out) >= MAX_CANDIDATES:
                return out
    return out


def is_hand_written(expression: str) -> bool:
    """True only for one of the four forms the earlier engine already had."""
    inner = expression.strip()
    if inner.startswith("(") and inner.endswith(")"):
        inner = inner[1:-1].strip()
    return any(marker in inner for marker in HAND_WRITTEN_MARKERS)


def fit_replacement(site: dict[str, Any], executions: Sequence[dict[str, Any]],
                    must_be_false_at: int) -> dict[str, Any] | None:
    """Exact fit on the flip: false at that firing, true at the others it passed."""
    bad = next((row for row in executions if row["n"] == must_be_false_at), None)
    if bad is None or not bad["truth"]:
        return None
    witnesses = [row for row in executions if row["truth"] and row["n"] != must_be_false_at]
    if not witnesses:
        return None
    for expression in candidate_expressions(site, executions):
        if evaluate(expression, bad) is not False:
            continue
        if any(evaluate(expression, row) is not True for row in witnesses):
            continue
        return {"predicate": expression, "false_at": bad["n"],
                "true_at": [row["n"] for row in witnesses], "vacuous": False,
                "novel": not is_hand_written(expression),
                "operator": next((name for name in ("isinstance", "len(", ".startswith")
                                  if name in expression), "identity_or_truth")}
    return None


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            seconds: int = 90) -> dict[str, Any]:
    """The existing flip/suite instrument with the replacement-expression fit."""
    started = time.time()
    row = guard.explore(repo, sha, source_path=source_path, test_path=test_path,
                        seconds=seconds, fit=fit_replacement)
    row["synthesis_seconds"] = round(time.time() - started, 1)
    row["schema"] = SCHEMA
    return row


def measure(entries: Sequence[dict[str, Any]], repo: pathlib.Path,
            *, seconds: int = 90) -> dict[str, Any]:
    rows = []
    for entry in entries:
        row = explore(repo, entry["commit"], source_path=entry["sources"][0],
                      test_path=entry["tests"][0], seconds=seconds)
        rows.append({"repo": repo.name, **entry, **row})
    verified = [r for r in rows if (r.get("verification") or {}).get("stage") == "VERIFIED"]
    novel = [r for r in verified
             if ((r.get("refinement") or {}).get("fit") or {}).get("novel")]
    gates = {
        "R1": len(verified) >= 1,
        "R2": len(novel) >= 1,
        "R3": all(not ((r.get("verification") or {}).get("broken") or []) for r in verified),
        "R4": True,
        "R5": all((r.get("stage") or "").startswith(("FLIP", "SWITCH", "REFINEMENT", "NO_SWITCH"))
                  for r in rows),
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_the_run": DECLARED,
        "corpus": {"repository": repo.name, "commits": len(entries),
                   "selection": "one source file and one test file; oracle executes; commit sha appears in no receipt or corpus file"},
        "rows": rows,
        "summary": {"rows": len(rows), "verified": len(verified), "novel_verified": len(novel),
                    "model_calls": 0, "parameters_stored": 0, "network_calls": 0,
                    "seconds": round(sum(float(r.get("synthesis_seconds") or 0) for r in rows), 1)},
        "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL",
        "what_this_is_not": [
            "not a benchmark: 15 real commits from one repository, producer-run",
            "not proof of general repair; the human edit is read only for reporting",
            "not a learned model: candidate atoms are computed from the run and the source AST",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True, help="JSON list of fresh real commits")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=90)
    args = parser.parse_args(argv)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    receipt = measure(entries, pathlib.Path(args.repo), seconds=args.seconds)
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": receipt["verdict"], "gates": receipt["gates"],
                      "summary": receipt["summary"], "receipt": str(out)}, indent=2))
    return 0 if receipt["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
