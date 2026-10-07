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

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_RELATIONAL_REFINEMENT_COMPILER_V1"
ROW_BINDING_SCHEMA = "PROJECT_BRAIN_RELATIONAL_REFINEMENT_CONTRACT_BINDING_V1"
GLOBAL_BINDING_SCHEMA = "PROJECT_BRAIN_RELATIONAL_REFINEMENT_GLOBAL_BINDING_V1"
ROOT = Path(__file__).resolve().parents[2]
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


def _git_blob_sha(path: str) -> str | None:
    if not isinstance(path, str) or not path.startswith("canonical/"):
        return None
    candidate = ROOT / path
    try:
        raw = candidate.read_bytes()
    except (OSError, ValueError):
        return None
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _receipt_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    path = value.get("path")
    sha = value.get("git_blob_sha")
    if (
        not isinstance(path, str)
        or not path.startswith("canonical/")
        or not isinstance(sha, str)
        or SHA40.fullmatch(sha) is None
    ):
        return False
    return _git_blob_sha(path) == sha


def _missing_receipt(prefix: str, field: str) -> str:
    return f"{prefix}:{field}:MISSING_OR_INVALID_CONTENT_ADDRESS"


def _receipt_ref(value: Any) -> dict[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    path = value.get("path")
    sha = value.get("git_blob_sha")
    if not isinstance(path, str) or not isinstance(sha, str):
        return None
    return {"path": path, "git_blob_sha": sha}


def _load_json_receipt(value: Any) -> dict[str, Any] | None:
    if not _receipt_valid(value):
        return None
    try:
        obj = json.loads((ROOT / value["path"]).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _validate_row_binding(
    relation_id: str, row_id: str, row: Mapping[str, Any]
) -> list[str]:
    obj = _load_json_receipt(row.get("contract_binding_receipt"))
    if obj is None:
        return [f"{row_id}:contract_binding_receipt:MISSING_INVALID_OR_UNREADABLE"]
    errors: list[str] = []
    if obj.get("schema") != ROW_BINDING_SCHEMA:
        errors.append(f"{row_id}:contract_binding_receipt:SCHEMA_INVALID")
    expected = {
        "row_id": row_id,
        "relation_id": relation_id,
        "precondition_spec": row.get("precondition_spec"),
        "target_transition_class": row.get("target_transition_class"),
        "brain_macrostep_contract": row.get("brain_macrostep_contract"),
        "postcondition_spec": row.get("postcondition_spec"),
        "evaluator_binding": row.get("evaluator_binding"),
    }
    for key, value in expected.items():
        if obj.get(key) != value:
            errors.append(f"{row_id}:contract_binding_receipt:MISMATCH:{key}")
    evidence = obj.get("evidence_receipts")
    if not isinstance(evidence, Mapping):
        errors.append(f"{row_id}:contract_binding_receipt:EVIDENCE_RECEIPTS_INVALID")
    else:
        for field in ROW_RECEIPTS:
            if _receipt_ref(evidence.get(field)) != _receipt_ref(row.get(field)):
                errors.append(
                    f"{row_id}:contract_binding_receipt:EVIDENCE_MISMATCH:{field}"
                )
    return errors


def _validate_global_binding(doc: Mapping[str, Any]) -> list[str]:
    obj = _load_json_receipt(doc.get("global_contract_binding_receipt"))
    if obj is None:
        return ["GLOBAL_CONTRACT_BINDING_MISSING_INVALID_OR_UNREADABLE"]
    errors: list[str] = []
    if obj.get("schema") != GLOBAL_BINDING_SCHEMA:
        errors.append("GLOBAL_CONTRACT_BINDING_SCHEMA_INVALID")
    if obj.get("target_claim") != doc.get("target_claim"):
        errors.append("GLOBAL_CONTRACT_BINDING_TARGET_CLAIM_MISMATCH")
    if obj.get("relation_id") != doc.get("relation_id"):
        errors.append("GLOBAL_CONTRACT_BINDING_RELATION_ID_MISMATCH")
    evidence = obj.get("global_receipts")
    if not isinstance(evidence, Mapping):
        errors.append("GLOBAL_CONTRACT_BINDING_RECEIPTS_INVALID")
    else:
        for field in GLOBAL_RECEIPTS:
            if _receipt_ref(evidence.get(field)) != _receipt_ref(doc.get(field)):
                errors.append(f"GLOBAL_CONTRACT_BINDING_RECEIPT_MISMATCH:{field}")
    return errors


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
    errors.extend(_validate_global_binding(doc))

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
        binding_errors = _validate_row_binding(
            str(doc["relation_id"]), row_id, row
        )
        errors.extend(binding_errors)

        complete = not missing and not evaluator_errors and not binding_errors
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
