from canonical.runtime.benchmark_witness_elimination_compiler_v3 import evaluate_certificate, compile_manifest

SHA="1"*40
BIND={"path":"canonical/governance/target.json","git_blob_sha":SHA}
RECEIPT={"path":"canonical/verification/evidence.json","git_blob_sha":SHA}

def relation(evidence_class="EXACT_FROZEN_TARGET_HARNESS"):
    return {
        "status":"PROVED_EXACT",
        "relation_type":"EXACT_IDENTITY",
        "target_scope":"FROZEN_TARGET_EVALUATOR_HARNESS_FALLBACK",
        "evidence_class":evidence_class,
        "target_tuple_binding":dict(BIND),
        "receipts":[dict(RECEIPT)],
    }

def proof(claim_id, scope, *, claim_value=None, target_value=None, evidence_class="DETERMINISTIC_FORMAL_PROOF"):
    out={
        "claim_id":claim_id,
        "status":"PROVED_EXACT",
        "proof_type":"DETERMINISTIC_DERIVATION",
        "target_scope":scope,
        "evidence_class":evidence_class,
        "target_tuple_binding":dict(BIND),
        "receipts":[dict(RECEIPT)],
    }
    if claim_value is not None:
        out["claim_value"]=claim_value
    if target_value is not None:
        out["target_value"]=target_value
    return out

def base(ctype):
    return {
        "predicate_id":"X",
        "exact_target_tuple_bound":True,
        "target_tuple_binding":dict(BIND),
        "certificate":{
            "type":ctype,
            "receipts":[dict(RECEIPT)],
            "evaluator_relation":relation(),
            "premise_proofs":{},
        },
    }

def threshold():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"]["proved_lower_bound"]=0.70
    x["certificate"]["target_threshold"]=0.664
    x["certificate"]["premise_proofs"]={
        "SCORE_DECOMPOSITION_EXACT":proof("SCORE_DECOMPOSITION_EXACT","FROZEN_TARGET_SCORING_RULE"),
        "LOWER_BOUND_GE_TARGET":proof("LOWER_BOUND_GE_TARGET","FROZEN_TARGET_SCORE_THRESHOLD",claim_value=0.70,target_value=0.664),
    }
    return x

def dominance():
    x=base("TASK_CONDITIONED_DOMINANCE")
    x["certificate"]["premise_proofs"]={
        "DOMAIN_SUBSET":proof("DOMAIN_SUBSET","FROZEN_TARGET_TASK_DOMAIN"),
        "RESOURCE_SEMANTICS":proof("RESOURCE_SEMANTICS","FROZEN_TARGET_RESOURCE_SEMANTICS"),
        "UNIVERSAL_SUCCESS":proof("UNIVERSAL_SUCCESS","CERTIFICATE_CLAIM_DOMAIN"),
    }
    return x

def superset():
    x=base("SCOPE_SUPERSET")
    x["certificate"]["premise_proofs"]={
        "HIDDEN_SCOPE_UPPER_BOUND":proof("HIDDEN_SCOPE_UPPER_BOUND","FROZEN_HIDDEN_TARGET_SCOPE"),
        "RESOURCE_SEMANTICS":proof("RESOURCE_SEMANTICS","FROZEN_TARGET_RESOURCE_SEMANTICS"),
        "UNIVERSAL_SUCCESS":proof("UNIVERSAL_SUCCESS","CERTIFICATE_CLAIM_DOMAIN"),
        "NO_TARGET_OUTCOME_LEAKAGE":proof("NO_TARGET_OUTCOME_LEAKAGE","CERTIFICATE_EVIDENCE_PROVENANCE",evidence_class="PROVENANCE_AUDIT"),
    }
    return x

def test_v2_threshold_bare_boolean_shortcut_rejected():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"].update({
        "score_decomposition_exact":True,
        "proved_lower_bound":0.70,
        "target_threshold":0.664,
    })
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason.startswith("PREMISE_PROOF_OBJECT_MISSING:")

def test_threshold_requires_score_decomposition_proof():
    x=threshold()
    del x["certificate"]["premise_proofs"]["SCORE_DECOMPOSITION_EXACT"]
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="PREMISE_PROOF_OBJECT_MISSING:SCORE_DECOMPOSITION_EXACT"

def test_threshold_requires_lower_bound_proof():
    x=threshold()
    del x["certificate"]["premise_proofs"]["LOWER_BOUND_GE_TARGET"]
    assert not evaluate_certificate(x).admissible

def test_threshold_rejects_lower_bound_claim_value_mismatch():
    x=threshold()
    x["certificate"]["premise_proofs"]["LOWER_BOUND_GE_TARGET"]["claim_value"]=0.71
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="LOWER_BOUND_PROOF_VALUE_MISMATCH"

def test_threshold_rejects_target_value_mismatch():
    x=threshold()
    x["certificate"]["premise_proofs"]["LOWER_BOUND_GE_TARGET"]["target_value"]=0.65
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="LOWER_BOUND_PROOF_TARGET_MISMATCH"

def test_threshold_rejects_insufficient_numeric_bound_even_with_proof():
    x=threshold()
    x["certificate"]["proved_lower_bound"]=0.60
    x["certificate"]["premise_proofs"]["LOWER_BOUND_GE_TARGET"]["claim_value"]=0.60
    assert not evaluate_certificate(x).admissible

def test_threshold_fully_proof_carrying_passes():
    assert evaluate_certificate(threshold()).admissible

def test_v2_dominance_bare_boolean_shortcut_rejected():
    x=base("TASK_CONDITIONED_DOMINANCE")
    x["certificate"].update({
        "domain_subset_proved":True,
        "resource_semantics_preserved":True,
        "universal_success_proved":True,
    })
    assert not evaluate_certificate(x).admissible

def test_dominance_requires_domain_subset_proof():
    x=dominance()
    del x["certificate"]["premise_proofs"]["DOMAIN_SUBSET"]
    assert not evaluate_certificate(x).admissible

def test_dominance_rejects_wrong_scope():
    x=dominance()
    x["certificate"]["premise_proofs"]["RESOURCE_SEMANTICS"]["target_scope"]="GENERIC_CARRIER"
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="PREMISE_PROOF_TARGET_SCOPE_MISMATCH:RESOURCE_SEMANTICS"

def test_dominance_fully_proof_carrying_passes():
    assert evaluate_certificate(dominance()).admissible

def test_v2_scope_superset_bare_boolean_shortcut_rejected():
    x=base("SCOPE_SUPERSET")
    x["certificate"].update({
        "published_contract_upper_bounds_hidden_scope":True,
        "resource_semantics_preserved":True,
        "universal_success_proved":True,
        "no_target_outcome_leakage":True,
    })
    assert not evaluate_certificate(x).admissible

def test_scope_superset_requires_no_leakage_proof():
    x=superset()
    del x["certificate"]["premise_proofs"]["NO_TARGET_OUTCOME_LEAKAGE"]
    assert not evaluate_certificate(x).admissible

def test_scope_superset_fully_proof_carrying_passes():
    assert evaluate_certificate(superset()).admissible

def test_premise_proof_receipts_must_be_content_addressed():
    x=dominance()
    x["certificate"]["premise_proofs"]["DOMAIN_SUBSET"]["receipts"]=["sha256:abc"]
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="PREMISE_PROOF_RECEIPTS_NOT_CONTENT_ADDRESSED:DOMAIN_SUBSET"

def test_premise_target_binding_must_match_certificate_target():
    x=dominance()
    x["certificate"]["premise_proofs"]["DOMAIN_SUBSET"]["target_tuple_binding"]={
        "path":"canonical/governance/other.json",
        "git_blob_sha":SHA,
    }
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="PREMISE_PROOF_TARGET_BINDING_MISMATCH:DOMAIN_SUBSET"

def test_forbidden_generic_protocol_premise_evidence_rejected():
    x=dominance()
    x["certificate"]["premise_proofs"]["RESOURCE_SEMANTICS"]["evidence_class"]="GENERIC_PROTOCOL_ONLY"
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="PREMISE_PROOF_FORBIDDEN_SUBSTITUTE_EVIDENCE:RESOURCE_SEMANTICS"

def test_v2_evaluator_relation_hardening_preserved():
    x=threshold()
    x["certificate"]["evaluator_relation"]=relation("PUBLIC_LEADERBOARD_CALIBRATION")
    assert not evaluate_certificate(x).admissible

def test_certificate_receipts_must_be_content_addressed():
    x=threshold()
    x["certificate"]["receipts"]=["sha256:abc"]
    assert not evaluate_certificate(x).admissible

def test_manifest_never_assigns_terminal_credit():
    out=compile_manifest({"targets":[threshold(),dominance(),superset()]})
    assert out["admitted_count"]==3
    assert all(v["terminal_credit"]==0 for v in out["verdicts"])
