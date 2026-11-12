"""Does the acceptance predicate read the answer, or only the receipt that something was written?

`THE_GATE_IS_NOT_A_RUBBER_STAMP_20261112_V1.md` found seven adapters that assign
``output_verified: True`` unconditionally. It called them "weak gates". Reading them is worse than
that, and better: in the repair family the same returned object also carries a computed ``pass``,
and the registered acceptance predicate does not read it.

    result = {..., "status": "OPEN__NO_VERIFIED_REPAIR...", "pass": winner is not None, ...}
    out.write_text(json.dumps(result))
    result["output_verified"] = True
    return result

A run that found nothing therefore writes its "nothing" to disk, marks the artifact verified, and
satisfies ``expect: output_verified == true``. The gate answers *"was a file produced?"* while the
answer to *"was the problem solved?"* sits two keys away.

This probe classifies every bound capability by which of those two questions its predicate asks,
and names the field it should read when the answer is already present in the result object.

It changes nothing. Repointing a predicate narrows what the planner accepts, and that decision
needs its own evidence rather than riding along with a measurement.

Static, deterministic, executes nothing. Authority NONE.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

TRANSPORT_FIELDS = frozenset(
    {"output_verified", "output_sha256", "output_path", "written", "exists", "byte_count",
     "bytes", "path", "sha256", "member_count", "destination_sha256", "destination_path"}
)
# Preference order matters: a boolean the adapter computed from its own verification beats a
# display string, which beats a number that would need a threshold nobody declared.
OUTCOME_FIELDS = ("pass", "accepted", "success", "verified", "answer", "status", "score")

INDEPENDENT_CHECK_TYPES = frozenset({"file_sha256_matches", "taught_program_recomputed"})

READS_INDEPENDENT_CHECK = "READS_INDEPENDENT_CHECK"
READS_TRANSPORT_OUTCOME_AVAILABLE = "READS_TRANSPORT_OUTCOME_AVAILABLE"
READS_TRANSPORT_NO_OUTCOME = "READS_TRANSPORT_NO_OUTCOME"
READS_OUTCOME = "READS_OUTCOME"
READS_NEITHER = "READS_NEITHER"
NO_SOURCE = "NO_SOURCE"


def _computed_assignments(tree: ast.AST, field: str) -> int:
    """Assignments to ``field`` whose right-hand side is not a literal.

    A literal is a constant the code chose, not a measurement it made. Only a computed value can
    differ between a solved problem and an unsolved one.
    """
    count = 0
    for node in ast.walk(tree):
        pairs: list[tuple[ast.AST | None, ast.AST]] = []
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    key = target.slice
                    if isinstance(key, ast.Constant) and key.value == field:
                        pairs.append((key, node.value))
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == field:
                    pairs.append((k, v))
        for _key, value in pairs:
            if not isinstance(value, ast.Constant):
                count += 1
    return count


def classify(capability_id: str, row: dict[str, Any], root: Path) -> dict[str, Any]:
    template = row.get("action_template") or {}
    expect = template.get("expect") or {}
    field = expect.get("field")
    result_fields = list(row.get("result_fields") or ())
    adapter = (row.get("source") or {}).get("adapter_path")

    base: dict[str, Any] = {
        "capability_id": capability_id,
        "expect_field": field,
        "expect_type": expect.get("type"),
        "adapter_path": adapter,
        "candidate_outcome_field": None,
        "outcome_is_computed": False,
    }

    # A digest comparison against the source, or a recomputation, checks content rather than
    # existence. It is not transport even though the field is named after a hash.
    if expect.get("type") in INDEPENDENT_CHECK_TYPES:
        return {**base, "class": READS_INDEPENDENT_CHECK}

    if field in OUTCOME_FIELDS:
        return {**base, "class": READS_OUTCOME}

    if field not in TRANSPORT_FIELDS:
        return {**base, "class": READS_NEITHER}

    if not adapter:
        return {**base, "class": READS_TRANSPORT_NO_OUTCOME, "why": "no adapter path"}

    path = root / str(adapter)
    if not path.is_file():
        return {**base, "class": NO_SOURCE}

    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))

    best: tuple[str, int] | None = None
    for candidate in OUTCOME_FIELDS:
        computed = _computed_assignments(tree, candidate)
        if computed and (best is None or computed > best[1]):
            best = (candidate, computed)
        if computed and candidate in ("pass", "accepted", "success"):
            break  # a computed boolean is the strongest available answer field

    if best is None:
        return {**base, "class": READS_TRANSPORT_NO_OUTCOME,
                "why": "no computed outcome field in the adapter"}

    candidate, computed = best
    declared = candidate in result_fields
    # Only a computed BOOLEAN that the capability also declares is unambiguous: `pass` is what
    # the adapter decided, `status` is a display string, `score` needs a threshold nobody
    # declared. Everything else is a candidate for a human to read, not a fix to apply.
    definite = declared and candidate in ("pass", "accepted", "success")
    return {
        **base,
        "class": READS_TRANSPORT_OUTCOME_AVAILABLE,
        "candidate_outcome_field": candidate,
        "outcome_is_computed": True,
        "outcome_assignments": computed,
        "candidate_declared_in_result_fields": declared,
        "confidence": "DEFINITE" if definite else "CANDIDATE",
    }


def run(root: Path = ROOT, registry: Path = REGISTRY) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = json.loads(registry.read_text(encoding="utf-8"))["capabilities"]
    records = [classify(cid, row, root) for cid, row in sorted(rows.items())]

    counts: dict[str, int] = {}
    for r in records:
        counts[r["class"]] = counts.get(r["class"], 0) + 1

    fixable = [r for r in records if r["class"] == READS_TRANSPORT_OUTCOME_AVAILABLE]
    return {
        "schema": "ACCEPTANCE_PREDICATE_TARGET_V1",
        "authority": "NONE",
        "summary": {
            "capabilities": len(records),
            "classes": dict(sorted(counts.items())),
            "reads_transport_while_outcome_available": len(fixable),
            "outcome_not_declared": sum(
                1 for r in fixable if not r.get("candidate_declared_in_result_fields")
            ),
            "definite": sum(1 for r in fixable if r.get("confidence") == "DEFINITE"),
        },
        "fix_list": [
            {
                "capability_id": r["capability_id"],
                "expect_field": r["expect_field"],
                "should_read": r["candidate_outcome_field"],
                "outcome_declared": r["candidate_declared_in_result_fields"],
                "confidence": r.get("confidence"),
            }
            for r in fixable
        ],
        "records": records,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--list-fixes", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = run()
    s = result["summary"]

    print("acceptance predicate target  --  static, executes nothing, authority NONE\n")
    for name in (READS_INDEPENDENT_CHECK, READS_OUTCOME, READS_TRANSPORT_OUTCOME_AVAILABLE,
                 READS_TRANSPORT_NO_OUTCOME, READS_NEITHER, NO_SOURCE):
        print(f"  {name:<38}{s['classes'].get(name, 0):>5}")
    print(f"\n  reads transport while some outcome is computed   "
          f"{s['reads_transport_while_outcome_available']:>4}")
    print(f"  ...of which the outcome is a declared boolean    {s['definite']:>4}   (DEFINITE)")
    print(f"  ...of which the outcome field is undeclared      {s['outcome_not_declared']:>4}")

    if args.list_fixes:
        print("\nrepoint the predicate:")
        for row in result["fix_list"]:
            declared = "" if row["outcome_declared"] else "   (outcome field undeclared)"
            print(f"  {row['confidence']:<10}{row['capability_id']:<52}"
                  f"{row['expect_field']} -> {row['should_read']}{declared}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("WROTE", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
