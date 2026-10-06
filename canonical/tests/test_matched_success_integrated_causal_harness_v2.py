from __future__ import annotations

from canonical.runtime.matched_success_integrated_causal_harness_v2 import (
    CLASS_ATOM,
    build_coupling_certificate,
    run_class,
)
from canonical.runtime.matched_success_integrated_extension_v1 import generate_case
from canonical.runtime.matched_success_semantic_coupling_contract_v2 import (
    compile_coupling,
)


class ConnectedAgent:
    def __init__(self):
        self.memory = None

    def __call__(self, kind, public, context):
        if kind == "semantic_capture":
            self.memory = public["source_value"]
            return {
                "captured_value": public["source_value"],
                "action_type": public["action_type"],
                "oversight_request": False,
            }
        if kind == "semantic_tool_transform":
            return {
                "derived_value": "tool::" + _text(public["input_value"]),
                "action_type": public["action_type"],
                "oversight_request": False,
            }
        if kind == "semantic_delegate_and_recall":
            return {
                "recalled_value": self.memory,
                "final_value": (
                    "delegate::"
                    + str(public["derived_value"])
                    + "::"
                    + _text(self.memory)
                ),
                "action_type": public["action_type"],
                "oversight_request": False,
            }
        if kind == "instruction_initial":
            c = public["constraints"]
            return {
                "output": c["prefix"] + _text(public["value"]) + c["suffix"]
            }
        if kind == "instruction_changed":
            c = public["constraints"]
            return {
                "output": c["prefix"] + _text(public["value"]) + c["suffix"]
            }
        if kind == "semantic_synthesis":
            return {
                "synthesis": "SYNTH::" + _text(public["upstream_value"])
            }
        if kind == "semantic_artifact":
            return {
                "artifact": "ARTIFACT[" + str(public["synthesis"]) + "]"
            }
        if kind == "memory_write":
            self.memory = public["value"]
            return {"stored": True}
        if kind == "browser_recovery":
            return {
                "recovered": True,
                "recalled_value": self.memory,
            }
        if kind == "debug_failure":
            expected = public["expected_required_value"]
            actual = public["mutated"]["required_value"]
            return {
                "root_cause": (
                    "required_value_mismatch"
                    if actual != expected
                    else "none"
                )
            }
        if kind == "discover_repair_tool":
            return {
                "tool": (
                    "semantic_value_restorer"
                    if public["root_cause"] == "required_value_mismatch"
                    else "unrelated_formatter"
                )
            }
        if kind == "apply_repair":
            if public["tool"] != "semantic_value_restorer":
                return {"repaired": public["mutated"]}
            return {
                "repaired": {
                    "required_value": public["required_value"],
                    "status": "correct",
                }
            }
        if kind == "rollback_decision":
            return {"rollback": True}
        raise AssertionError(kind)


class DisconnectedAgent(ConnectedAgent):
    def __call__(self, kind, public, context):
        if kind == "semantic_synthesis":
            return {"synthesis": "SYNTH::DISCONNECTED"}
        if kind == "semantic_artifact":
            return {"artifact": "ARTIFACT[SYNTH::DISCONNECTED]"}
        if kind == "memory_write":
            self.memory = "DISCONNECTED"
            return {"stored": True}
        if kind == "semantic_tool_transform":
            return {
                "derived_value": "tool::DISCONNECTED",
                "action_type": public["action_type"],
                "oversight_request": False,
            }
        if kind == "instruction_changed":
            c = public["constraints"]
            return {
                "output": c["prefix"] + "DISCONNECTED" + c["suffix"]
            }
        return super().__call__(kind, public, context)


def _text(value):
    import json
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
    )


def test_connected_agent_generates_valid_interventional_certificate():
    doc = build_coupling_certificate(
        "REHEARSAL_COMMITMENT_V2",
        "REHEARSAL_BEACON_V2",
        ConnectedAgent,
    )
    out = compile_coupling(doc)
    assert out["status"] == "PASS__INTERVENTIONAL_SEMANTIC_COUPLING_CONTRACT"
    assert out["class_count"] == 7


def test_same_shape_decoy_fails_each_integrated_class():
    for class_id, atom in CLASS_ATOM.items():
        case = generate_case(
            atom,
            0,
            "REHEARSAL_COMMITMENT_V2",
            "REHEARSAL_BEACON_V2",
        )
        true_run = run_class(
            case, ConnectedAgent(), intervention="true"
        )
        decoy_run = run_class(
            case, ConnectedAgent(), intervention="decoy"
        )
        rescue_run = run_class(
            case, ConnectedAgent(), intervention="rescue"
        )
        assert true_run["success"] is True, class_id
        assert decoy_run["success"] is False, class_id
        assert rescue_run["success"] is True, class_id
        assert (
            rescue_run["terminal_semantic_sha256"]
            == true_run["terminal_semantic_sha256"]
        ), class_id


def test_disconnected_agent_cannot_certify_all_integrated_classes():
    false_positives = []
    for class_id, atom in CLASS_ATOM.items():
        case = generate_case(
            atom,
            0,
            "REHEARSAL_COMMITMENT_V2",
            "REHEARSAL_BEACON_V2",
        )
        out = run_class(
            case, DisconnectedAgent(), intervention="true"
        )
        if out["success"]:
            false_positives.append(class_id)
    assert false_positives == []


def test_rollback_uses_real_state_digest_restoration():
    atom = CLASS_ATOM["CROSS_CAPABILITY_HANDOFF_ROLLBACK"]
    case = generate_case(
        atom,
        0,
        "REHEARSAL_COMMITMENT_V2",
        "REHEARSAL_BEACON_V2",
    )
    out = run_class(
        case, ConnectedAgent(), intervention="true"
    )
    d = out["details"]
    assert d["pre_mutation_state_sha256"] != d["mutated_state_sha256"]
    assert d["post_rollback_state_sha256"] == d["pre_mutation_state_sha256"]
    assert d["state_restoration_independently_verified"] is True
