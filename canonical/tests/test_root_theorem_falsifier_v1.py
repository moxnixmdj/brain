from canonical.runtime.root_theorem_falsifier_v1 import (
    assess_mechanism_admission,
    classify_false_success,
    evaluate_root_closure,
    exhaustive_boolean_theorem_check,
)


def exact_binding(**overrides):
    value = {
        "claim_id": "a" * 64,
        "scope_sha256": "b" * 64,
        "semantics_sha256": "c" * 64,
        "carrier_schema_id": "CARRIER_V1",
        "mission_id": "MISSION_V1",
        "epoch_id": "E1",
        "canonical_generation": "GEN1",
    }
    value.update(overrides)
    return value


def exact_root_proofs(binding):
    return {
        root: {"status": "PROVED", "binding": dict(binding)}
        for root in ("R1", "R2", "R3")
    }


def false_success_base():
    binding = exact_binding()
    return {
        "terminal_success_claimed": True,
        "real_behavior": True,
        "in_behavior_upper": True,
        "in_good_lower": True,
        "real_good": False,
        "proof_chain_trustworthy": True,
        "root_proofs": exact_root_proofs(binding),
        "expected_binding": binding,
    }


def test_exhaustive_theorem_and_root_minimality():
    out = exhaustive_boolean_theorem_check()
    assert out["theorem_holds"] is True
    assert out["counterexamples_with_R1_R2_R3"] == []
    assert out["each_set_root_load_bearing"] is True
    assert all(out["omission_counterexamples"][r] is not None for r in ("R1", "R2", "R3"))


def test_r1_failure_localized():
    x = false_success_base()
    x["in_behavior_upper"] = False
    out = classify_false_success(x)
    assert out["status"] == "ROOT_FAILURE_WITNESS"
    assert "R1" in out["failed_roots"]


def test_r2_failure_localized():
    x = false_success_base()
    out = classify_false_success(x)
    assert out["status"] == "ROOT_FAILURE_WITNESS"
    assert "R2" in out["failed_roots"]


def test_r3_failure_localized():
    x = false_success_base()
    x["in_good_lower"] = False
    out = classify_false_success(x)
    assert out["status"] == "ROOT_FAILURE_WITNESS"
    assert "R3" in out["failed_roots"]


def test_r4_failure_localized():
    x = false_success_base()
    x["proof_chain_trustworthy"] = False
    out = classify_false_success(x)
    assert out["status"] == "ROOT_FAILURE_WITNESS"
    assert "R4" in out["failed_roots"]


def test_unknown_fails_closed():
    x = false_success_base()
    x["in_behavior_upper"] = "UNKNOWN"
    x["in_good_lower"] = "UNKNOWN"
    out = classify_false_success(x)
    assert out["status"] == "UNKNOWN_FAIL_CLOSED"
    assert out["terminal_credit"] == 0


def test_four_roots_closed_still_grants_zero_credit():
    binding = exact_binding()
    out = evaluate_root_closure({
        "R1": True,
        "R2": True,
        "R3": True,
        "R4": True,
        "root_proofs": exact_root_proofs(binding),
        "expected_binding": binding,
    })
    assert out["status"] == "FOUR_ROOT_PRECONDITIONS_CLOSED"
    assert out["terminal_credit"] == 0


def test_four_roots_without_exact_binding_refine():
    out = evaluate_root_closure({"R1": True, "R2": True, "R3": True, "R4": True})
    assert out["status"] == "REFINE"
    assert out["roots"]["R4"] is None


def test_root_unknown_returns_refine():
    out = evaluate_root_closure({"R1": True, "R2": True, "R3": "UNKNOWN", "R4": True})
    assert out["status"] == "REFINE"
    assert out["terminal_credit"] == 0


def test_redundant_meta_mechanism_rejected():
    out = assess_mechanism_admission({
        "closes_demonstrated_root_gap": False,
        "proof_cost_reduction": 0,
        "trusted_core_delta": 0,
    })
    assert out["status"] == "REJECT_REDUNDANT_META_MECHANISM"


def test_cost_saving_non_tcb_optimization_admitted():
    out = assess_mechanism_admission({
        "closes_demonstrated_root_gap": False,
        "proof_cost_reduction": 10,
        "trusted_core_delta": 0,
    })
    assert out["status"] == "ADMIT_DERIVED_OPTIMIZATION"


def test_tcb_growth_needs_dominance_proof():
    out = assess_mechanism_admission({
        "closes_demonstrated_root_gap": False,
        "proof_cost_reduction": 10,
        "trusted_core_delta": 1,
        "tcb_growth_dominance_proved": False,
    })
    assert out["status"] == "REJECT_PENDING_TCB_DOMINANCE_PROOF"
