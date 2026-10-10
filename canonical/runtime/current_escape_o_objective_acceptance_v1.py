"""Current Escape O objective-acceptance theorem projection.

This module binds the current Escape O frontier to the already-proved frozen
scope-lift normal form. It proves only that the shared implication applies to
the current O obligation universe. It does not close any O row and accepts no
caller assertion that a row's scope-complete Brain proof exists.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_O_OBJECTIVE_ACCEPTANCE_V1"
ROOT = Path(__file__).resolve().parents[2]
FROZEN_O_PATH = ROOT / "canonical/governance/FROZEN_O_OBJECTIVE_ACCEPTANCE_SCOPE_LIFT_NORMAL_FORM_20261007_V1.json"
CURRENT_OQ_PATH = ROOT / "canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json"
CURRENT_MANIFEST_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
FROZEN_O_EXPECTED_GIT_BLOB_SHA = "2ce4b7fdcb5556072b936f04887ac6a05e92dce3"


def _git_blob_sha_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "shared_o_acceptance_law_bound": False,
        "all_current_o_rows_closed": False,
        "row_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    if detail:
        out.update(detail)
    return out


def evaluate(
    manifest: Mapping[str, Any],
    oq: Mapping[str, Any],
    frozen_o: Mapping[str, Any],
) -> dict[str, Any]:
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        return _fail("CURRENT_MANIFEST_ROWS_NOT_LIST")

    row_ids: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            return _fail("CURRENT_MANIFEST_ROW_INVALID")
        oid = row.get("obligation_id")
        if not isinstance(oid, str) or not oid.strip():
            return _fail("CURRENT_MANIFEST_OBLIGATION_ID_INVALID")
        row_ids.append(oid.strip())
    if len(row_ids) != len(set(row_ids)):
        return _fail("CURRENT_MANIFEST_DUPLICATE_OBLIGATION_ID")

    reduction = oq.get("reduction")
    if not isinstance(reduction, Mapping):
        return _fail("CURRENT_OQ_REDUCTION_MISSING")
    q_rows_raw = reduction.get("Q_rows")
    if not isinstance(q_rows_raw, list) or not all(isinstance(x, str) and x.strip() for x in q_rows_raw):
        return _fail("CURRENT_OQ_Q_ROWS_INVALID")
    q_rows = [x.strip() for x in q_rows_raw]
    if len(q_rows) != len(set(q_rows)):
        return _fail("CURRENT_OQ_DUPLICATE_Q_ROW")
    unknown_q = sorted(set(q_rows) - set(row_ids))
    if unknown_q:
        return _fail("CURRENT_OQ_Q_ROW_OUTSIDE_MANIFEST", unknown_q_rows=unknown_q)

    o_rows = [x for x in row_ids if x not in set(q_rows)]
    if reduction.get("current_frontier_row_count") != len(row_ids):
        return _fail("CURRENT_OQ_FRONTIER_COUNT_MISMATCH")
    if reduction.get("O_OBJECTIVE_ACCEPTANCE") != len(o_rows):
        return _fail("CURRENT_OQ_O_COUNT_MISMATCH")
    if reduction.get("Q_QUALITATIVE_RELATIVE_ORDER") != len(q_rows):
        return _fail("CURRENT_OQ_Q_COUNT_MISMATCH")
    if reduction.get("mixed") != 0 or reduction.get("unclassified") != 0:
        return _fail("CURRENT_OQ_NOT_EXHAUSTIVELY_O_Q_CLASSIFIED")

    frozen_rows = frozen_o.get("current_O_obligations")
    theorem = frozen_o.get("theorem")
    proof_schema = frozen_o.get("proof_schema")
    if not isinstance(frozen_rows, list) or not all(isinstance(x, str) and x.strip() for x in frozen_rows):
        return _fail("FROZEN_O_OBLIGATION_UNIVERSE_INVALID")
    if not isinstance(theorem, Mapping) or not isinstance(theorem.get("statement"), str):
        return _fail("FROZEN_O_THEOREM_INVALID")
    if not isinstance(proof_schema, Mapping):
        return _fail("FROZEN_O_PROOF_SCHEMA_INVALID")
    required = proof_schema.get("common_required")
    if not isinstance(required, list) or not required:
        return _fail("FROZEN_O_COMMON_PROOF_REQUIREMENTS_INVALID")

    missing = sorted(set(o_rows) - set(frozen_rows))
    if missing:
        return _fail(
            "CURRENT_O_ROW_OUTSIDE_FROZEN_O_THEOREM_UNIVERSE",
            current_o_count=len(o_rows),
            current_q_count=len(q_rows),
            current_o_rows=o_rows,
            missing_from_frozen_o_theorem=missing,
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CURRENT_O_FRONTIER_IS_SUBSET_OF_PROVED_SCOPE_LIFT_THEOREM__ZERO_ROW_CREDIT",
        "shared_o_acceptance_law_bound": True,
        "current_frontier_count": len(row_ids),
        "current_o_count": len(o_rows),
        "current_q_count": len(q_rows),
        "current_o_rows": o_rows,
        "current_q_rows": q_rows,
        "missing_from_frozen_o_theorem": [],
        "scope_lift_theorem_statement": theorem["statement"],
        "scope_lift_common_required": list(required),
        "accepted_scope_completeness_bases": list(proof_schema.get("accepted_scope_completeness_bases", [])),
        "open_o_rows": o_rows,
        "all_current_o_rows_closed": False,
        "row_proof_authority": False,
        "caller_asserted_row_closure_authority": False,
        "next_required_edge": "INSTANTIATE_THE_BOUND_SHARED_O_LAW_WITH_REAL_CONTENT_ADDRESSED_SCOPE_COMPLETE_BRAIN_PROOFS_FOR_CURRENT_O_ROWS__PREFER_ONE_PROOF_COVERING_MULTIPLE_ROWS",
        "row_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def evaluate_current() -> dict[str, Any]:
    try:
        frozen_raw = FROZEN_O_PATH.read_bytes()
        frozen_sha = _git_blob_sha_bytes(frozen_raw)
        if frozen_sha != FROZEN_O_EXPECTED_GIT_BLOB_SHA:
            return _fail(
                "FROZEN_O_THEOREM_BLOB_DRIFT",
                expected_git_blob_sha=FROZEN_O_EXPECTED_GIT_BLOB_SHA,
                actual_git_blob_sha=frozen_sha,
            )
        frozen = json.loads(frozen_raw.decode("utf-8"))
        manifest = _load(CURRENT_MANIFEST_PATH)
        oq = _load(CURRENT_OQ_PATH)
    except Exception as exc:
        return _fail("CURRENT_O_PROJECTION_SOURCE_LOAD_FAILED", detail=str(exc))
    return evaluate(manifest, oq, frozen)
