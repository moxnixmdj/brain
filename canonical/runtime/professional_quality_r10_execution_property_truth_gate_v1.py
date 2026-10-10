"""R10 execution whole-leaf property-truth promotion gate.

Combines the already-independent whole-leaf scope proof with independently
replayed positive/near-miss/adversarial execution evidence for the exact R10
execution claim. Authority is limited to this one leaf acceptance predicate.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_EXECUTION_PROPERTY_TRUTH_GATE_V1"
LEAF_ID="PQ::R10_ANALYSIS_DECISION::EXECUTION"
ROOT_ID="R10_ANALYSIS_DECISION"
CLAIM_ID="205a864e7d7a56a14a46bb75923cc9b11126d479676d26d88803831da1197294"
SCOPE_VERIFY_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_V2_GATE_VERIFY_V1"
CHALLENGE_VERIFY_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_EXECUTION_PROPERTY_CHALLENGE_VERIFY_V1"
EXPECTED_ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
GUARD_BLOB="d0bbda399a71ea7f30aae9095237b1ab2542647c"
TEST_BLOB="8a57df62f10fe6f3a949b2adf3d412451f18fb32"

def _base(status:str, passed:bool)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,
        "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
        "whole_leaf_property_truth_proved":False,
        "leaf_property_truth_authority":False,
        "global_leaf_closed":False,"root_closed":False,
        "domain_semantic_closure":False,"domain_execution_closure":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {**_base("FAIL_CLOSED",False),"reason":reason,**extra}

def evaluate(*, leaf_manifest:Mapping[str,Any], scope_verification:Mapping[str,Any],
             challenge_verification:Mapping[str,Any])->dict[str,Any]:
    roots=leaf_manifest.get("roots")
    if not isinstance(roots,list):
        return _fail("LEAF_MANIFEST_ROOTS_INVALID")
    r10=next((x for x in roots if isinstance(x,Mapping) and x.get("root_id")==ROOT_ID),None)
    if not isinstance(r10,Mapping):
        return _fail("R10_ROOT_NOT_IN_MANIFEST")
    leaf=r10.get("execution_leaf")
    if not isinstance(leaf,Mapping) or leaf.get("id")!=LEAF_ID:
        return _fail("R10_EXECUTION_LEAF_IDENTITY_INVALID")
    if leaf.get("acceptance")!=EXPECTED_ACCEPTANCE:
        return _fail("R10_EXECUTION_ACCEPTANCE_DRIFT")

    if scope_verification.get("schema")!=SCOPE_VERIFY_SCHEMA:
        return _fail("SCOPE_VERIFICATION_SCHEMA_INVALID")
    if not str(scope_verification.get("status") or "").startswith("PASS__"):
        return _fail("SCOPE_VERIFICATION_NOT_PASS")
    if scope_verification.get("leaf_id")!=LEAF_ID or scope_verification.get("claim_id")!=CLAIM_ID:
        return _fail("SCOPE_VERIFICATION_IDENTITY_MISMATCH")
    consequence=scope_verification.get("consequence")
    if not isinstance(consequence,Mapping):
        return _fail("SCOPE_VERIFICATION_CONSEQUENCE_INVALID")
    if consequence.get("whole_leaf_domain_equivalence_proved") is not True:
        return _fail("WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")
    if consequence.get("whole_leaf_scope_complete") is not True:
        return _fail("WHOLE_LEAF_SCOPE_COMPLETE_REQUIRED")
    if consequence.get("property_truth_ready") is not True:
        return _fail("PROPERTY_TRUTH_READY_REQUIRED")
    if consequence.get("leaf_property_truth_authority") is not False:
        return _fail("SCOPE_RECEIPT_SELF_PROPERTY_AUTHORITY_FORBIDDEN")

    if challenge_verification.get("schema")!=CHALLENGE_VERIFY_SCHEMA:
        return _fail("CHALLENGE_VERIFICATION_SCHEMA_INVALID")
    if not str(challenge_verification.get("status") or "").startswith("PASS__DUAL_INDEPENDENT_FOCUSED_REPLAY"):
        return _fail("CHALLENGE_VERIFICATION_NOT_PASS")
    if challenge_verification.get("leaf_id")!=LEAF_ID or challenge_verification.get("root_id")!=ROOT_ID or challenge_verification.get("claim_id")!=CLAIM_ID:
        return _fail("CHALLENGE_VERIFICATION_IDENTITY_MISMATCH")
    if challenge_verification.get("leaf_acceptance")!=EXPECTED_ACCEPTANCE:
        return _fail("CHALLENGE_ACCEPTANCE_MISMATCH")
    blobs=challenge_verification.get("exact_blobs")
    if not isinstance(blobs,Mapping) or blobs.get("guard_runtime")!=GUARD_BLOB or blobs.get("challenge_tests")!=TEST_BLOB:
        return _fail("CHALLENGE_EXACT_BYTES_MISMATCH")
    replays=challenge_verification.get("replay")
    if not isinstance(replays,list) or len(replays)<2:
        return _fail("DUAL_INDEPENDENT_REPLAY_REQUIRED")
    carriers=set()
    for row in replays:
        if not isinstance(row,Mapping):
            return _fail("REPLAY_ROW_INVALID")
        if row.get("py_compile")!="PASS" or row.get("tests_run")!=12 or row.get("tests_passed")!=12 or row.get("tests_failed")!=0:
            return _fail("REPLAY_NOT_12_OF_12")
        cid=row.get("carrier_id")
        if not isinstance(cid,str) or not cid:
            return _fail("REPLAY_CARRIER_ID_REQUIRED")
        carriers.add(cid)
    if len(carriers)<2:
        return _fail("REPLAY_INDEPENDENCE_REQUIRED")

    cov=challenge_verification.get("observed_case_coverage")
    if not isinstance(cov,Mapping):
        return _fail("CASE_COVERAGE_INVALID")
    required_true=(
        "positive_clean_path","all_known_r10_defeaters_blocked","near_miss_signals_escalate",
        "unknown_detected_defeater_escalates","unmapped_material_signal_escalates",
        "missing_proof_slot_blocks","lossy_decision_contract_fails_closed",
        "omitted_decision_evidence_fails_closed","broad_acquisition_weakening_fails_closed",
        "profile_trigger_drift_fails_closed","catalog_drift_fails_closed",
        "claim_substitution_fails_closed",
    )
    missing=[k for k in required_true if cov.get(k) is not True]
    if missing:
        return _fail("REQUIRED_CASE_COVERAGE_MISSING",missing=missing)
    if cov.get("all_known_r10_defeaters_count")!=17 or cov.get("near_miss_signal_count")!=5:
        return _fail("CASE_COVERAGE_CARDINALITY_INVALID")
    nonclaims=set(challenge_verification.get("hard_nonclaims") or [])
    if "NO_CLAIM_ALL_CONCEIVABLE_DEFEATERS_ARE_ENUMERATED" not in nonclaims:
        return _fail("OPEN_WORLD_NONCLAIM_REQUIRED")
    if challenge_verification.get("leaf_property_truth_authority") is not False:
        return _fail("CHALLENGE_RECEIPT_SELF_PROPERTY_AUTHORITY_FORBIDDEN")

    return {
        **_base("PASS__R10_EXECUTION_WHOLE_LEAF_PROPERTY_TRUTH_CLOSED",True),
        "whole_leaf_property_truth_proved":True,
        "leaf_property_truth_authority":True,
        "global_leaf_closed":True,
        "scope_semantics":"EXACT_WHOLE_ADMISSIBLE_R10_EXECUTION_LEAF_CLAIM_SCOPE",
        "property_semantics":"EXACT_MANIFEST_ACCEPTANCE_CASE_SUITE_ON_CONTENT_ADDRESSED_RUNTIME_BYTES",
        "unknown_defeater_enumeration_claimed":False,
    }
