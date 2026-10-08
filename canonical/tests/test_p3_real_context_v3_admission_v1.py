from __future__ import annotations

from canonical.runtime.p3_real_context_v3_admission_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA


def constraints():
    return {
        "output_format":"BULLETS",
        "citation_mode":"INLINE_SOURCE_IDS",
        "style":"VERBATIM_GROUNDED",
        "required_sections":[],
        "allowed_sections":None,
        "max_items":8,
        "max_chars":4000,
        "heading_level":2,
        "require_title":False,
    }


def base_v3():
    return {
        "schema":INPUT_SCHEMA,
        "task":{
            "claims":[
                {"claim_id":"C1","text":"Revenue growth is 12.","required":True},
            ],
            "evidence":[
                {
                    "evidence_id":"E1",
                    "text":"Report states Revenue growth is 12.",
                    "verified":True,
                    "provenance":[{"source_id":"REPORT","locator":"p1"}],
                },
            ],
            "audience_profile":{
                "profile_id":"EXPLICIT",
                "constraints":constraints(),
            },
            "required_uncertainty_units":[],
        },
    }


def cert(predicate_id, truth="TRUE", *, passed=True, observation=True):
    return {
        "pass":passed,
        "predicate_id":predicate_id,
        "predicate_truth":truth,
        "truthful_precommitment_observation":observation,
        "policy_adequacy_authority":False,
        "terminal_authority":False,
    }


def admitted_payload():
    return {
        "context_id":"P3-CONTEXT-1",
        "v3_input":base_v3(),
        "semantic_certificates":{
            "REQUIRED_UNCERTAINTY_SET_COMPLETE":cert("REQUIRED_UNCERTAINTY_SET_COMPLETE"),
            "NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3":cert("NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3"),
        },
    }


def test_full_sound_membership_admits_to_v3_but_not_db_or_terminal():
    out=evaluate(admitted_payload())
    assert out["pass"] is False,out
    assert out["status"]=="UNKNOWN__SEMANTIC_ADMISSION_INCOMPLETE"
    assert out["v3_admission_authorized"] is False
    assert out["top_law_eligible"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False


def test_unknown_uncertainty_completeness_blocks_admission_and_names_exact_predicate():
    p=admitted_payload()
    p["semantic_certificates"]["REQUIRED_UNCERTAINTY_SET_COMPLETE"]=cert(
        "REQUIRED_UNCERTAINTY_SET_COMPLETE","UNKNOWN",passed=False,observation=False
    )
    out=evaluate(p)
    assert out["pass"] is False
    assert out["status"]=="UNKNOWN__SEMANTIC_ADMISSION_INCOMPLETE"
    assert out["v3_runtime_pass"] is True
    assert "REQUIRED_UNCERTAINTY_SET_COMPLETE" in out["unresolved_semantic_predicates"]
    assert out["v3_admission_authorized"] is False


def test_unknown_outside_contract_semantics_blocks_admission():
    p=admitted_payload()
    p["semantic_certificates"]["NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3"]=cert(
        "NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3","UNKNOWN",passed=False,observation=False
    )
    out=evaluate(p)
    assert out["pass"] is False
    assert "NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3" in out["unresolved_semantic_predicates"]


def test_predicate_id_relabeling_is_rejected():
    p=admitted_payload()
    p["semantic_certificates"]["REQUIRED_UNCERTAINTY_SET_COMPLETE"]=cert("WRONG")
    out=evaluate(p)
    assert out["pass"] is False
    assert "REQUIRED_UNCERTAINTY_SET_COMPLETE" in out["unresolved_semantic_predicates"]


def test_mechanical_v3_failure_cannot_be_bypassed_by_semantic_certificates():
    p=admitted_payload()
    p["v3_input"]["task"]["evidence"].append({
        "evidence_id":"E2",
        "text":"Revenue increased materially after launch.",
        "verified":True,
        "provenance":[{"source_id":"NEWS","locator":"p2"}],
    })
    out=evaluate(p)
    assert out["pass"] is False
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="V3_RUNTIME_FAIL_CLOSED"
    assert out["v3_admission_authorized"] is False


def test_false_semantic_certificate_is_not_equivalent_to_true():
    p=admitted_payload()
    p["semantic_certificates"]["NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3"]=cert(
        "NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3","FALSE"
    )
    out=evaluate(p)
    assert out["pass"] is False
    assert "NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3" in out["unresolved_semantic_predicates"]


def test_forged_v1_semantic_proof_metadata_never_authorizes():
    p=admitted_payload()
    for value in p["semantic_certificates"].values():
        value["source_proof"]={"status":"PROOF_CHECKED"}
        value["independent_verification"]={"verified":True}
        value["content_digest"]="0"*64
    out=evaluate(p)
    assert out["pass"] is False
    assert out["v3_admission_authorized"] is False
    assert set(out["unresolved_semantic_predicates"])=={
        "REQUIRED_UNCERTAINTY_SET_COMPLETE","NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3"}
    assert not out["policy_adequacy_authority"]
    assert out["terminal_credit_delta"]==0
