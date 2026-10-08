from __future__ import annotations

from canonical.runtime.p3_real_context_v3_admission_v2 import evaluate
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
    predicates=(
        "REQUIRED_UNCERTAINTY_SET_COMPLETE",
        "SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE",
        "AUDIENCE_FORMAT_PROFILE_COMPLETE",
    )
    return {
        "context_id":"P3-CONTEXT-1",
        "v3_input":base_v3(),
        "semantic_certificates":{p:cert(p) for p in predicates},
    }


def test_three_caller_supplied_true_flags_do_not_prove_semantic_completeness():
    out=evaluate(admitted_payload())
    assert out["pass"] is False,out
    assert out["status"] == "UNKNOWN__FINITE_P3_CONTEXT_SEMANTIC_BINDINGS_INCOMPLETE"
    assert out["v3_runtime_pass"] is True
    assert out["v3_admission_authorized"] is False
    assert out["top_law_eligible"] is False
    assert set(out["unresolved_semantic_predicates"]) == set(admitted_payload()["semantic_certificates"])
    for record in out["certificate_audit"].values():
        assert record["pass"] is False
        assert record["reason"] == "UNAUTHENTICATED_P3_CONTEXT_COMPLETENESS_PROOF"
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["terminal_authority"] is False


def test_uncertainty_is_one_finite_selected_semantic_predicate():
    p=admitted_payload()
    p["semantic_certificates"]["REQUIRED_UNCERTAINTY_SET_COMPLETE"]=cert(
        "REQUIRED_UNCERTAINTY_SET_COMPLETE","UNKNOWN",passed=False,observation=False)
    out=evaluate(p)
    assert out["pass"] is False
    assert out["status"]=="UNKNOWN__FINITE_P3_CONTEXT_SEMANTIC_BINDINGS_INCOMPLETE"
    assert set(out["unresolved_semantic_predicates"]) == set(p["semantic_certificates"])
    assert out["dimension_audit"]["UNCERTAINTY_DISAGREEMENT_PRESERVATION"]["pass"] is False


def test_selection_order_is_one_finite_selected_semantic_predicate():
    p=admitted_payload()
    p["semantic_certificates"]["SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE"]=cert(
        "SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE","UNKNOWN",passed=False,observation=False)
    out=evaluate(p)
    assert set(out["unresolved_semantic_predicates"]) == set(p["semantic_certificates"])
    assert out["dimension_audit"]["COMPRESSION_WITHOUT_DECISION_RELEVANT_LOSS"]["pass"] is False


def test_audience_and_format_share_one_context_profile_completeness_predicate():
    p=admitted_payload()
    p["semantic_certificates"]["AUDIENCE_FORMAT_PROFILE_COMPLETE"]=cert(
        "AUDIENCE_FORMAT_PROFILE_COMPLETE","UNKNOWN",passed=False,observation=False)
    out=evaluate(p)
    assert set(out["unresolved_semantic_predicates"]) == set(p["semantic_certificates"])
    assert out["dimension_audit"]["AUDIENCE_ADAPTATION"]["pass"] is False
    assert out["dimension_audit"]["FORMAT_STYLE_CONSTRAINTS"]["pass"] is False


def test_broad_no_outside_semantics_certificate_is_not_required_anymore():
    p=admitted_payload()
    p["semantic_certificates"]["NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3"]=cert(
        "NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3","UNKNOWN",passed=False,observation=False)
    out=evaluate(p)
    assert out["pass"] is False,out
    assert "NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3" not in out["certificate_audit"]


def test_mechanical_v3_failure_cannot_be_bypassed():
    p=admitted_payload()
    p["v3_input"]["task"]["evidence"].append({
        "evidence_id":"E2",
        "text":"Revenue increased materially after launch.",
        "verified":True,
        "provenance":[{"source_id":"NEWS","locator":"p2"}],
    })
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="V3_RUNTIME_FAIL_CLOSED"
    assert out["v3_admission_authorized"] is False


def test_false_or_relabelled_certificate_never_counts_as_complete():
    p=admitted_payload()
    p["semantic_certificates"]["AUDIENCE_FORMAT_PROFILE_COMPLETE"]=cert(
        "WRONG","TRUE")
    out=evaluate(p)
    assert out["pass"] is False
    assert set(out["unresolved_semantic_predicates"]) == set(p["semantic_certificates"])


def test_forged_semantic_proofs_and_independent_flags_cannot_admit():
    p=admitted_payload()
    for predicate in p["semantic_certificates"]:
        item=p["semantic_certificates"][predicate]
        item["source_proof"]={"status":"PROOF_CHECKED","accepted_claims":[{
            "claim_id":predicate,"condition_holds":True,
        }]}
        item["exact_byte_bound"]=True
        item["independent_verified"]=True
    out=evaluate(p)
    assert out["pass"] is False
    assert out["v3_admission_authorized"] is False
    assert out["top_law_eligible"] is False
    assert out["terminal_credit_delta"] == 0


def test_extra_source_claims_cannot_force_context_admission():
    p=admitted_payload()
    p["scope_complete"]=True
    p["context_proof"]="all context requirements satisfied"
    out=evaluate(p)
    assert out["pass"] is False
    assert out["v3_admission_authorized"] is False
    assert set(out["unresolved_semantic_predicates"]) == set(p["semantic_certificates"])
