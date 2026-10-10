"""Current escape-frontier acceptance-regime reducer.

This module is deliberately narrow. It projects the exact current 13-row
escape-progress manifest through the already frozen O/Q acceptance-regime
classification and proves only that every current row is classified as either
objective acceptance O or qualitative relative-order acceptance Q.

It grants no acceptance, capability, ownership, escape-totality, U-empty, or
terminal credit. Its purpose is scheduler compression: replace thirteen benchmark
labels as primary research units with two shared acceptance-law proof objects.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
CLASSIFICATION = ROOT / "canonical/governance/FROZEN_18_ACCEPTANCE_REGIME_EXHAUSTIVE_CLASSIFICATION_20261007_V1.json"

SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_V1"
O = "O_OBJECTIVE_ACCEPTANCE"
Q = "Q_QUALITATIVE_RELATIVE_ORDER"
ALLOWED = {O, Q}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "current_frontier_scope_complete": False,
        "acceptance_closed": False,
        "escape_progress_totality_proved": False,
        "u_empty": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def reduce_frontier(
    manifest: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return _fail("MANIFEST_NOT_OBJECT")
    if not isinstance(classification, Mapping):
        return _fail("CLASSIFICATION_NOT_OBJECT")

    rows = manifest.get("rows")
    classified = classification.get("exhaustive_rows")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not rows
    ):
        return _fail("MANIFEST_ROWS_INVALID")
    if (
        not isinstance(classified, Sequence)
        or isinstance(classified, (str, bytes))
        or not classified
    ):
        return _fail("CLASSIFICATION_ROWS_INVALID")

    current_ids: list[str] = []
    route_group_by_id: dict[str, str] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return _fail("MANIFEST_ROW_NOT_OBJECT", index=index)
        oid = row.get("obligation_id")
        group = row.get("route_group")
        if not isinstance(oid, str) or not oid or oid in current_ids:
            return _fail("MANIFEST_OBLIGATION_ID_INVALID_OR_DUPLICATE", index=index)
        if not isinstance(group, str) or not group:
            return _fail("MANIFEST_ROUTE_GROUP_INVALID", obligation_id=oid)
        current_ids.append(oid)
        route_group_by_id[oid] = group

    regime_by_id: dict[str, str] = {}
    basis_by_id: dict[str, str] = {}
    duplicates: list[str] = []
    for index, row in enumerate(classified):
        if not isinstance(row, Mapping):
            return _fail("CLASSIFICATION_ROW_NOT_OBJECT", index=index)
        oid = row.get("obligation")
        regime = row.get("regime")
        if not isinstance(oid, str) or not oid:
            return _fail("CLASSIFICATION_OBLIGATION_ID_INVALID", index=index)
        if oid in regime_by_id:
            duplicates.append(oid)
            continue
        if regime not in ALLOWED:
            return _fail("CLASSIFICATION_REGIME_INVALID", obligation_id=oid, regime=regime)
        basis = row.get("basis")
        if not isinstance(basis, str) or not basis:
            return _fail("CLASSIFICATION_BASIS_INVALID", obligation_id=oid)
        regime_by_id[oid] = regime
        basis_by_id[oid] = basis

    if duplicates:
        return _fail("CLASSIFICATION_DUPLICATE_OBLIGATIONS", duplicates=sorted(duplicates))

    missing = sorted(set(current_ids) - set(regime_by_id))
    if missing:
        return _fail("CURRENT_FRONTIER_UNCLASSIFIED", missing_obligation_ids=missing)

    projected = [
        {
            "obligation_id": oid,
            "route_group": route_group_by_id[oid],
            "regime": regime_by_id[oid],
            "classification_basis": basis_by_id[oid],
        }
        for oid in current_ids
    ]
    o_ids = sorted(row["obligation_id"] for row in projected if row["regime"] == O)
    q_ids = sorted(row["obligation_id"] for row in projected if row["regime"] == Q)

    if len(projected) != 13:
        return _fail("CURRENT_FRONTIER_ROW_COUNT_NOT_13", row_count=len(projected))
    if len(o_ids) != 11 or len(q_ids) != 2:
        return _fail(
            "CURRENT_FRONTIER_OQ_COUNT_DRIFT",
            objective_count=len(o_ids),
            qualitative_count=len(q_ids),
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CURRENT_13_ESCAPE_FRONTIER_EXHAUSTIVELY_REDUCED_TO_O11_Q2",
        "current_frontier_scope_complete": True,
        "current_frontier_row_count": len(projected),
        "objective_acceptance_count": len(o_ids),
        "qualitative_relative_order_count": len(q_ids),
        "mixed_count": 0,
        "unclassified_count": 0,
        "objective_obligation_ids": o_ids,
        "qualitative_obligation_ids": q_ids,
        "rows": projected,
        "shared_primary_proof_objects": {
            O: (
                "ONE_SCOPE_COMPLETE_BRAIN_SIDE_OBJECTIVE_ACCEPTANCE_PROOF_LAW_"
                "SUFFICIENT_FOR_EACH_CURRENT_O_ROW_WITH_ROW_SPECIFIC_SCOPE_BINDING"
            ),
            Q: (
                "ONE_SHARED_AUTHENTICATED_PROFESSIONAL_QUALITY_ORDER_OR_ROBUST_"
                "DOMINANCE_LAW_COVERING_GDPVAL_AND_AA_BRIEFCASE"
            ),
        },
        "scheduler_rule": (
            "DO_NOT_TREAT_THE_THIRTEEN_BENCHMARK_LABELS_AS_THIRTEEN_PRIMARY_"
            "ACCEPTANCE_RESEARCH_PROGRAMS__ATTACK_O_AND_Q_SHARED_PROOF_LAWS__"
            "PRESERVE_ROW_SPECIFIC_SCOPE_BINDINGS_AS_FALSIFIERS"
        ),
        "acceptance_closed": False,
        "escape_progress_totality_proved": False,
        "u_empty": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def reduce_repo(root: Path = ROOT) -> dict[str, Any]:
    manifest = json.loads((root / MANIFEST.relative_to(ROOT)).read_text(encoding="utf-8"))
    classification = json.loads((root / CLASSIFICATION.relative_to(ROOT)).read_text(encoding="utf-8"))
    return reduce_frontier(manifest, classification)


if __name__ == "__main__":
    print(json.dumps(reduce_repo(), indent=2, sort_keys=True))
