from __future__ import annotations

import hashlib
import json

from canonical.runtime.matched_success_integrated_causal_harness_v3 import (
    CLASS_ATOM,
    _scalar_leaves,
    _semantic_source,
    build_v3_bundle,
)
from canonical.runtime.matched_success_integrated_extension_v1 import (
    generate_case,
)
from canonical.runtime.matched_success_public_projection_v1 import (
    public_component,
)
from canonical.runtime.matched_success_semantic_coupling_contract_v3 import (
    compile_coupling_v3,
)


def _text(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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
                "output": (
                    c["prefix"] + _text(public["value"]) + c["suffix"]
                )
            }
        if kind == "instruction_changed":
            c = public["constraints"]
            return {
                "output": (
                    c["prefix"] + _text(public["value"]) + c["suffix"]
                )
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
            return {
                "root_cause": (
                    "required_value_mismatch"
                    if (
                        public["mutated"]["required_value"]
                        != public["expected_required_value"]
                    )
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
        if kind == "semantic_synthesis":
            return {"synthesis": "SYNTH::DISCONNECTED"}
        if kind == "semantic_artifact":
            return {"artifact": "ARTIFACT[SYNTH::DISCONNECTED]"}
        if kind == "memory_write":
            self.memory = "DISCONNECTED"
            return {"stored": True}
        if kind == "debug_failure":
            return {"root_cause": "none"}
        if kind == "rollback_decision":
            return {"rollback": False}
        return super().__call__(kind, public, context)


def _git_blob_sha(text):
    data = text.encode("utf-8")
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _iter_receipts(certificate):
    for row in certificate["classes"]:
        for role in ("true", "ablated", "rescue"):
            yield row[role + "_run"]["receipt"]
        yield row["details_receipt"]


def test_connected_causal_bundle_passes_v3_candidate_compiler():
    bundle = build_v3_bundle(
        "V3_REHEARSAL_COMMITMENT",
        "V3_REHEARSAL_BEACON",
        ConnectedAgent,
    )
    out = compile_coupling_v3(bundle["certificate"])
    assert out["status"] == (
        "PASS__CONTENT_BOUND_INTERVENTIONAL_SEMANTIC_COUPLING_V3"
    )
    assert out["class_count"] == 7
    assert out["independent_receipt_bytes_verified"] is False
    assert bundle["terminal_case_generation"] is False
    assert bundle["fresh_reality_consumed"] == 0


def test_every_v3_receipt_ref_matches_exact_emitted_bytes():
    bundle = build_v3_bundle(
        "V3_REHEARSAL_COMMITMENT",
        "V3_REHEARSAL_BEACON",
        ConnectedAgent,
    )
    docs = bundle["receipt_documents"]
    assert len(docs) == 28
    for receipt in _iter_receipts(bundle["certificate"]):
        text = docs[receipt["path"]]
        assert _git_blob_sha(text) == receipt["git_blob_sha"]
        body = json.loads(text)
        for key, value in body.items():
            assert receipt[key] == value
        assert body["independent_or_objective"] is True


def test_disconnected_semantics_cannot_produce_v3_pass():
    bundle = build_v3_bundle(
        "V3_DISCONNECTED_COMMITMENT",
        "V3_DISCONNECTED_BEACON",
        DisconnectedAgent,
    )
    out = compile_coupling_v3(bundle["certificate"])
    assert out["status"] == "FAIL_CLOSED"


def test_same_shape_ablation_is_semantically_distinct_for_every_class():
    bundle = build_v3_bundle(
        "V3_REHEARSAL_COMMITMENT",
        "V3_REHEARSAL_BEACON",
        ConnectedAgent,
    )
    for row in bundle["certificate"]["classes"]:
        true = row["true_run"]
        ablated = row["ablated_run"]
        rescue = row["rescue_run"]
        assert true["upstream_shape_sha256"] == ablated["upstream_shape_sha256"]
        assert true["upstream_shape_sha256"] == rescue["upstream_shape_sha256"]
        assert true["upstream_semantic_sha256"] != ablated["upstream_semantic_sha256"]
        assert true["upstream_semantic_sha256"] == rescue["upstream_semantic_sha256"]
        assert true["success"] is True
        assert ablated["success"] is False
        assert rescue["success"] is True
        assert true["terminal_semantic_sha256"] != ablated["terminal_semantic_sha256"]
        assert true["terminal_semantic_sha256"] == rescue["terminal_semantic_sha256"]


def test_semantic_source_uses_public_projection_not_raw_case_fields():
    atom = CLASS_ATOM["RESEARCH_TOOL_ARTIFACT"]
    case = generate_case(
        atom,
        0,
        "PUBLIC_ONLY_COMMITMENT",
        "PUBLIC_ONLY_BEACON",
    )
    first = case["case_payload"]["payload"]["components"][0]
    first["case"]["HIDDEN_SENTINEL_DO_NOT_USE"] = "SECRET_ORACLE_VALUE"
    public = public_component(first)
    public_values = [value for _, value in _scalar_leaves(public)]
    assert "SECRET_ORACLE_VALUE" not in public_values
    source = _semantic_source(case)
    assert source in public_values
    assert source != "SECRET_ORACLE_VALUE"
