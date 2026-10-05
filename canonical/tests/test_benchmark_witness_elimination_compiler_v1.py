from canonical.runtime.benchmark_witness_elimination_compiler_v1 import evaluate_certificate, compile_manifest

def base(ctype):
    return {
        "predicate_id": "X",
        "exact_target_tuple_bound": True,
        "certificate": {"type": ctype, "receipts": ["sha256:abc"]},
    }

def test_threshold_lower_bound_pass():
    x = base("THRESHOLD_LOWER_BOUND")
    x["certificate"].update({"score_decomposition_exact": True, "proved_lower_bound": 0.70, "target_threshold": 0.664, "evaluator_relation_proved": True})
    assert evaluate_certificate(x).admissible

def test_threshold_lower_bound_rejects_insufficient_bound():
    x = base("THRESHOLD_LOWER_BOUND")
    x["certificate"].update({"score_decomposition_exact": True, "proved_lower_bound": 0.60, "target_threshold": 0.664, "evaluator_relation_proved": True})
    assert not evaluate_certificate(x).admissible

def test_task_conditioned_dominance_requires_all_universal_premises():
    x = base("TASK_CONDITIONED_DOMINANCE")
    x["certificate"].update({"domain_subset_proved": True, "evaluator_relation_proved": True, "resource_semantics_preserved": True, "universal_success_proved": True})
    assert evaluate_certificate(x).admissible
    x["certificate"]["domain_subset_proved"] = False
    assert not evaluate_certificate(x).admissible

def test_scope_superset_requires_hidden_scope_upper_bound():
    x = base("SCOPE_SUPERSET")
    x["certificate"].update({"published_contract_upper_bounds_hidden_scope": False, "evaluator_relation_proved": True, "resource_semantics_preserved": True, "universal_success_proved": True, "no_target_outcome_leakage": True})
    assert not evaluate_certificate(x).admissible
    x["certificate"]["published_contract_upper_bounds_hidden_scope"] = True
    assert evaluate_certificate(x).admissible

def test_no_receipt_no_admission():
    x = base("TASK_CONDITIONED_DOMINANCE")
    x["certificate"]["receipts"] = []
    assert not evaluate_certificate(x).admissible

def test_manifest_never_assigns_terminal_credit():
    x = base("TASK_CONDITIONED_DOMINANCE")
    x["certificate"].update({"domain_subset_proved": True, "evaluator_relation_proved": True, "resource_semantics_preserved": True, "universal_success_proved": True})
    out = compile_manifest({"targets":[x]})
    assert out["admitted_count"] == 1
    assert all(v["terminal_credit"] == 0 for v in out["verdicts"])
