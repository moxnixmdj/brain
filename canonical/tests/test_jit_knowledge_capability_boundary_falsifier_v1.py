from canonical.runtime.jit_knowledge_capability_boundary_falsifier_v1 import (
    causal_boundary_contract,
    code_data_relabeling_counterexample,
    compile_boundary_falsification,
)


def test_code_data_relabeling_kills_label_only_boundary():
    out = code_data_relabeling_counterexample()
    assert out["same_payload"] is True
    assert out["different_labels"] is True
    assert out["label_only_boundary_representation_invariant"] is False
    assert out["causal_role_required"] is True


def test_causal_boundary_preserves_method_knowledge_but_not_outsourced_execution():
    out = causal_boundary_contract()
    assert out["direct_remote_model_inference_is_capability"] is True
    assert out["direct_external_policy_execution_is_capability"] is True
    assert out["method_description_may_be_knowledge_if_internal_reconstruction_is_load_bearing"] is True
    assert out["resource_competitive_reconstruction_required"] is True


def test_next_falsifier_is_resource_or_information_lower_bound():
    out = compile_boundary_falsification()
    assert out["causal_boundary_required"] is True
    assert out["repaired_h0"] == "H0_ZERO_INCREMENTAL_PERSISTENT_CAPABILITY_INFORMATION_V2"
    assert out["next_falsifier"] == "F_RECONSTRUCTION_RESOURCE_OR_INFORMATION_LOWER_BOUND"
    assert out["terminal_credit"] is False
