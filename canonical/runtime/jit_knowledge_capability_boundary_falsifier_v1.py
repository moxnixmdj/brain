from __future__ import annotations

from typing import Any


def code_data_relabeling_counterexample() -> dict[str, Any]:
    payload = b"if task_kind == 7: return action_A"
    as_data = {"kind": "data", "bytes": payload}
    as_policy_artifact = {"kind": "policy", "bytes": payload}
    return {
        "same_payload": as_data["bytes"] == as_policy_artifact["bytes"],
        "different_labels": as_data["kind"] != as_policy_artifact["kind"],
        "label_only_boundary_representation_invariant": False,
        "causal_role_required": True,
    }


def causal_boundary_contract() -> dict[str, Any]:
    return {
        "knowledge_role": "PROVIDE_TASK_WORLD_PROPOSITIONAL_EVIDENCE",
        "capability_role": "PERFORM_LOAD_BEARING_CROSS_TASK_TRANSFORMATION_SEARCH_DECISION_OR_POLICY_SELECTION",
        "direct_remote_model_inference_is_capability": True,
        "direct_external_policy_execution_is_capability": True,
        "method_description_may_be_knowledge_if_internal_reconstruction_is_load_bearing": True,
        "resource_competitive_reconstruction_required": True,
    }


def compile_boundary_falsification() -> dict[str, Any]:
    witness = code_data_relabeling_counterexample()
    if not witness["same_payload"]:
        return {"status": "FAIL_CLOSED", "reason": "NO_CODE_DATA_WITNESS"}
    return {
        "status": "PASS__LABEL_ONLY_JIT_KNOWLEDGE_BOUNDARY_FALSIFIED",
        "causal_boundary_required": True,
        "repaired_h0": "H0_ZERO_INCREMENTAL_PERSISTENT_CAPABILITY_INFORMATION_V2",
        "next_falsifier": "F_RECONSTRUCTION_RESOURCE_OR_INFORMATION_LOWER_BOUND",
        "terminal_credit": False,
    }
