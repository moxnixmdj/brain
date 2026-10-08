from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P3_BINARY_EXPLICIT_TOP_LAW_REGION_VERIFIER_V1"
REGION="canonical/governance/P3_BOUND_BINARY_REAL_CONTEXT_TOP_LAW_REGION_20261008_V1.json"
EXPECTED={
 REGION:"e367ff0a5734e2430b0b5476bf073b4688c410e1",
 "canonical/runtime/p3_binary_explicit_contract_membership_v1.py":"ca24d891210fb6d885a959c26a9da3451a8b67c7",
 "canonical/verification/P3_BINARY_EXPLICIT_CONTRACT_MEMBERSHIP_TWO_SPRITE_VERIFICATION_20261008_V1.json":"9d39f0b01f5ff571c8f607f0a4ec50b97542e017",
 "canonical/runtime/p3_binary_decision_grounded_expression_v1.py":"590cdc4e7f5a513d0e40bb31afed20df61826bad",
 "canonical/verification/P3_BINARY_DECISION_GROUNDED_EXPRESSION_TWO_SPRITE_VERIFICATION_20261008_V1.json":"2964ab7b86b61a6362e310e35b4a38ab75e04e87",
 "canonical/governance/P3_BOUND_OBJECTIVE_ROLE_PRESENTATION_TOP_LAW_CANDIDATE_20261008_V1.json":"471a17702a9ab6e0c3b68e9d5714003469c9aa7c",
 "canonical/governance/SYNTHESIS_EXPLICIT_SELECTION_ORDER_TOP_LAW_CELL_20261007_V2.json":"70f5796d77b79e96ffcc706918410da77dd4d653",
 "canonical/governance/SYNTHESIS_P3_CONTRACT_SEMANTIC_REDUCTION_20261005_V1.json":"f6b83872bf1288693e4e5250a561599f1cc6fa75",
 "canonical/governance/P3_BOUND_BINARY_REAL_CONTEXT_MEMBERSHIP_SELF_CERTIFICATION_INVALIDATION_20261008_V1.json":"e27c6108415dfcd2505a086e297f6c22971f2c83",
}

def blob(path):
    b=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def verify():
    errors=[]
    for path,want in EXPECTED.items():
        p=ROOT/path
        if not p.is_file():
            errors.append("MISSING:"+path);continue
        got=blob(path)
        if got!=want: errors.append("DRIFT:"+path+":"+got)

    if errors:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":errors,
                "parameterized_D_B_region_candidate":False,"whole_p3_closed":False,
                "terminal":False,"terminal_credit_delta":0}

    region=load(REGION)
    mem=load("canonical/verification/P3_BINARY_EXPLICIT_CONTRACT_MEMBERSHIP_TWO_SPRITE_VERIFICATION_20261008_V1.json")
    dec=load("canonical/verification/P3_BINARY_DECISION_GROUNDED_EXPRESSION_TWO_SPRITE_VERIFICATION_20261008_V1.json")
    pres=load("canonical/governance/P3_BOUND_OBJECTIVE_ROLE_PRESENTATION_TOP_LAW_CANDIDATE_20261008_V1.json")
    top=load("canonical/governance/SYNTHESIS_EXPLICIT_SELECTION_ORDER_TOP_LAW_CELL_20261007_V2.json")
    contract=load("canonical/governance/SYNTHESIS_P3_CONTRACT_SEMANTIC_REDUCTION_20261005_V1.json")
    invalid=load("canonical/governance/P3_BOUND_BINARY_REAL_CONTEXT_MEMBERSHIP_SELF_CERTIFICATION_INVALIDATION_20261008_V1.json")
    runtime=(ROOT/"canonical/runtime/p3_binary_explicit_contract_membership_v1.py").read_text(encoding="utf-8")

    if region.get("status")!="CANDIDATE_PARAMETERIZED_SOUND_TOP_LAW_REGION__STRICT_EXPLICIT_ROOT_SOURCE_MEMBERSHIP__ZERO_GLOBAL_TERMINAL_CREDIT":
        errors.append("REGION_STATUS")
    rr=region.get("region") or {}
    if rr.get("id")!="P3_BOUND_BINARY_REAL_CONTEXT_GROUNDED_DECISION_TOP_LAW_V1": errors.append("REGION_ID")
    if (rr.get("recognizer") or {}).get("git_blob_sha")!=EXPECTED["canonical/runtime/p3_binary_explicit_contract_membership_v1.py"]:
        errors.append("REGION_RECOGNIZER_BINDING")
    if (rr.get("policy") or {}).get("git_blob_sha")!=EXPECTED["canonical/runtime/p3_binary_decision_grounded_expression_v1.py"]:
        errors.append("REGION_POLICY_BINDING")

    if not str(mem.get("status") or "").startswith("PASS_20_OF_20_ON_TWO_SPRITES__LOSSLESS_EXPLICIT_ROOT_SOURCE_CLASS"):
        errors.append("MEMBERSHIP_VERIFICATION_STATUS")
    if len(mem.get("verification") or [])!=2 or any(x.get("tests_passed")!=20 or x.get("tests_run")!=20 for x in mem.get("verification") or []):
        errors.append("MEMBERSHIP_TWO_SPRITE_COUNTS")
    proved=set(mem.get("proved") or [])
    for x in {
      "ROOT_TASK_BYTES_MUST_BE_STRICT_JSON_WITH_EXACT_P3_BINARY_CONTRACT_FIELDS",
      "DUPLICATE_JSON_KEYS_REJECTED",
      "EXTRA_TOP_TASK_CLAIM_EVIDENCE_PROFILE_OR_CONSTRAINT_FIELDS_REJECTED",
      "VERIFIED_BINARY_GROUNDED_EXPRESSION_POLICY_RECOMPUTED_FROM_THE_PARSED_BYTES",
      "NO_CALLER_MEMBERSHIP_FLAG_OR_SEMANTIC_EXTRACTOR_ACCEPTED",
    }:
        if x not in proved: errors.append("MEMBERSHIP_PROPERTY:"+x)
    if "UPSTREAM_TASK_BYTES_ARE_THE_UNAVOIDABLE_ROOT_OF_TRUST" not in str(mem.get("root_boundary")):
        errors.append("ROOT_TRUST_BOUNDARY")

    forbidden_code_patterns=(
      'get("independent_verified")',
      "get('independent_verified')",
      'get("authority_scope_ref")',
      "get('authority_scope_ref')",
      'get("extractor_units")',
      "get('extractor_units')",
    )
    for forbidden in forbidden_code_patterns:
        if forbidden in runtime: errors.append("SELF_CERTIFYING_RUNTIME_PATTERN:"+forbidden)
    required_patterns=(
      "object_pairs_hook=_pairs",
      '_exact(doc,{"contract","objective","task"},"TOP_LEVEL")',
      '_exact(task,{"claims","evidence","audience_profile"},"TASK")',
      '"membership_self_assertion_permitted":False',
      '"semantic_extractor_required":False',
      'expression({"objective":objective,"v2_input":public})',
    )
    for required in required_patterns:
        if required not in runtime: errors.append("STRICT_RUNTIME_PATTERN_MISSING:"+required)

    if not str(dec.get("status") or "").startswith("PASS_11_OF_11_ON_TWO_SPRITES__BOUND_BINARY_DECISION_EXPRESSION_OWNED"):
        errors.append("DECISION_VERIFICATION_STATUS")
    if len(dec.get("verification") or [])!=2 or any(x.get("tests_passed")!=11 or x.get("tests_run")!=11 for x in dec.get("verification") or []):
        errors.append("DECISION_TWO_SPRITE_COUNTS")

    if not str(pres.get("status") or "").startswith("VERIFIED_MECHANICAL_TOP_LAW_COMPILER__TWO_SPRITE_EXACT_BYTE_PASS"):
        errors.append("PRESENTATION_TOP_LAW_STATUS")
    theorem=top.get("theorem") or {}
    if theorem.get("common_policy_certificate") is not True: errors.append("TOP_LAW_COMMON_POLICY")
    if theorem.get("comparator_required") is not False: errors.append("TOP_LAW_COMPARATOR")
    if (contract.get("semantic_implication") or {}).get("direction")!="P3_REQUIRED_CHECKS => SYNTHESIS_CONTRACT_SUCCESS":
        errors.append("CONTRACT_IMPLICATION")

    if not str(invalid.get("status") or "").startswith("PROMOTION_INVALIDATED__CALLER_CONSTRUCTIBLE_AUTHORITY_AND_SEMANTIC_RECEIPTS"):
        errors.append("OLD_ROUTE_NOT_INVALIDATED")
    eff=invalid.get("effect") or {}
    if eff.get("old_runtime_may_authorize_db_admission") is not False or eff.get("old_runtime_may_authorize_u_subtraction") is not False:
        errors.append("OLD_ROUTE_AUTHORITY_NOT_ZERO")

    rt=region.get("theorem") or {}
    if rt.get("target_comparator_required") is not False or rt.get("common_policy_region") is not True:
        errors.append("REGION_THEOREM_FLAGS")
    if (region.get("resource_and_ownership") or {}).get("brain_owned") is not True:
        errors.append("OWNERSHIP_FLAG")
    if region.get("accounting",{}).get("terminal_credit_delta")!=0:
        errors.append("TERMINAL_CREDIT_DRIFT")

    return {
      "schema":SCHEMA,
      "pass":not errors,
      "status":"PASS__STRICT_EXPLICIT_P3_BINARY_PARAMETERIZED_TOP_LAW_REGION_VERIFIED__ZERO_GLOBAL_CREDIT" if not errors else "FAIL_CLOSED",
      "errors":errors,
      "region_id":rr.get("id"),
      "parameterized_D_B_region_candidate":not errors,
      "root_task_authority_self_proved":False,
      "free_form_p3_closed":False,
      "whole_p3_closed":False,
      "u_empty":False,
      "terminal":False,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=verify();print(json.dumps(out,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
