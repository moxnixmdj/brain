from canonical.runtime.composition_component_scoped_proof_necessity_falsifier_v1 import (
    compile_necessity_falsifier,
    composition_countermodel,
)


def test_composition_can_match_while_one_internal_component_is_isolated_inferior():
    out = composition_countermodel()
    assert out["isolated_component_brain_noninferior"] is False
    assert out["composition_parity_holds"] is True
    assert out["terminal_distribution_equal"] is True
    assert out["hard_constraints_equal_and_pass"] is True


def test_truth_repair_preserves_other_obligations():
    out = compile_necessity_falsifier()
    assert out["status"].startswith("PASS__")
    assert out["countermodel_valid"] is True
    assert out["candidate_deleted_obligation"] == "COMPOSITION_COMPONENT_SCOPED_PROOFS"
    assert out["preserve_separate_component_capability_obligations"] is True
    assert out["preserve_composition_success_and_invariant_obligations"] is True
    assert out["terminal_credit"] is False
