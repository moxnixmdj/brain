"""Fail-closed state-conditioned relational refinement compiler.

This compiler materializes the proof obligations required by the already-verified
finite-trace forward-simulation theorem. It does not infer semantic refinement
from benchmark parity, scores, or naked booleans.

A row closes only when every load-bearing state-conditioned proof object is
content-addressed. Whole-trace readiness additionally requires global receipts
for trace-scope binding, initialization, constructor preservation, terminal
preservation, and acceptance-order soundness.

No acceptance, capability, family, ownership, or terminal credit is granted.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_RELATIONAL_REFINEMENT_COMPILER_V1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

EVALUATOR_MODES = {
    "EXPLICIT",
    "RESTRICTED_HIDDEN",
    "UNRESTRICTED_HIDDEN",
}

LOCAL_REFINEMENT_PROOF_KINDS = {
    "FORMAL_REFINEMENT",
    "EXHAUSTIVE_FINITE_REFINEMENT",
    "CONTENT_ADDRESSED_CONTRACT_REFINEMENT",
    "OBJECTIVE_CEILING_REFINEMENT",
    "OBSERVATIONAL_EQUIVALENCE_REFINEMENT",
}

FORBIDDEN_LOCAL_PROOF_KINDS = {
    "BENCHMARK_SCORE",
    "MATCHED_SCORE",
    "AGGREGATE_PARITY",
    "POINT_ESTIMATE",
    "ASSERTION_ONLY",
}

GLOBAL_RECEIPTS = (
    "trace_scope_receipt",
    "initialization_receipt",
    "constructor_preservation_receipt",
    "terminal_preservation_receipt",
    "acceptance_order_soundness_receipt",
)

ROW_RECEIPTS = (
    "relation_soundness_receipt",
    "local_refinement_receipt",
    "scope_authority_receipt",
    "state_carry_receipt",
    "ownership_receipt",
)


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "whole_trace_candidate_ready": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _receipt_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    path = value.get("path")
    sha = value.get("git_blob_sha")
    return (
        isinstance(path, str)
        and path.startswith("canonical/")
        and isinstance(sha, str)
        and SHA40.fullmatch(sha) is not None
    )


def _missing_receipt(prefix: str, field: str) -> str:
    return f"{prefix}:{field}:MISSING_OR_INVALID_CONTENT_ADDRESS"


def _validate_evaluator_binding(row_id: str, binding: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(binding, Mapping):
        return [f"{row_id}:evaluator_binding:INVALID"]

    mode = binding.get("mode")
    if mode not in EVALUATOR_MODES:
        errors.append(f"{row_id}:evaluator_binding:MODE_INVALID")
        return errors

    if mode == "EXPLICIT":
        if not _receipt_valid(binding.get("evaluator_receipt")):
            errors.append(_missing_receipt(row_id, "evaluator_receipt"))
    elif mode == "RESTRICTED_HIDDEN":
        if not _receipt_valid(binding.get("utility_class_receipt")):
            errors.append(_missing_receipt(row_id, "utility_class_receipt"))
        if not _receipt_valid(binding.get("material_order_receipt")):
            errors.append(_missing_receipt(row_id, "material_order_receipt"))
    elif mode == "UNRESTRICTED_HIDDEN":
        receipt = binding.get("equivalence_receipt")
        if not _receipt_valid(receipt):
            errors.append(_missing_receipt(row_id, "equivalence_receipt"))
        elif receipt.get("proof_kind") != "OBSERVATIONAL_EQUIVALENCE":
            errors.append(f"{row_id}:equivalence_receipt:PROOF_KIND_INVALID")

    return errors


def compile_relational_refinement(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    if doc.get("schema") != SCHEMA:
        return _fail("SCHEMA_INVALID")
    if not _nonempty(doc.get("target_claim")):
        return _fail("TARGET_CLAIM_INVALID")
    if not _nonempty(doc.get("relation_id")):
        return _fail("RELATION_ID_INVALID")

    rows = doc.get("rows")
    if not isinstance(rows, list) or not rows:
        return _fail("ROWS_INVALID_OR_EMPTY")

    errors: list[str] = []
    global_missing: list[str] = []
    for field in GLOBAL_RECEIPTS:
        if not _receipt_valid(doc.get(field)):
            global_missing.append(field)

    seen: set[str] = set()
    row_outputs: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"ROW_{idx}:INVALID")
            continue

        row_id = row.get("id")
        if not _nonempty(row_id):
            errors.append(f"ROW_{idx}:ID_INVALID")
            continue
        row_id = row_id.strip()
        if row_id in seen:
            errors.append(f"{row_id}:DUPLICATE_ID")
            continue
        seen.add(row_id)

        for field in (
            "precondition_spec",
            "target_transition_class",
            "brain_macrostep_contract",
            "postcondition_spec",
        ):
            if not _nonempty(row.get(field)):
                errors.append(f"{row_id}:{field}:INVALID")

        missing: list[str] = []
        for field in ROW_RECEIPTS:
            receipt = row.get(field)
            if not _receipt_valid(receipt):
                missing.append(field)

        local_receipt = row.get("local_refinement_receipt")
        if _receipt_valid(local_receipt):
            kind = local_receipt.get("proof_kind")
            if kind in FORBIDDEN_LOCAL_PROOF_KINDS:
                errors.append(f"{row_id}:LOCAL_REFINEMENT_FORBIDDEN_PROOF_KIND:{kind}")
            elif kind not in LOCAL_REFINEMENT_PROOF_KINDS:
                errors.append(f"{row_id}:LOCAL_REFINEMENT_PROOF_KIND_INVALID")

        evaluator_errors = _validate_evaluator_binding(
            row_id, row.get("evaluator_binding")
        )
        errors.extend(evaluator_errors)

        complete = not missing and not evaluator_errors
        if _receipt_valid(local_receipt):
            kind = local_receipt.get("proof_kind")
            complete = complete and kind in LOCAL_REFINEMENT_PROOF_KINDS
        else:
            complete = False

        row_outputs.append(
            {
                "id": row_id,
                "complete": complete,
                "missing_receipts": sorted(missing),
                "evaluator_mode": (
                    row.get("evaluator_binding", {}).get("mode")
                    if isinstance(row.get("evaluator_binding"), Mapping)
                    else None
                ),
            }
        )

    if errors:
        return {
            **_fail(*errors),
            "global_missing_receipts": sorted(global_missing),
            "rows": row_outputs,
        }

    open_rows = [r["id"] for r in row_outputs if not r["complete"]]
    whole_trace_candidate_ready = not global_missing and not open_rows

    return {
        "schema": SCHEMA,
        "status": (
            "RELATIONAL_REFINEMENT_PREMISES_COMPLETE__CANDIDATE_FOR_SEPARATE_INDUCTION_PROMOTION"
            if whole_trace_candidate_ready
            else "RELATIONAL_REFINEMENT_RESIDUALS_COMPILED"
        ),
        "errors": [],
        "relation_id": doc["relation_id"],
        "target_claim": doc["target_claim"],
        "row_count": len(row_outputs),
        "closed_row_count": len(row_outputs) - len(open_rows),
        "open_row_count": len(open_rows),
        "open_rows": open_rows,
        "global_missing_receipts": sorted(global_missing),
        "rows": row_outputs,
        "whole_trace_candidate_ready": whole_trace_candidate_ready,
        "rule": (
            "BENCHMARK_OR_MATCHED_SCORE_PARITY_IS_NOT_LOCAL_REFINEMENT__"
            "EVERY_LOCAL_ROW_REQUIRES_CONTENT_ADDRESSED_STATE_CONDITIONED_PROOF__"
            "UNKNOWN_OR_MISSING_PREMISES_REMAIN_OPEN__"
            "WHOLE_TRACE_READINESS_REQUIRES_GLOBAL_SCOPE_INITIALIZATION_CONSTRUCTOR_TERMINAL_AND_ACCEPTANCE_ORDER_RECEIPTS"
        ),
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
