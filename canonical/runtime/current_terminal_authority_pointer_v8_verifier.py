from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

EXPECTED = {
    "canonical/governance/DB_EXISTING_EVIDENCE_SATURATION_UNION_20261007_V10.json":
        "09c5c3c8ca4675f28585930ae74c04c8a34d3904",
    "canonical/verification/DB_EXISTING_EVIDENCE_SATURATION_UNION_WOLFRAM_VERIFY_20261007_V10.json":
        "ed673c2094babdb490d1509bf0a90c8a81a7daf0",
    "canonical/governance/IF_SCOPE_FINITE_PROTOCOL_BINDING_TRUTH_REPAIR_20261007_V1.json":
        "15c5e607e9f5c921d62bf75492e26021980e75fa",
    "canonical/verification/IF_SCOPE_FINITE_PROTOCOL_BINDING_CONNECTOR_VERIFICATION_20261007_V1.json":
        "b7bfc865267554f0c7005c0835f09107b2dec998",
    "canonical/governance/AA_BRIEFCASE_SHARED_RESIDUAL_RECONCILIATION_20261007_V1.json":
        "2ec5e65558f7f622d8ab486068a8ebf4ce39bd3e",
    "canonical/verification/AA_BRIEFCASE_SHARED_RESIDUAL_RECONCILIATION_VERIFICATION_20261007_V1.json":
        "f4e08f38d23b3fe45dd95b07459f27ef7bc5be92",
    "canonical/governance/SYNTHESIS_SINGLE_RESIDUAL_RECONCILIATION_20261007_V1.json":
        "a8825ddd105c6200f96ebf7435ba4de60f677be7",
    "canonical/verification/SYNTHESIS_SINGLE_RESIDUAL_RECONCILIATION_VERIFICATION_20261007_V1.json":
        "44d3ba256aef4eb92edee4d6c186ed35dc559141",
    "canonical/governance/UNKNOWN_DOMAIN_SINGLE_RESIDUAL_RECONCILIATION_20261007_V1.json":
        "6477b9d6d926d2810e347040c94c265961aae39e",
    "canonical/verification/UNKNOWN_DOMAIN_SINGLE_RESIDUAL_RECONCILIATION_VERIFICATION_20261007_V1.json":
        "54dee66e4a1a9fca7c7e87c19439db941e2d6697",
}


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OBJECT_REQUIRED:" + str(path))
    return value


def verify() -> dict:
    errors: list[str] = []

    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append("MISSING:" + rel)
        elif blob_sha(path) != expected:
            errors.append("DRIFT:" + rel)

    if not POINTER.is_file():
        return {"pass": False, "errors": errors + ["POINTER_MISSING"], "terminal": False}

    p = load(POINTER)
    if p.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V8":
        errors.append("POINTER_SCHEMA")
    if "TERMINAL_FALSE" not in str(p.get("status", "")):
        errors.append("POINTER_STATUS")

    truth = p.get("live_truth", {})
    if truth.get("fixed_authorized_target_trace_scope_closed") is not True:
        errors.append("TARGET_SCOPE")
    if truth.get("known_sound_D_B_certificate_record_count") != 16:
        errors.append("DB_COUNT")
    if truth.get("cache_record_count_is_not_semantic_coverage_measure") is not True:
        errors.append("COUNT_GUARD")
    if truth.get("independent_top_level_terminal_predicate_count") != 2:
        errors.append("TOP_LEVEL_COUNT")
    if set(truth.get("independent_top_level_terminal_predicates", [])) != {
        "COMPLETE_SELECTED_CONTEXT_ABC",
        "D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY",
    }:
        errors.append("TOP_LEVEL_SET")
    if truth.get("if_scope_boundary_refinement_closed") is not True:
        errors.append("IF_NOT_CLOSED")
    if truth.get("if_scope_boundary_soundly_subtracted_from_U") is not True:
        errors.append("IF_NOT_SUBTRACTED")
    if truth.get("undeclared_IF_population_inference_required") is not False:
        errors.append("IF_POPULATION_REOPENED")
    if truth.get("current_U_empty_proved") is not False:
        errors.append("U_EMPTY_OVERCLAIM")
    if truth.get("complete_selected_context_ABC_closed") is not False:
        errors.append("ABC_OVERCLAIM")
    if truth.get("D_finality_closed") is not False:
        errors.append("D_OVERCLAIM")
    if truth.get("terminal") is not False:
        errors.append("TERMINAL_OVERCLAIM")

    frontier = p.get("only_live_ABC_frontier", {})
    if frontier.get("closure_condition") != "U_IS_EMPTY":
        errors.append("U_NORMAL_FORM")
    if "IF_SCOPE_BOUNDARY_NONINFERIOR" not in set(frontier.get("closed_refinement_delta", [])):
        errors.append("IF_DELTA")

    v10 = load(ROOT / "canonical/governance/DB_EXISTING_EVIDENCE_SATURATION_UNION_20261007_V10.json")
    if v10.get("saturation_result", {}).get("sound_subtraction_from_U") is not True:
        errors.append("V10_U_SUBTRACTION")
    if v10.get("saturation_result", {}).get("U_empty_proved") is not False:
        errors.append("V10_U_OVERCLAIM")

    iv = load(ROOT / "canonical/verification/DB_EXISTING_EVIDENCE_SATURATION_UNION_WOLFRAM_VERIFY_20261007_V10.json")
    if iv.get("verified", {}).get("if_scope_boundary_refinement_closed") is not True:
        errors.append("V10_INDEPENDENT_IF")
    if iv.get("verified", {}).get("sound_subtraction_from_U") is not True:
        errors.append("V10_INDEPENDENT_U")

    required_nonclaims = {
        "NO_CLAIM_U_IS_EMPTY.",
        "NO_CLAIM_D_FINALITY_IS_CLOSED.",
        "NO_TERMINAL_CREDIT.",
    }
    if not required_nonclaims.issubset(set(p.get("hard_nonclaims", []))):
        errors.append("NONCLAIM_GUARD")

    return {
        "pass": not errors,
        "errors": errors,
        "authority_schema": p.get("schema"),
        "sound_record_count": 16 if not errors else None,
        "newly_closed_refinement": "IF_SCOPE_BOUNDARY_NONINFERIOR" if not errors else None,
        "U_empty_proved": False,
        "ABC_closed": False,
        "D_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)
