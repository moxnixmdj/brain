import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/K6_PROOF_ROLE_RECLASSIFICATION_20261006_V1.json"
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V2.json"
ROOTS=ROOT/"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
GRAPH=ROOT/"canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json"
RECON=ROOT/"canonical/governance/ATOMIC_SURVIVOR_EXECUTION_AUTHORITY_RECONCILIATION_V1.json"
K6C=ROOT/"canonical/governance/K6_DECISION_REFINEMENT_COMPILER_20261006_V1.json"
K6V=ROOT/"canonical/verification/K6_DECISION_REFINEMENT_COMPILER_SPRITE_VERIFICATION_20261006_V1.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))

def test_exact_current_authority_supports_zero_positive_gap():
    d=load(P); a=load(AUTH)
    assert d["source_bindings"]["current_authority"]["git_blob_sha"]=="f17f2f83e7ac8173b0bf54a5cde65646125a15fd"
    assert a["current_truth"]["root1_positive_gap_count"]==0

def test_preproof_implementation_residual_is_zero():
    g=load(GRAPH); r=load(RECON)
    assert "ZERO_PREPROOF_IMPLEMENTATION_RESIDUALS" in g["status"]
    assert r["facts"]["current_preproof_implementation_residual_count"]==0
    assert r["scheduling_effect"]["execute_atomic_survivors_now"] is False
    assert r["scheduling_effect"]["generic_s0_g0_donor_or_mechanism_work_authorized"] is False

def test_k6_refinement_operator_is_owned_bounded_operator():
    c=load(K6C); v=load(K6V)
    assert "BRAIN_OWNED_OPERATOR" in c["status"]
    assert "GENERIC_REFINEMENT_OPERATOR_BRAIN_OWNED" in v["status"]
    assert "K6_OPERATOR_IMPLEMENTATION_IS_NO_LONGER_THE_PRIMARY_UNKNOWN" in v["consequence"]

def test_reclassification_preserves_truth_and_rejects_missing_capability_inference():
    d=load(P)
    r=d["reclassification"]
    assert r["current_positive_missing_semantic_generator_count"]==0
    assert r["current_unresolved_semantic_proof_role_count"]==1
    assert r["new_scheduler_label"]=="UNRESOLVED_SEMANTIC_PROOF_AND_INPUT_BINDING_ROLE"
    assert "UNPROVED_K6_BINDING_DOES_NOT_IMPLY_A_MISSING_IMPLEMENTATION_CAPABILITY" in r["deleted_inference"]
    assert d["relation_to_29_truth_basis"]["truth_obligation_deletion"]==0

def test_semantic_load_is_split_into_certification_input_and_owned_operator():
    d=load(P)
    s=d["load_split"]
    assert s["target_acceptability_semantics"]["classification"]=="CERTIFICATION_AND_TARGET_SEMANTICS"
    assert s["precommitment_discriminator_truth"]["classification"]=="INPUT_INFORMATION_OR_EVIDENCE_ACQUISITION_UNLESS_POSITIVE_TRANSFORM_GAP_PROVED"
    assert s["decision_refinement_operator"]["classification"]=="VERIFIED_BRAIN_OWNED_BOUNDED_OPERATOR"
    assert s["decision_refinement_operator"]["open_implementation_gap"] is False

def test_positive_gap_reopen_requires_causal_witness():
    d=load(P)
    req=d["positive_gap_reopen_test"]["all_required"]
    assert len(req)>=7
    assert any("CAUSALLY_LOCALIZED" in x for x in req)
    assert any("OPUS55_OR_A_SOUND" in x for x in req)
    assert "PROMOTE_ROOT1_POSITIVE_GAP" in d["positive_gap_reopen_test"]["only_then"]

def test_zero_credit_and_no_terminal_claim():
    d=load(P)
    for k,v in d["accounting"].items():
        if k.endswith("_delta"):
            assert v==0
    assert "NO_CLAIM_K6_TERMINAL_REQUIREMENT_IS_DELETED" in d["hard_nonclaims"]
    assert "NO_CLAIM_TERMINAL_GOAL_ACHIEVED" in d["hard_nonclaims"]
