from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MANIFEST = "canonical/governance/V17_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V1.json"

EXPECTED = {
    "canonical/action_intents/ACTION_INTENT_V17_DB_SATURATION_20261007_V1.json": "1b28f9fc0e2efa7b151dff44d60bae7f6534e4fb",
    "canonical/governance/TERMINAL_NOW_V16_RESIDUAL_NORMALIZATION_20261007_V1.json": "e77766459fecbc15c983cbe5a26175101b94d5f7",
    "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json": "8f64a698645e9ba0fe433560cbee3f084700b6e7",
    "canonical/governance/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_20261007_V1.json": "0ccc3ecbdbf2636b8f1e7f0daf959a48350cb82e",
    "canonical/verification/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_INDEPENDENT_VERIFICATION_20261007_V1.json": "f3e86554f87868587d4ce3f58f97714b2dbe4672",
    "canonical/runtime/p2_p3_information_safe_proof_suites_v2.py": "9d3d9bb837a98a7f78b5794cec0c0ae88bb32860",
    "canonical/governance/V14_P2_PROFESSIONAL_TOP_LAW_SELECTED_CELL_20261007_V1.json": "481b8efd7925c19d7f4e77faf70dfb2ec649cca5",
    "canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json": "28692768a21e95b51e847417cf5ba2343587e4aa",
    "canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json": "aefee446782989518c9794db1e73909bd3c4f55c",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(path: str):
    return json.loads((ROOT / path).read_text())


def verify():
    errors: list[str] = []

    for path, expected in EXPECTED.items():
        p = ROOT / path
        if not p.is_file():
            errors.append("SOURCE_MISSING:" + path)
            continue
        actual = git_blob_sha(p.read_bytes())
        if actual != expected:
            errors.append("SOURCE_DRIFT:" + path + ":" + actual)

    manifest = load(MANIFEST)
    base = load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json")
    p2 = load("canonical/governance/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_20261007_V1.json")
    p2_verify = load("canonical/verification/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_INDEPENDENT_VERIFICATION_20261007_V1.json")
    t1 = load("canonical/governance/V14_P2_PROFESSIONAL_TOP_LAW_SELECTED_CELL_20261007_V1.json")
    unsupported = load("canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json")
    unsupported_verify = load("canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json")
    intent = load("canonical/action_intents/ACTION_INTENT_V17_DB_SATURATION_20261007_V1.json")
    suite_text = (ROOT / "canonical/runtime/p2_p3_information_safe_proof_suites_v2.py").read_text()

    base_ids = [x["id"] for x in base.get("known_D_B_regions", [])]
    if len(base_ids) != 10 or len(set(base_ids)) != 10:
        errors.append("BASE_TEN_INVALID")

    inherited = manifest.get("base_region_ids_inherited_from_v3", [])
    if inherited != base_ids:
        errors.append("BASE_REGION_ID_DRIFT")

    new_regions = manifest.get("new_sound_context_regions", [])
    if len(new_regions) != 1:
        errors.append("NEW_REGION_COUNT_NOT_ONE")
    else:
        region = new_regions[0]
        if region.get("id") != "PROFESSIONAL_ARTIFACT_P2_INFO_SAFE_V2_ALL_GENERATED_CASES":
            errors.append("NEW_REGION_ID")
        if region.get("kind") != "SELECTED_CONTEXT_DIRECT_E2E_UNIVERSAL_CELL":
            errors.append("NEW_REGION_KIND")

    abc = p2.get("abc_consequence") or {}
    if abc.get("selected_cell_scope_complete") is not True:
        errors.append("P2_SCOPE_NOT_COMPLETE")
    if abc.get("direct_e2e") is not True:
        errors.append("P2_NOT_DIRECT_E2E")
    if abc.get("proposed_D_B_region") != "PROFESSIONAL_ARTIFACT_P2_INFO_SAFE_V2_ALL_GENERATED_CASES":
        errors.append("P2_DB_REGION_MISMATCH")
    if abc.get("artifact_family_closed") is not False or abc.get("professional_quality_global_closed") is not False:
        errors.append("P2_OVERCLAIM")

    if not str(p2_verify.get("status", "")).startswith("INDEPENDENT_WOLFRAM_ALGEBRA_PASS"):
        errors.append("P2_INDEPENDENT_VERIFICATION_MISSING")
    if not (p2_verify.get("wolfram") or {}).get("result", {}).get("All16ScoreCasesEqual"):
        errors.append("P2_ALGEBRA_NOT_PASS")

    # The generator domain cannot be identical to the frozen 30-case context:
    # the public case carries the arbitrary integer seed and its provenance into
    # task.evidence, so arbitrarily many integer seeds produce seed-distinguished
    # public case objects. V3's prior P2 region is explicitly a finite 30-case cell.
    required_suite_tokens = [
        'if not isinstance(seed,int)',
        '"seed":seed',
        'f"SRC-{seed}-{i}"',
        'if not isinstance(difficulty,int)',
        '1<=difficulty<=5',
    ]
    for token in required_suite_tokens:
        if token not in suite_text:
            errors.append("GENERATOR_DOMAIN_PROOF_TOKEN_MISSING:" + token)

    exact_domain = ((p2.get("target") or {}).get("exact_domain") or "")
    if "ANY_INTEGER_SEED" not in exact_domain or "DIFFICULTY_1_THROUGH_5" not in exact_domain:
        errors.append("P2_EXACT_DOMAIN_NOT_UNBOUNDED_SEED")

    if "P2_PROFESSIONAL_T1_FROZEN_30_HIDDEN_OPTIMUM" not in base_ids:
        errors.append("FROZEN_30_BASE_REGION_MISSING")

    t1_case = ((t1.get("existing_terminal_witness") or {}).get("case_id"))
    unsupported_case = ((unsupported.get("direct_end_to_end_witness") or {}).get("case_id"))
    if not t1_case or t1_case != unsupported_case:
        errors.append("REDUNDANT_CERTIFICATE_CONTEXT_MISMATCH")
    if (unsupported.get("selected_property_cell") or {}).get("population_complete") is not True:
        errors.append("UNSUPPORTED_PROPERTY_POPULATION_NOT_COMPLETE")
    if (unsupported.get("selected_property_cell") or {}).get("brain_value") != 1:
        errors.append("UNSUPPORTED_PROPERTY_NOT_TOP")
    if (unsupported.get("selected_property_cell") or {}).get("top_value") != 1:
        errors.append("UNSUPPORTED_PROPERTY_TOP_VALUE_DRIFT")
    if unsupported.get("v14_effect", {}).get("new_target_reality_consumed") != 0:
        errors.append("UNSUPPORTED_PROPERTY_CONSUMED_REALITY")
    if not str(unsupported_verify.get("status", "")).startswith("INDEPENDENT_WOLFRAM_BOOLEAN_TOP_LOGIC_PASS"):
        errors.append("UNSUPPORTED_PROPERTY_VERIFICATION_MISSING")
    if unsupported_verify.get("wolfram_result") is not True:
        errors.append("UNSUPPORTED_PROPERTY_WOLFRAM_FAIL")

    redundant = manifest.get("redundant_same_context_certificates", [])
    if len(redundant) != 1 or redundant[0].get("id") != "PROFESSIONAL_ARTIFACT_T1_FROZEN_30_ZERO_UNSUPPORTED_MATERIAL_CONTENT":
        errors.append("REDUNDANT_CERTIFICATE_ACCOUNTING")

    result = manifest.get("saturation_result") or {}
    if result.get("known_sound_context_region_count") != 11:
        errors.append("ELEVEN_COUNT_DRIFT")
    if result.get("new_nonidentical_context_region_count") != 1:
        errors.append("DELTA_COUNT_DRIFT")
    if result.get("redundant_same_context_certificate_count") != 1:
        errors.append("REDUNDANT_COUNT_DRIFT")
    if result.get("coverage_measure_not_claimed") is not True:
        errors.append("COVERAGE_MEASURE_OVERCLAIM")

    terminal_truth = manifest.get("terminal_truth") or {}
    if terminal_truth != {
        "complete_selected_context_ABC": False,
        "D_final_route_ownership_effect_donor_independence_finality": False,
        "terminal": False,
    }:
        errors.append("TERMINAL_TRUTH_OVERCLAIM")

    accounting = manifest.get("accounting") or {}
    if any(accounting.get(k) != 0 for k in (
        "incremental_spend_usd",
        "fresh_reality_units_consumed",
        "terminal_cases_consumed",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
        "terminal_credit_delta",
    )):
        errors.append("NONZERO_CREDIT_OR_SPEND")

    if intent.get("canonical_base_commit") != "787f2fc0e23b7ddcb3f73c611d4acf92867b2930":
        errors.append("INTENT_BASE_DRIFT")
    if (intent.get("reality_query_admission") or {}).get("admission_verdict") != "NO_REALITY_QUERY_REQUIRED":
        errors.append("REALITY_QUERY_WRONGLY_ADMITTED")

    return {
        "schema": "PROJECT_BRAIN_V17_DB_EXISTING_EVIDENCE_SATURATION_VERIFY_V1",
        "status": "PASS__ELEVEN_NAMED_SOUND_CONTEXT_REGIONS__ONE_NEW_NONIDENTICAL_CONTEXT_DOMAIN__ONE_REDUNDANT_SAME_CONTEXT_CERTIFICATE__ZERO_REALITY__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": errors,
        "base_region_count": 10,
        "new_named_context_region_count": 1 if not errors else 0,
        "resulting_named_context_region_count": 11 if not errors else 0,
        "redundant_same_context_certificate_count": 1 if not errors else 0,
        "coverage_measure_claimed": False,
        "abc_closed": False,
        "d_finality_closed": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
