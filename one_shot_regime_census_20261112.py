"""How much of Brain's own bound surface is in the regime where one try is safe?

`ONE_TRY_BUYS_A_RULE_THAT_IS_WRONG_20261112_V1.md` measured that a single demonstration leaves
~14 of 47 programs standing, and named the only regime where that does not matter:

    one try is enough exactly when the interface and the verifier already do the generalising.

That sentence is only useful if it can be pointed at this repository. This census does that,
using the registry the tree already keeps, with two axes and no judgement calls:

  * **typed interface** -- an entry point, typed arguments, and declared result fields. This is
    the `environment_fit_v1` shape: code against a declared contract. In that regime the
    interface *is* the prior, so a one-shot lesson is a program, not an induction.
  * **verifier strength** -- whether the capability's qualification declares independence, and
    whether the receipt it names is actually present in the tree:
        RECEIPTED  independence declared AND the named receipt exists on disk
        DECLARED   independence declared, but no receipt on disk
        NONE       no independence marker at all

A declaration is not verification -- this repository's own law says verification means someone
else ran it. So `DECLARED` is deliberately *not* counted as safe, and the difference between
DECLARED and RECEIPTED is reported rather than smoothed away.

A third, separate axis is reported because it is the one that matters at runtime: does the action
template's success predicate read a field the capability itself emits? A capability that reports
its own success is not necessarily wrong; it is simply not checked by anything else.

Authority: NONE. Structural census of declared metadata. It measures what the registry claims,
not whether the claims are true, and it never runs a capability.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

INDEPENDENCE_MARKERS = (
    "independently_verified",
    "independent_verified",
    "independently_verified_by",
    "producer_independent",
    "independent_verifier",
    "independent_oracle",
    "independent_recomputation",
    "independent_semantic_verification",
    "independent_falsification_passed",
    "independent_output_sha256",
    "independent_personnel_verification",
    "independent_reference_evidence",
)

RECEIPTED = "RECEIPTED"
DECLARED = "DECLARED"
NONE = "NONE"


NEGATIVE_VOCABULARY = frozenset(
    {"", "false", "no", "none", "null", "pending", "unverified", "unknown", "n/a", "not_run"}
)


def truthy(value: Any) -> bool:
    """A marker counts only when it actually says something.

    ``independently_verified_by`` names the verifier (``"archive.verify.tar_gz.gnu"``), so a
    non-empty string is a declaration. A negated vocabulary is what must not count: a marker
    whose value is ``"pending"`` or ``"false"`` is a statement that no check happened, and
    reading it as one would inflate every count in this census.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() not in NEGATIVE_VOCABULARY
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (list, dict)):
        return bool(value)
    return False


def classify(capability_id: str, row: dict[str, Any], root: Path) -> dict[str, Any]:
    template = row.get("action_template") or {}
    verification = row.get("verification") or {}
    result_fields = list(row.get("result_fields") or [])

    typed = bool(row.get("entrypoint")) and bool(template.get("args")) and bool(result_fields)

    markers = sorted(m for m in INDEPENDENCE_MARKERS if truthy(verification.get(m)))
    receipt_path = verification.get("receipt_path")
    receipt_present = bool(receipt_path) and (root / str(receipt_path)).is_file()

    if markers and receipt_present:
        strength = RECEIPTED
    elif markers:
        strength = DECLARED
    else:
        strength = NONE

    expect = template.get("expect") or {}
    expect_field = expect.get("field")
    self_reported = bool(expect_field) and expect_field in result_fields

    return {
        "capability_id": capability_id,
        "typed_interface": typed,
        "verifier_strength": strength,
        "independence_markers": markers,
        "receipt_path": None if not receipt_path else str(receipt_path),
        "receipt_present": receipt_present,
        "expect_type": expect.get("type"),
        "runtime_predicate_is_self_reported": self_reported,
    }


def census(root: Path = ROOT, registry: Path = REGISTRY) -> dict[str, Any]:
    payload = json.loads(registry.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, Any]] = payload["capabilities"]

    records = [classify(cid, row, root) for cid, row in sorted(rows.items())]

    cells: dict[str, int] = {}
    for r in records:
        key = f"{'TYPED' if r['typed_interface'] else 'UNTYPED'}|{r['verifier_strength']}"
        cells[key] = cells.get(key, 0) + 1

    safe = [r for r in records if r["typed_interface"] and r["verifier_strength"] == RECEIPTED]
    dangerous = [r for r in records if r["typed_interface"] and r["verifier_strength"] == NONE]
    orphan_receipts = sorted(
        {r["receipt_path"] for r in records
         if r["receipt_path"] and not r["receipt_present"]}
    )

    summary = {
        "capabilities": len(records),
        "typed_interface": sum(1 for r in records if r["typed_interface"]),
        "declares_independence": sum(
            1 for r in records if r["verifier_strength"] in (RECEIPTED, DECLARED)
        ),
        "receipted": sum(1 for r in records if r["verifier_strength"] == RECEIPTED),
        "one_shot_safe": len(safe),
        "typed_but_unchecked": len(dangerous),
        "runtime_predicate_is_self_reported": sum(
            1 for r in records if r["runtime_predicate_is_self_reported"]
        ),
        "orphan_receipts": len(orphan_receipts),
        "receipt_without_declaration": sum(
            1 for r in records if r["receipt_present"] and not r["independence_markers"]
        ),
        "cells": dict(sorted(cells.items())),
    }
    return {
        "schema": "ONE_SHOT_REGIME_CENSUS_V1",
        "authority": "NONE",
        "source": str(registry.relative_to(root)),
        "summary": summary,
        "one_shot_safe_ids": [r["capability_id"] for r in safe],
        "typed_but_unchecked_ids": [r["capability_id"] for r in dangerous],
        "orphan_receipt_paths": orphan_receipts,
        "records": records,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--list-unchecked", action="store_true",
                        help="print the typed capabilities with no independent check")
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = census()
    s = result["summary"]

    print("one-shot regime census  --  authority NONE, structural, runs nothing\n")
    print(f"bound capabilities            {s['capabilities']}")
    print(f"typed interface               {s['typed_interface']}")
    print(f"declares independence         {s['declares_independence']}")
    print(f"  of which receipt on disk    {s['receipted']}")
    print(f"runtime predicate self-report {s['runtime_predicate_is_self_reported']}")
    print()
    print("              RECEIPTED   DECLARED      NONE")
    for kind in ("TYPED", "UNTYPED"):
        row = [s["cells"].get(f"{kind}|{tier}", 0) for tier in (RECEIPTED, DECLARED, NONE)]
        print(f"{kind:<10}{row[0]:>10}{row[1]:>11}{row[2]:>10}")
    print()
    print(f"one-shot safe (typed + receipted)      {s['one_shot_safe']}"
          f"  = {s['one_shot_safe'] / s['capabilities']:.0%} of the bound surface")
    print(f"typed but nothing checks it            {s['typed_but_unchecked']}"
          f"  = {s['typed_but_unchecked'] / s['capabilities']:.0%}")
    print(f"declared receipts not in the tree      {s['orphan_receipts']}")
    print(f"receipts with no attribution           {s['receipt_without_declaration']}")
    print("\nA declaration is not verification. DECLARED is not counted as safe.")

    if args.list_unchecked:
        print("\ntyped with no independent check:")
        for cid in result["typed_but_unchecked_ids"]:
            print(" ", cid)
        if result["orphan_receipt_paths"]:
            print("\ndedared receipt paths that do not exist:")
            for path in result["orphan_receipt_paths"]:
                print(" ", path)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("WROTE", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
