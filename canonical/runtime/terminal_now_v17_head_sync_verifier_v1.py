from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = "canonical/governance/TERMINAL_NOW_V17_HEAD_SYNCHRONIZED_RESIDUAL_NORMALIZATION_20261007_V1.json"
EXPECTED = {
    "canonical/governance/TERMINAL_NOW_V16_RESIDUAL_NORMALIZATION_20261007_V1.json":"e77766459fecbc15c983cbe5a26175101b94d5f7",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json":"09f11461c7aa1ee7719409723726712f68d03da8",
    "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json":"8f64a698645e9ba0fe433560cbee3f084700b6e7",
    "canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json":"28692768a21e95b51e847417cf5ba2343587e4aa",
    "canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json":"aefee446782989518c9794db1e73909bd3c4f55c",
    "canonical/governance/FINANCE_SHARED_SEMANTIC_RESIDUAL_RECONCILIATION_20261007_V1.json":"d9453733ac28a205305129ac7b80e6ea1b692815",
    "canonical/runtime/finance_shared_semantic_residual_reconciliation_verifier_v1.py":"aab40218ba8866ffbb44d003909fa15ad1b99cfe",
}

def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def verify():
    errors=[]
    for rel,want in EXPECTED.items():
        path=ROOT/rel
        if not path.is_file():
            errors.append("SOURCE_MISSING:"+rel)
            continue
        got=blob(path)
        if got!=want:
            errors.append("SOURCE_DRIFT:"+rel+":"+got)

    db=load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json")
    cell=load("canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json")
    independent=load("canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json")
    finance=load("canonical/governance/FINANCE_SHARED_SEMANTIC_RESIDUAL_RECONCILIATION_20261007_V1.json")
    gov=load(GOV)

    if (db.get("saturation_result") or {}).get("known_D_B_region_count") != 10:
        errors.append("PREDECESSOR_DB_COUNT_NOT_10")
    if (cell.get("v14_effect") or {}).get("add_to_D_B") != "ONLY_THIS_EXACT_FROZEN_T1_PROFESSIONAL_UNSUPPORTED_CONTENT_PROPERTY_CELL":
        errors.append("UNSUPPORTED_CONTENT_CELL_NOT_ADMISSIBLE_TO_DB")
    if independent.get("wolfram_result") is not True:
        errors.append("UNSUPPORTED_CONTENT_INDEPENDENT_TOP_LAW_NOT_VERIFIED")
    if "WHOLE_PROFESSIONAL_ARTIFACT_QUALITY_DOMINANCE" not in set(independent.get("not_verified") or []):
        errors.append("PROFESSIONAL_GLOBAL_CLOSURE_GUARD_MISSING")
    falsification=finance.get("falsification") or {}
    if falsification.get("exact_runtime_bound") is not True or falsification.get("finance_source_admitted") is not True:
        errors.append("FINANCE_ROUTE_NOT_EXACTLY_ADMITTED")
    if "NO_CLAIM_FINANCE_UNCOVERED_SCOPE_AUDIT_IS_CLOSED" not in set(finance.get("hard_nonclaims") or []):
        errors.append("FINANCE_CLOSURE_GUARD_MISSING")

    truth=gov.get("current_truth") or {}
    db2=gov.get("reconciled_d_b") or {}
    if db2.get("predecessor_known_sound_region_count") != 10:
        errors.append("V17_PREDECESSOR_COUNT_DRIFT")
    if db2.get("current_known_sound_region_count") != 11:
        errors.append("V17_CURRENT_DB_COUNT_NOT_11")
    if truth.get("known_sound_D_B_region_count") != 11:
        errors.append("V17_TRUTH_DB_COUNT_NOT_11")
    if truth.get("finance_owned_route_exists") is not True:
        errors.append("V17_FINANCE_ROUTE_LOST")
    if truth.get("finance_route_acquisition_or_donor_invention_required") is not False:
        errors.append("V17_STALE_FINANCE_ACQUISITION_BLOCKER_RETAINED")
    if truth.get("terminal") is not False:
        errors.append("V17_FALSE_TERMINAL_PROMOTION")
    if (gov.get("terminal_now_verdict") or {}).get("can_truthfully_set_terminal_true_from_current_bound_evidence") is not False:
        errors.append("V17_FALSE_TERMINAL_VERDICT")
    return {
        "schema":"PROJECT_BRAIN_TERMINAL_NOW_V17_HEAD_SYNCHRONIZATION_VERIFIER_V1",
        "status":"PASS__HEAD_SYNCHRONIZED__DB_10_TO_11__FINANCE_ROUTE_BLOCKER_DELETED__TERMINAL_FALSE" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "db_region_delta":1 if not errors else 0,
        "known_sound_D_B_region_count":11 if not errors else None,
        "finance_route_exists":not errors,
        "abc_closed":False,
        "d_finality_closed":False,
        "terminal":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
