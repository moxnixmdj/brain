from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "v10": "canonical/governance/DB_EXISTING_EVIDENCE_SATURATION_UNION_20261007_V10.json",
    "v9": "canonical/governance/DB_EXISTING_EVIDENCE_SATURATION_UNION_20261007_V9.json",
    "if_repair": "canonical/governance/IF_SCOPE_FINITE_PROTOCOL_BINDING_TRUTH_REPAIR_20261007_V1.json",
    "if_verify": "canonical/verification/IF_SCOPE_FINITE_PROTOCOL_BINDING_CONNECTOR_VERIFICATION_20261007_V1.json",
    "l1": "canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json",
}

EXPECTED = {
    "v9": "73fbe58346dd2ff94feccfa0cbea7d00a9dcd1d0",
    "if_repair": "15c5e607e9f5c921d62bf75492e26021980e75fa",
    "if_verify": "b7bfc865267554f0c7005c0835f09107b2dec998",
    "l1": "cff6a95cad0027f3e142a32fd028a27566a00ea5",
}

PREDICATE = "IF_SCOPE_BOUNDARY_NONINFERIOR"
RECORD = "IF_SCOPE_BOUNDARY_FROZEN_160_FINITE_MANIFEST"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(key: str) -> dict:
    value = json.loads((ROOT / FILES[key]).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OBJECT_REQUIRED:" + key)
    return value


def verify() -> dict:
    errors: list[str] = []
    for key, expected in EXPECTED.items():
        path = ROOT / FILES[key]
        if not path.is_file():
            errors.append("MISSING:" + key)
        elif blob_sha(path) != expected:
            errors.append("DRIFT:" + key)

    if errors:
        return {"pass": False, "errors": errors, "terminal": False}

    v10 = load("v10")
    v9 = load("v9")
    repair = load("if_repair")
    iv = load("if_verify")
    l1 = load("l1")

    if v10.get("schema") != "PROJECT_BRAIN_DB_EXISTING_EVIDENCE_SATURATION_UNION_V10":
        errors.append("V10_SCHEMA")

    if v9.get("saturation_result", {}).get("known_sound_D_B_certificate_record_count") != 16:
        errors.append("V9_COUNT")
    if v9.get("added_certificate", {}).get("id") != RECORD:
        errors.append("V9_IF_RECORD")
    if v9.get("added_certificate", {}).get("brain_result") != "160_OF_160":
        errors.append("V9_IF_RESULT")

    pb = repair.get("protocol_binding", {})
    bp = repair.get("bound_portfolio", {})
    tr = repair.get("truth_repair", {})
    if pb.get("predicate") != PREDICATE:
        errors.append("REPAIR_PREDICATE")
    if pb.get("interpretation") != "FINITE_DECLARED_SCOPE":
        errors.append("REPAIR_SCOPE_MODE")
    if pb.get("underlying_population_declared") is not False:
        errors.append("REPAIR_POPULATION")
    if bp.get("case_count") != 160 or bp.get("brain_success_count") != 160 or bp.get("brain_failure_count") != 0:
        errors.append("REPAIR_RESULT")
    if bp.get("required_dimension_coverage_complete") is not True:
        errors.append("REPAIR_DIMENSION_COVERAGE")
    if tr.get("if_scope_boundary_refinement_closed_if_verified") is not True:
        errors.append("REPAIR_CLOSURE")
    if tr.get("sound_subtraction_from_U_if_verified") is not True:
        errors.append("REPAIR_U_SUBTRACTION")

    verified = iv.get("verified", {})
    if not str(iv.get("status", "")).startswith("INDEPENDENT_EXACT_SOURCE_BINDING_AND_VERIFIER_REPLAY_PASS"):
        errors.append("INDEPENDENT_STATUS")
    required_true = (
        "all_source_blob_bindings_exact",
        "precommit_dimension_atom_set_exact",
        "result_blind_freeze_controls_all_true",
        "independent_execution_pass",
        "if_scope_boundary_refinement_closed",
        "sound_subtraction_from_U",
    )
    for key in required_true:
        if verified.get(key) is not True:
            errors.append("INDEPENDENT_" + key.upper())
    if verified.get("protocol_declares_larger_underlying_population") is not False:
        errors.append("INDEPENDENT_POPULATION")
    if verified.get("brain_success_count") != 160 or verified.get("brain_failure_count") != 0:
        errors.append("INDEPENDENT_RESULT")
    if verified.get("binary_success_top_value") != 1:
        errors.append("INDEPENDENT_TOP")
    if verified.get("opus_query_required") is not False:
        errors.append("INDEPENDENT_OPUS_QUERY")

    structural = set(l1.get("current_19_refinements", {}).get("structural_abc_refinements", []))
    if PREDICATE not in structural:
        errors.append("L1_REFINEMENT_MISSING")

    sat = v10.get("saturation_result", {})
    if sat.get("known_sound_D_B_certificate_record_count") != 16:
        errors.append("V10_COUNT")
    if sat.get("added_sound_certificate_record_count") != 0:
        errors.append("V10_ADDED_COUNT")
    if sat.get("record_count_changed") is not False:
        errors.append("V10_RECORD_COUNT_CHANGE")
    if sat.get("closed_refinement") != PREDICATE:
        errors.append("V10_CLOSED_REFINEMENT")
    if sat.get("sound_subtraction_from_U") is not True:
        errors.append("V10_U_SUBTRACTION")
    if sat.get("U_empty_proved") is not False:
        errors.append("V10_U_EMPTY_OVERCLAIM")
    if v10.get("proof", {}).get("objective_binary_success_ceiling") != 1:
        errors.append("V10_TOP")
    if v10.get("proof", {}).get("comparator_residual_case_count") != 0:
        errors.append("V10_COMPARATOR_RESIDUAL")

    required_nonclaims = {
        "NO_CLAIM_U_IS_EMPTY.",
        "NO_CLAIM_COMPLETE_SELECTED_CONTEXT_ABC_IS_CLOSED.",
        "NO_CLAIM_D_FINALITY_OR_TERMINAL_IS_CLOSED.",
    }
    if not required_nonclaims.issubset(set(v10.get("hard_nonclaims", []))):
        errors.append("NONCLAIM_GUARD")

    return {
        "pass": not errors,
        "errors": errors,
        "sound_record_count": 16 if not errors else None,
        "record_count_delta": 0 if not errors else None,
        "closed_refinement": PREDICATE if not errors else None,
        "sound_subtraction_from_U": True if not errors else None,
        "opus_query_required": False if not errors else None,
        "U_empty_proved": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)
