from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_ROOT_DECISION_GATE_V1"
ALLOWED_PROOF_KINDS = {
    "FULL_SCOPE_DB_COVER",
    "TARGET_ESCAPE_NONOCCUPANCY",
    "GENERATOR_CLOSURE_SCOPE_COMPLETE",
    "SELECTED_COVER_COMPLEMENT_UNSAT",
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

def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "x_decided": False,
        "x": None,
        "u_empty": False,
        "abc_closed": False,
        "d_finality_required": True,
        "terminal": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out

def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    receipt = payload.get("closure_receipt")
    if not isinstance(receipt, Mapping):
        return _fail("CLOSURE_RECEIPT_REQUIRED")

    kind = receipt.get("proof_kind")
    if kind not in ALLOWED_PROOF_KINDS:
        return _fail("PROOF_KIND_INVALID")
    if receipt.get("independent_verified") is not True:
        return _fail("INDEPENDENT_VERIFICATION_REQUIRED")
    if receipt.get("exact_byte_bound") is not True:
        return _fail("EXACT_BYTE_BINDING_REQUIRED")
    if receipt.get("conclusion") != "success":
        return _fail("SUCCESS_CONCLUSION_REQUIRED")
    if not _binding(receipt.get("proof_artifact")) or not _binding(receipt.get("verifier_receipt_artifact")):
        return _fail("CONTENT_ADDRESSED_PROOF_AND_VERIFIER_REQUIRED")

    scope_id = str(receipt.get("scope_id") or "").strip()
    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")

    if kind == "FULL_SCOPE_DB_COVER":
        if receipt.get("s_trace_subset_db") is not True:
            return _fail("FULL_SCOPE_DB_COVER_UNPROVED")
        rule = "S_TRACE_SUBSET_DB_IMPLIES_U_SUBSET_DB_IMPLIES_U_INTERSECTION_E_EMPTY"
    elif kind == "TARGET_ESCAPE_NONOCCUPANCY":
        if receipt.get("u_intersection_escape_empty") is not True:
            return _fail("TARGET_ESCAPE_NONOCCUPANCY_UNPROVED")
        rule = "DIRECT_TARGET_ESCAPE_NONOCCUPANCY"
    elif kind == "GENERATOR_CLOSURE_SCOPE_COMPLETE":
        required = (
            "generator_basis_complete",
            "all_generators_covered",
            "all_transforms_abc_preserving",
            "all_useful_contexts_reachable",
        )
        missing = [field for field in required if receipt.get(field) is not True]
        if missing:
            return _fail("GENERATOR_CLOSURE_PREMISES_UNPROVED", missing=missing)
        rule = "SCOPE_COMPLETE_GENERATOR_INDUCTION_COVERS_ALL_USEFUL_CONTEXTS"
    else:
        required = ("every_admission_sound", "residual_complement_unsat")
        missing = [field for field in required if receipt.get(field) is not True]
        if missing:
            return _fail("SELECTED_COVER_COMPLEMENT_PREMISES_UNPROVED", missing=missing)
        rule = "SOUND_ADMISSION_UNION_PLUS_UNSAT_COMPLEMENT_COVERS_SCOPE"

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__TERMINAL_ROOT_NOT_X_PROVED",
        "proof_kind": kind,
        "scope_id": scope_id,
        "proof_rule": rule,
        "x_decided": True,
        "x": False,
        "u_empty": True,
        "abc_closed": True,
        "d_finality_required": True,
        "terminal": False,
        "terminal_credit_delta": 0,
        "next": "FREEZE_EXACT_CREDITED_ROUTES__RECOMPUTE_D__DELETE_DONORS__RUN_INDEPENDENT_CLEAN_ROOM_REPLAY",
    }
