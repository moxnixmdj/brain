"""Scope-complete semantic-elision cover bridge.

Lift cell-level D_B admissions from the existing A/B/C semantic-elision
trichotomy to a whole declared scope. This module does not prove the cell
admissions itself; it requires content-addressed receipts for them and a
separate content-addressed proof that the declared partition exhausts the
load-bearing scope.

A = complete-objective global optimum
B = robust common policy over every still-possible completion
C = direct end-to-end acceptance of every load-bearing raw obligation
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SEMANTIC_ELISION_SCOPE_COVER_BRIDGE_V1"
ROUTES = {
    "A_COMPLETE_OBJECTIVE",
    "B_ROBUST_COMMON_POLICY",
    "C_DIRECT_END_TO_END_ACCEPTANCE",
}

def _sha1(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 40 and all(c in "0123456789abcdef" for c in v)

def _binding(v: Any) -> bool:
    return (
        isinstance(v, Mapping)
        and isinstance(v.get("path"), str)
        and bool(v["path"].strip())
        and _sha1(v.get("git_blob_sha"))
    )

def _receipts(v: Any) -> bool:
    return (
        isinstance(v, Sequence)
        and not isinstance(v, (str, bytes))
        and bool(v)
        and all(_binding(x) for x in v)
    )

def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "scope_cover_proved": False,
        "u_subtraction_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out

def evaluate(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_REQUIRED")

    scope_id = problem.get("scope_id")
    if not isinstance(scope_id, str) or not scope_id.strip():
        return _fail("SCOPE_ID_REQUIRED")

    if problem.get("scope_partition_complete") is not True:
        return _fail("SCOPE_PARTITION_COMPLETENESS_UNPROVED")
    if not _receipts(problem.get("scope_partition_proof_receipts")):
        return _fail("SCOPE_PARTITION_PROOF_RECEIPTS_INVALID")

    cells = problem.get("cells")
    if (
        not isinstance(cells, Sequence)
        or isinstance(cells, (str, bytes))
        or not cells
    ):
        return _fail("CELLS_REQUIRED")

    seen: set[str] = set()
    route_counts = {r: 0 for r in sorted(ROUTES)}
    normalized: list[dict[str, Any]] = []

    for i, row in enumerate(cells):
        if not isinstance(row, Mapping):
            return _fail(f"CELL_INVALID:{i}")
        cid = row.get("cell_id")
        if not isinstance(cid, str) or not cid or cid in seen:
            return _fail(f"CELL_ID_INVALID:{i}")
        seen.add(cid)

        if row.get("membership_proved") is not True:
            return _fail(f"CELL_MEMBERSHIP_UNPROVED:{cid}")

        route = row.get("db_admission_route")
        if route not in ROUTES:
            return _fail(f"CELL_ADMISSION_ROUTE_INVALID:{cid}")
        if row.get("db_admission_proved") is not True:
            return _fail(f"CELL_DB_ADMISSION_UNPROVED:{cid}")
        if not _receipts(row.get("db_admission_proof_receipts")):
            return _fail(f"CELL_DB_ADMISSION_PROOF_RECEIPTS_INVALID:{cid}")

        route_counts[route] += 1
        normalized.append({"cell_id": cid, "route": route})

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SCOPE_COMPLETE_UNION_OF_SEMANTIC_ELISION_DB_ADMISSIONS",
        "scope_id": scope_id,
        "scope_partition_complete": True,
        "cell_count": len(normalized),
        "route_counts": route_counts,
        "cells": sorted(normalized, key=lambda x: x["cell_id"]),
        "scope_cover_proved": True,
        "u_subtraction_authorized": True,
        "u_subtraction_scope": scope_id,
        "semantic_world_reconstruction_required": False,
        "single_universal_semantic_representation_required": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "THIS_LIFTS_ONLY_ALREADY_PROVED_CELL_LEVEL_D_B_ADMISSIONS_OVER_A_SEPARATELY_"
            "PROVED_SCOPE_COMPLETE_PARTITION__IT_DOES_NOT_PROVE_SCOPE_COMPLETENESS_OR_CELL_ADMISSION"
        ),
    }
