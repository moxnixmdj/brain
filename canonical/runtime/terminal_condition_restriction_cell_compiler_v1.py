"""Fail-closed compiler for condition-restriction proof reuse.

A condition x family cell closes only when a content-addressed proof:
1) targets the exact family,
2) is independently/objectively supported and scope-complete,
3) uses an admissible transfer class, and
4) explicitly contains the condition in its covered scope.

Aggregate-only proofs, implicit family mappings, and missing scope metadata never close a cell.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

ALLOWED_PROOF_CLASSES = {
    "POINTWISE_UNIVERSAL",
    "OBJECTIVE_CEILING",
    "EXHAUSTIVE_FINITE_PER_CASE",
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class ConditionRestrictionError(RuntimeError):
    pass


def _valid_receipt(p: dict[str, Any]) -> bool:
    return (
        p.get("independent_or_objective") is True
        and p.get("scope_complete") is True
        and p.get("proof_class") in ALLOWED_PROOF_CLASSES
        and isinstance(p.get("source_path"), str)
        and bool(p["source_path"])
        and isinstance(p.get("source_sha"), str)
        and bool(SHA40.fullmatch(p["source_sha"]))
        and isinstance(p.get("family"), str)
        and bool(p["family"])
        and isinstance(p.get("covered_conditions"), list)
    )


def _proof_closes_cell(proof: dict[str, Any], family: str, condition: str) -> bool:
    if not _valid_receipt(proof):
        return False
    if proof["family"] != family:
        return False
    return condition in set(map(str, proof["covered_conditions"]))


def compile_condition_cells(
    matrix: dict[str, Any],
    proofs: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    rows = matrix.get("shared_condition_matrix")
    if not isinstance(rows, list):
        raise ConditionRestrictionError("MISSING_SHARED_CONDITION_MATRIX")

    proofs = list(proofs)
    cells: list[dict[str, Any]] = []
    for row in rows:
        condition = row.get("condition")
        families = row.get("mapped_family_union")
        if not isinstance(condition, str) or not condition:
            raise ConditionRestrictionError("INVALID_CONDITION")
        if not isinstance(families, list) or not all(isinstance(x, str) and x for x in families):
            raise ConditionRestrictionError(f"INVALID_FAMILY_UNION:{condition}")

        for family in families:
            matches = [
                p for p in proofs
                if _proof_closes_cell(p, family=family, condition=condition)
            ]
            matches.sort(key=lambda p: (p["source_path"], p["source_sha"], str(p.get("proof_id", ""))))
            if matches:
                p = matches[0]
                cells.append({
                    "condition": condition,
                    "family": family,
                    "state": "CLOSED_BY_SOUND_RESTRICTION_TRANSFER",
                    "proof_id": p.get("proof_id"),
                    "proof_class": p["proof_class"],
                    "source_path": p["source_path"],
                    "source_sha": p["source_sha"],
                })
            else:
                cells.append({
                    "condition": condition,
                    "family": family,
                    "state": "OPEN__NO_EXPLICIT_SCOPE_SAFE_TRANSFER_RECEIPT",
                })

    closed = sum(c["state"].startswith("CLOSED") for c in cells)
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CONDITION_CELL_COMPILATION_V1",
        "status": "PASS__FAIL_CLOSED_CONDITION_RESTRICTION_COMPILATION",
        "total_cells": len(cells),
        "closed_cells": closed,
        "open_cells": len(cells) - closed,
        "cells": cells,
        "rules": [
            "FAMILY_NAME_MATCH_ALONE_NEVER_CLOSES_A_CELL",
            "AGGREGATE_NONINFERIORITY_NEVER_TRANSFERS_WITHOUT_A_CONDITION_BOUND",
            "MISSING_SCOPE_METADATA_FAILS_OPEN",
            "ONLY_POINTWISE_UNIVERSAL_OBJECTIVE_CEILING_OR_EXHAUSTIVE_PER_CASE_CLASSES_ARE_ADMISSIBLE",
            "EVERY_CLOSING_RECEIPT_MUST_BE_CONTENT_ADDRESSED",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--proofs", required=True)
    ap.add_argument("--output")
    ns = ap.parse_args()

    try:
        matrix = json.loads(Path(ns.matrix).read_text(encoding="utf-8"))
        proof_doc = json.loads(Path(ns.proofs).read_text(encoding="utf-8"))
        proofs = proof_doc.get("proofs", proof_doc) if isinstance(proof_doc, dict) else proof_doc
        if not isinstance(proofs, list):
            raise ConditionRestrictionError("PROOFS_MUST_BE_LIST")
        result = compile_condition_cells(matrix, proofs)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if ns.output:
            Path(ns.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, ConditionRestrictionError) as exc:
        print(json.dumps({
            "schema": "PROJECT_BRAIN_TERMINAL_CONDITION_CELL_COMPILATION_V1",
            "status": "FAIL_CLOSED__COMPILER_ERROR",
            "error": str(exc),
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }, indent=2, sort_keys=True))
        return 43


if __name__ == "__main__":
    raise SystemExit(main())
