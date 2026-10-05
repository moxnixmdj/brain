from canonical.runtime.benchmark_witness_elimination_compiler_v2 import evaluate_certificate, compile_manifest

SHA="1"*40
BIND={"path":"canonical/governance/target.json","git_blob_sha":SHA}
RECEIPT={"path":"canonical/verification/evidence.json","git_blob_sha":SHA}

def exact_relation(evidence_class="EXACT_FROZEN_TARGET_HARNESS"):
    return {
        "status":"PROVED_EXACT",
        "relation_type":"EXACT_IDENTITY",
        "target_scope":"FROZEN_TARGET_EVALUATOR_HARNESS_FALLBACK",
        "evidence_class":evidence_class,
        "target_tuple_binding":dict(BIND),
        "receipts":[dict(RECEIPT)],
    }

def base(ctype):
    return {
        "predicate_id":"X",
        "exact_target_tuple_bound":True,
        "target_tuple_binding":dict(BIND),
        "certificate":{
            "type":ctype,
            "receipts":[dict(RECEIPT)],
            "evaluator_relation":exact_relation(),
        },
    }

def test_legacy_bare_boolean_rejected():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"].pop("evaluator_relation")
    x["certificate"]["evaluator_relation_proved"]=True
    x["certificate"].update({"score_decomposition_exact":True,"proved_lower_bound":0.70,"target_threshold":0.664})
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="EVALUATOR_RELATION_OBJECT_MISSING"

def test_generic_protocol_cannot_substitute_for_evaluator_relation():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"]["evaluator_relation"]=exact_relation("GENERIC_PROTOCOL_ONLY")
    x["certificate"].update({"score_decomposition_exact":True,"proved_lower_bound":0.70,"target_threshold":0.664})
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="EVALUATOR_RELATION_FORBIDDEN_SUBSTITUTE_EVIDENCE"

def test_public_calibration_cannot_substitute_for_evaluator_relation():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"]["evaluator_relation"]=exact_relation("PUBLIC_LEADERBOARD_CALIBRATION")
    x["certificate"].update({"score_decomposition_exact":True,"proved_lower_bound":0.70,"target_threshold":0.664})
    assert not evaluate_certificate(x).admissible

def test_relation_receipts_must_be_content_addressed():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"]["evaluator_relation"]["receipts"]=["sha256:abc"]
    x["certificate"].update({"score_decomposition_exact":True,"proved_lower_bound":0.70,"target_threshold":0.664})
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="EVALUATOR_RELATION_RECEIPTS_NOT_CONTENT_ADDRESSED"

def test_certificate_receipts_must_be_content_addressed():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"]["receipts"]=["sha256:abc"]
    x["certificate"].update({"score_decomposition_exact":True,"proved_lower_bound":0.70,"target_threshold":0.664})
    out=evaluate_certificate(x)
    assert not out.admissible
    assert out.reason=="CERTIFICATE_RECEIPTS_NOT_CONTENT_ADDRESSED"

def test_threshold_lower_bound_passes_with_proof_carrying_relation():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"].update({"score_decomposition_exact":True,"proved_lower_bound":0.70,"target_threshold":0.664})
    assert evaluate_certificate(x).admissible

def test_threshold_lower_bound_rejects_insufficient_bound():
    x=base("THRESHOLD_LOWER_BOUND")
    x["certificate"].update({"score_decomposition_exact":True,"proved_lower_bound":0.60,"target_threshold":0.664})
    assert not evaluate_certificate(x).admissible

def test_task_conditioned_dominance_requires_other_universal_premises():
    x=base("TASK_CONDITIONED_DOMINANCE")
    x["certificate"].update({"domain_subset_proved":True,"resource_semantics_preserved":True,"universal_success_proved":True})
    assert evaluate_certificate(x).admissible
    x["certificate"]["domain_subset_proved"]=False
    assert not evaluate_certificate(x).admissible

def test_scope_superset_requires_hidden_scope_upper_bound():
    x=base("SCOPE_SUPERSET")
    x["certificate"].update({"published_contract_upper_bounds_hidden_scope":False,"resource_semantics_preserved":True,"universal_success_proved":True,"no_target_outcome_leakage":True})
    assert not evaluate_certificate(x).admissible
    x["certificate"]["published_contract_upper_bounds_hidden_scope"]=True
    assert evaluate_certificate(x).admissible

def test_manifest_never_assigns_terminal_credit():
    x=base("TASK_CONDITIONED_DOMINANCE")
    x["certificate"].update({"domain_subset_proved":True,"resource_semantics_preserved":True,"universal_success_proved":True})
    out=compile_manifest({"targets":[x]})
    assert out["admitted_count"]==1
    assert all(v["terminal_credit"]==0 for v in out["verdicts"])
