"""Can the registry's success predicate ever say no?

`THE_ONE_SHOT_REGIME_IS_41_PERCENT_20261112_V1.md` counted 60 of 145 bound capabilities as
"one-shot safe" on the strength of a typed interface and a receipted independent check. That count
assumes the *runtime* gate is a gate. This probe tests the assumption statically.

For every bound capability it reads the declared action template and the adapter source, and asks
one question:

    given this adapter's code, is there any way the declared `expect` predicate evaluates to false?

The classes, from strongest finding to weakest:

  DECLARATION_MISMATCH   the predicate reads a field the capability does not declare in
                         `result_fields`. The template and the tool's own contract disagree.
  NO_SOURCE              the adapter path is not present in the tree, so nothing can be read.
  ALWAYS_TRUE_NO_RAISE   every assignment to the field is the expected literal AND the module
                         contains no raise/assert: success is reported unconditionally and
                         nothing signals failure.
  ALWAYS_TRUE_RAISES     same assignments, but the module raises on failure. The gate is the
                         exception, not the predicate -- honest, but the predicate adds nothing.
  DYNAMIC                some assignment is computed, so the predicate can differ from success.
  NOT_STATICALLY_VISIBLE the field is never assigned in this module (set by a framework, a
                         helper, or a callee); this probe cannot judge it and says so.

Only `ALWAYS_TRUE_NO_RAISE` and `DECLARATION_MISMATCH` are defects. The rest are honest states,
and the distinction is the point: a predicate that cannot fail is not a check, but a tool that
raises instead is not lying.

Static, deterministic, executes nothing. Authority NONE.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

DECLARATION_MISMATCH = "DECLARATION_MISMATCH"
NO_SOURCE = "NO_SOURCE"
ALWAYS_TRUE_NO_RAISE = "ALWAYS_TRUE_NO_RAISE"
ALWAYS_TRUE_UNGUARDED_RAISES = "ALWAYS_TRUE_UNGUARDED_RAISES"
ALWAYS_TRUE_GUARDED_RAISES = "ALWAYS_TRUE_GUARDED_RAISES"
DYNAMIC = "DYNAMIC"
NOT_STATICALLY_VISIBLE = "NOT_STATICALLY_VISIBLE"

DEFECTS = (DECLARATION_MISMATCH, ALWAYS_TRUE_NO_RAISE)


def _assigned_values(tree: ast.AST, field: str) -> list[ast.AST]:
    """Every right-hand side assigned to ``field`` as a dict key or subscript, anywhere in the module."""
    values: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    key = target.slice
                    if isinstance(key, ast.Constant) and key.value == field:
                        values.append(node.value)
                elif isinstance(target, ast.Name) and target.id == field:
                    values.append(node.value)
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == field:
                    values.append(v)
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Subscript):
                key = target.slice
                if isinstance(key, ast.Constant) and key.value == field and node.value is not None:
                    values.append(node.value)
    return values


def _is_constant(value: ast.AST) -> tuple[bool, Any]:
    if isinstance(value, ast.Constant):
        return True, value.value
    return False, None


GUARD_NODES = (ast.If, ast.Try, ast.While, ast.For, ast.AsyncFor, ast.Assert,
               ast.With, ast.AsyncWith)


def _guarded_assignments(tree: ast.AST, field: str) -> tuple[int, int]:
    """(guarded, unguarded) assignments to ``field``.

    An assignment inside an ``if``/``try``/``assert`` is reported only when a condition held.
    An assignment at function-body level is reported on every path that reaches it, so the value
    carries no information about whether the work succeeded.
    """
    guarded = unguarded = 0

    def visit(node: ast.AST, depth: int) -> None:
        nonlocal guarded, unguarded
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    key = target.slice
                    if isinstance(key, ast.Constant) and key.value == field:
                        if depth > 0:
                            guarded += 1
                        else:
                            unguarded += 1
        for child in ast.iter_child_nodes(node):
            visit(child, depth + 1 if isinstance(child, GUARD_NODES) else depth)

    # Start at module level; the depth counter only increments on guard nodes, so a plain
    # function body does not count as a guard.
    visit(tree, 0)
    return guarded, unguarded


def _signals_failure(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"exit", "_fail", "fail", "die"}:
                return True
    return False


def classify(capability_id: str, row: dict[str, Any], root: Path) -> dict[str, Any]:
    template = row.get("action_template") or {}
    expect = template.get("expect") or {}
    field = expect.get("field")
    expected = expect.get("value")
    result_fields = list(row.get("result_fields") or [])
    adapter = (row.get("source") or {}).get("adapter_path")

    base = {
        "capability_id": capability_id,
        "expect_type": expect.get("type"),
        "expect_field": field,
        "adapter_path": adapter,
        "assignments": 0,
        "signals_failure": False,
    }

    if not field or not adapter:
        return {**base, "class": NOT_STATICALLY_VISIBLE, "why": "no field or no adapter path"}

    path = root / str(adapter)
    if not path.is_file():
        return {**base, "class": NO_SOURCE, "why": "adapter not in tree"}

    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    signals = _signals_failure(tree)
    values = _assigned_values(tree, str(field))
    base["assignments"] = len(values)
    base["signals_failure"] = signals

    declared_mismatch = field not in result_fields
    if declared_mismatch and not values:
        return {**base, "class": DECLARATION_MISMATCH,
                "why": "predicate field is not among the capability's declared result_fields"}

    if not values:
        if declared_mismatch:
            return {**base, "class": DECLARATION_MISMATCH,
                    "why": "predicate field undeclared and never assigned in the module"}
        return {**base, "class": NOT_STATICALLY_VISIBLE,
                "why": "field not assigned in this module"}

    all_constant = True
    all_equal = True
    for value in values:
        constant, literal = _is_constant(value)
        if not constant:
            all_constant = False
            continue
        if literal != expected:
            all_equal = False

    if not all_constant or not all_equal:
        return {**base, "class": DYNAMIC, "why": "a computed or differing value is assigned"}

    guarded, unguarded = _guarded_assignments(tree, str(field))
    base["guarded_assignments"] = guarded
    base["unguarded_assignments"] = unguarded

    if signals and unguarded == 0:
        return {**base, "class": ALWAYS_TRUE_GUARDED_RAISES,
                "why": "the expected literal is assigned only under a condition, and the module raises"}
    if signals:
        return {**base, "class": ALWAYS_TRUE_UNGUARDED_RAISES,
                "why": "expected literal assigned unconditionally; failure signalled only by a raise elsewhere"}
    return {**base, "class": ALWAYS_TRUE_NO_RAISE,
            "why": "only the expected literal is assigned and nothing raises"}


def run(root: Path = ROOT, registry: Path = REGISTRY) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = json.loads(registry.read_text(encoding="utf-8"))["capabilities"]
    records = [classify(cid, row, root) for cid, row in sorted(rows.items())]

    counts: dict[str, int] = {}
    for r in records:
        counts[r["class"]] = counts.get(r["class"], 0) + 1

    defects = [r for r in records if r["class"] in DEFECTS]
    return {
        "schema": "RUNTIME_PREDICATE_FALSIFIABILITY_V1",
        "authority": "NONE",
        "summary": {
            "capabilities": len(records),
            "classes": dict(sorted(counts.items())),
            "defects": len(defects),
            "defect_ids": [r["capability_id"] for r in defects],
        },
        "records": records,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--list-defects", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = run()
    s = result["summary"]

    print("runtime predicate falsifiability  --  static, executes nothing, authority NONE\n")
    for name in (DECLARATION_MISMATCH, ALWAYS_TRUE_NO_RAISE, ALWAYS_TRUE_UNGUARDED_RAISES,
                 ALWAYS_TRUE_GUARDED_RAISES, DYNAMIC, NOT_STATICALLY_VISIBLE, NO_SOURCE):
        print(f"  {name:<24}{s['classes'].get(name, 0):>5}")
    print(f"\n  {'defects':<24}{s['defects']:>5}   "
          f"(DECLARATION_MISMATCH + ALWAYS_TRUE_NO_RAISE)")

    if args.list_defects:
        print("\ndefects:")
        for r in result["records"]:
            if r["class"] in DEFECTS:
                print(f"  {r['class']:<22}{r['capability_id']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("WROTE", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
