import json
from pathlib import Path

P=Path(__file__).resolve().parents[2]/"canonical/governance/K6_PROOF_ROLE_RECLASSIFICATION_20261006_V1.json"

def load(): return json.loads(P.read_text(encoding="utf-8"))

def test_exact_source_hashes_are_frozen():
    d=load()
    got={k:v["git_blob_sha"] for k,v in d["source_bindings"].items()}
    assert got=={
      "current_authority":"f17f2f83e7ac8173b0bf54a5cde65646125a15fd",
      "root_cause_state":"7c1ed0adf243b92abab2cbdb6ebced921dcbb860",
      "global_obligation_graph":"eebdeb6de3b3cfaed30a3bc991dae0548d25e7f5",
      "execution_authority_reconciliation":"19b363f3f6be080b73ba144f82ef5f0a481217b1",
      "s0_g0_saturation":"31effb16940e6d5c0c95259871b2e3c00cb5e400",
      "k6_projection":"6de21878be3f45b318c8715487f03909a6f89e88",
      "k6_decision_compiler":"93cf697300efc0a34ca534f2ce0d8ffa0b6c9616",
      "k6_decision_compiler_verification":"e7a98cd6c9f80c2120f1f53562338cd63e9d1581",
      "decision_quotient":"03baddc27d5ee9dd73656fdd801251e1f4fd8cc6",
      "outcome_order":"d9e732eb7fb17de51f0d92dd72da96977f6e183f",
    }

def test_reclassification_is_not_truth_deletion():
    d=load()
    assert d["relation_to_29_truth_basis"]["truth_obligation_deletion"]==0
    assert d["relation_to_29_truth_basis"]["terminal"] is False
    assert "NO_CLAIM_K6_TERMINAL_REQUIREMENT_IS_DELETED" in d["hard_nonclaims"]

def test_zero_positive_missing_generator_but_one_unresolved_role():
    d=load()
    r=d["reclassification"]
    assert r["current_positive_missing_semantic_generator_count"]==0
    assert r["current_unresolved_semantic_proof_role_count"]==1
    assert r["new_scheduler_label"]=="UNRESOLVED_SEMANTIC_PROOF_AND_INPUT_BINDING_ROLE"

def test_operator_is_not_marked_open():
    d=load()
    op=d["load_split"]["decision_refinement_operator"]
    assert op["classification"]=="VERIFIED_BRAIN_OWNED_BOUNDED_OPERATOR"
    assert op["open_implementation_gap"] is False

def test_capability_reopen_requires_positive_causal_witness():
    d=load()
    req=d["positive_gap_reopen_test"]["all_required"]
    assert any("COMPLETE" in x and "TARGET" in x for x in req)
    assert any("INFORMATION" in x for x in req)
    assert any("CAUSALLY_LOCALIZED" in x for x in req)
    assert "ONLY_THEN" not in d["positive_gap_reopen_test"]
    assert "PROMOTE_ROOT1_POSITIVE_GAP" in d["positive_gap_reopen_test"]["only_then"]

def test_generic_k6_implementation_work_is_disabled():
    d=load()
    disabled=d["scheduler_delta_if_verified"]["disable"]
    assert "GENERIC_K6_MODEL_PORTING" in disabled
    assert "GENERIC_LANGUAGE_OR_VISION_DONOR_HARVEST_FOR_K6" in disabled

def test_zero_credit():
    d=load()
    for k,v in d["accounting"].items():
        if k.endswith("_delta"):
            assert v==0
