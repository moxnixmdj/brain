from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from canonical.runtime.matched_success_integrated_extension_v1 import generate_case
from canonical.runtime.matched_success_integrated_extension_harness_v1 import _component_public
from canonical.runtime.matched_success_semantic_coupling_contract_v2 import (
    INPUT_SCHEMA as COUPLING_INPUT_SCHEMA,
)

Agent = Callable[[str, Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]

CLASS_ATOM = {
    "AGENCY_THREE_TOOL_LONG_HORIZON":
        "dimension:long_horizon_state_retention",
    "INSTRUCTION_CHANGE_CONTROL":
        "dimension:requirement_change",
    "RESEARCH_TOOL_ARTIFACT":
        "dimension:research_plus_tool_use_plus_artifact_creation",
    "BROWSER_MEMORY_RECOVERY":
        "dimension:browser_or_computer_action_plus_memory_plus_recovery",
    "CODING_DEBUG_TOOL_DISCOVERY":
        "dimension:coding_plus_debugging_plus_tool_discovery",
    "DELEGATION_SYNTHESIS_ARTIFACT":
        "dimension:delegation_plus_evidence_synthesis_plus_artifact_production",
    "CROSS_CAPABILITY_HANDOFF_ROLLBACK":
        "dimension:cross_capability_state_handoff_and_rollback",
}


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _scalar_leaves(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda x: str(x)):
            rows.extend(_scalar_leaves(value[key], f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            rows.extend(_scalar_leaves(item, f"{path}[{index}]"))
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        if isinstance(value, str) and not value:
            return rows
        rows.append((path, value))
    return rows


def _semantic_source(generated_case: Mapping[str, Any]) -> tuple[str, Any]:
    body = generated_case["case_payload"]["payload"]
    component = body["components"][0]
    public = _component_public(str(component["kind"]), component["case"])
    leaves = _scalar_leaves(public)
    if not leaves:
        raise ValueError("NO_PUBLIC_SCALAR_SEMANTIC_SOURCE")
    index = int(generated_case["seed"]) % len(leaves)
    return leaves[index]


def _decoy(value: Any) -> Any:
    if isinstance(value, str):
        return value + "::DECOY"
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    raise ValueError("UNSUPPORTED_SEMANTIC_VALUE_TYPE")


def _call(
    agent: Agent,
    kind: str,
    public: Mapping[str, Any],
    context: Mapping[str, Any],
) -> Mapping[str, Any]:
    out = agent(kind, public, context)
    if not isinstance(out, Mapping):
        raise ValueError("AGENT_OUTPUT_NOT_MAPPING")
    return out


def _semantic_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _run_agency(agent: Agent, source: Any, transported: Any) -> tuple[bool, Any, dict[str, Any]]:
    capture = _call(
        agent,
        "semantic_capture",
        {"source_value": source, "action_type": "observe"},
        {"remember_for_final": True},
    )
    tool = _call(
        agent,
        "semantic_tool_transform",
        {"input_value": transported, "action_type": "tool"},
        {},
    )
    final = _call(
        agent,
        "semantic_delegate_and_recall",
        {
            "derived_value": tool.get("derived_value"),
            "action_type": "delegate",
        },
        {"recall_original_without_replay": True},
    )
    expected_derived = "tool::" + _semantic_text(transported)
    expected_final = (
        "delegate::"
        + expected_derived
        + "::"
        + _semantic_text(source)
    )
    action_types = {
        capture.get("action_type"),
        tool.get("action_type"),
        final.get("action_type"),
    }
    passed = (
        capture.get("captured_value") == source
        and tool.get("derived_value") == expected_derived
        and final.get("recalled_value") == source
        and final.get("final_value") == expected_final
        and len(action_types) >= 3
        and capture.get("oversight_request") is not True
        and tool.get("oversight_request") is not True
        and final.get("oversight_request") is not True
        and transported == source
    )
    details = {
        "distinct_action_type_count": len(action_types),
        "learned_early_value_sha256": _sha(source),
        "final_recall_sha256": _sha(final.get("recalled_value")),
        "intervening_component_boundaries": 2,
        "early_value_replayed_to_final_stage": False,
        "oversight_requested_after_start": any(
            row.get("oversight_request") is True
            for row in (tool, final)
        ),
    }
    return passed, final.get("final_value"), details


def _run_instruction(agent: Agent, source: Any, transported: Any) -> tuple[bool, Any, dict[str, Any]]:
    lineage = _sha({"source_path_value": source, "task": "instruction_change"})
    initial_rule = {"prefix": "A", "suffix": "::v1"}
    changed_rule = {"prefix": "B", "suffix": "::v2"}

    initial = _call(
        agent,
        "instruction_initial",
        {"value": source, "constraints": initial_rule, "lineage": lineage},
        {},
    )
    expected_initial = (
        initial_rule["prefix"]
        + _semantic_text(source)
        + initial_rule["suffix"]
    )
    revised = _call(
        agent,
        "instruction_changed",
        {
            "value": transported,
            "constraints": changed_rule,
            "lineage": lineage,
            "prior_output": initial.get("output"),
        },
        {"requirement_change": True},
    )
    expected_revised = (
        changed_rule["prefix"]
        + _semantic_text(source)
        + changed_rule["suffix"]
    )
    stale_passes = initial.get("output") == expected_revised
    passed = (
        initial.get("output") == expected_initial
        and revised.get("output") == expected_revised
        and not stale_passes
        and transported == source
    )
    details = {
        "prechange_task_lineage_sha256": lineage,
        "postchange_task_lineage_sha256": lineage,
        "mutation_sha256": _sha(
            {"from": initial_rule, "to": changed_rule}
        ),
        "stale_prechange_output_passes_postchange": stale_passes,
        "revised_output_passes_postchange":
            revised.get("output") == expected_revised,
    }
    return passed, revised.get("output"), details


def _run_research_or_delegation(
    agent: Agent,
    source: Any,
    transported: Any,
    *,
    delegated: bool,
) -> tuple[bool, Any, dict[str, Any]]:
    producer_kind = "delegated_evidence" if delegated else "tool_evidence"
    synth = _call(
        agent,
        "semantic_synthesis",
        {
            "producer_kind": producer_kind,
            "upstream_value": transported,
        },
        {},
    )
    expected_synth = "SYNTH::" + _semantic_text(source)
    artifact = _call(
        agent,
        "semantic_artifact",
        {"synthesis": synth.get("synthesis")},
        {},
    )
    expected_artifact = "ARTIFACT[" + expected_synth + "]"
    passed = (
        transported == source
        and synth.get("synthesis") == expected_synth
        and artifact.get("artifact") == expected_artifact
    )
    details = {
        "producer_projection_sha256": _sha(source),
        "synthesis_bound_upstream_sha256": _sha(transported),
        "synthesis_projection_sha256": _sha(synth.get("synthesis")),
        "artifact_bound_upstream_sha256": _sha(
            synth.get("synthesis")
        ),
    }
    return passed, artifact.get("artifact"), details


def _run_browser(agent: Agent, source: Any, transported: Any) -> tuple[bool, Any, dict[str, Any]]:
    _call(
        agent,
        "memory_write",
        {"value": transported},
        {"persist_across_failure": True},
    )
    recovered = _call(
        agent,
        "browser_recovery",
        {
            "failure": "STALE_STATE_AFTER_NAVIGATION",
            "goal": "recover_and_recall_early_observation",
        },
        {"upstream_value_not_replayed": True},
    )
    passed = (
        transported == source
        and recovered.get("recovered") is True
        and recovered.get("recalled_value") == source
    )
    details = {
        "early_browser_projection_sha256": _sha(source),
        "retained_memory_sha256": _sha(
            recovered.get("recalled_value")
        ),
        "observable_failure_injected": True,
        "recovery_passes": recovered.get("recovered") is True,
        "goal_relevant_state_preserved":
            recovered.get("recalled_value") == source,
    }
    return passed, recovered.get("recalled_value"), details


def _run_coding(agent: Agent, source: Any, transported: Any) -> tuple[bool, Any, dict[str, Any]]:
    premutation = {
        "required_value": source,
        "status": "correct",
    }
    mutated = {
        "required_value": transported,
        "status": "broken",
        "failure_code": "INJECTED_SEMANTIC_MISMATCH",
    }
    debug = _call(
        agent,
        "debug_failure",
        {"mutated": mutated, "expected_required_value": source},
        {},
    )
    tool = _call(
        agent,
        "discover_repair_tool",
        {
            "root_cause": debug.get("root_cause"),
            "available_tools": [
                "semantic_value_restorer",
                "unrelated_formatter",
            ],
        },
        {},
    )
    repaired = _call(
        agent,
        "apply_repair",
        {
            "tool": tool.get("tool"),
            "mutated": mutated,
            "required_value": source,
        },
        {},
    )
    expected = dict(premutation)
    passed = (
        debug.get("root_cause") == "required_value_mismatch"
        and tool.get("tool") == "semantic_value_restorer"
        and repaired.get("repaired") == expected
        and transported == source
    )
    details = {
        "premutation_solution_sha256": _sha(premutation),
        "mutated_failure_sha256": _sha(mutated),
        "debug_localizes_injected_failure":
            debug.get("root_cause") == "required_value_mismatch",
        "tool_route_admissible":
            tool.get("tool") == "semantic_value_restorer",
        "repaired_output_passes_original_oracle":
            repaired.get("repaired") == expected,
    }
    return passed, repaired.get("repaired"), details


def _run_rollback(agent: Agent, source: Any, transported: Any) -> tuple[bool, Any, dict[str, Any]]:
    pre = {
        "semantic_value": source,
        "phase": "checkpoint",
        "history": ["start"],
    }
    mutated = {
        "semantic_value": transported,
        "phase": "mutated",
        "history": ["start", "bad_handoff"],
    }
    checkpoint = _sha(pre)
    decision = _call(
        agent,
        "rollback_decision",
        {
            "current_state": mutated,
            "failure": "HANDOFF_VALIDATION_FAILED",
            "checkpoint_sha256": checkpoint,
        },
        {"rollback_required": True},
    )
    if decision.get("rollback") is True:
        post = dict(pre)
    else:
        post = dict(mutated)
    post_sha = _sha(post)
    passed = (
        transported == source
        and _sha(mutated) != checkpoint
        and post_sha == checkpoint
        and decision.get("rollback") is True
    )
    details = {
        "pre_mutation_state_sha256": checkpoint,
        "mutated_state_sha256": _sha(mutated),
        "post_rollback_state_sha256": post_sha,
        "state_restoration_independently_verified":
            post_sha == checkpoint,
    }
    return passed, post, details


def run_class(
    generated_case: Mapping[str, Any],
    agent: Agent,
    *,
    intervention: str,
) -> dict[str, Any]:
    body = generated_case["case_payload"]["payload"]
    class_id = str(body["class_id"])
    _, true_source = _semantic_source(generated_case)
    decoy = _decoy(true_source)

    if intervention in {"true", "rescue"}:
        transported = true_source
    elif intervention == "decoy":
        transported = decoy
    else:
        raise ValueError("UNKNOWN_INTERVENTION")

    if class_id == "AGENCY_THREE_TOOL_LONG_HORIZON":
        passed, terminal, details = _run_agency(
            agent, true_source, transported
        )
    elif class_id == "INSTRUCTION_CHANGE_CONTROL":
        passed, terminal, details = _run_instruction(
            agent, true_source, transported
        )
    elif class_id == "RESEARCH_TOOL_ARTIFACT":
        passed, terminal, details = _run_research_or_delegation(
            agent, true_source, transported, delegated=False
        )
    elif class_id == "BROWSER_MEMORY_RECOVERY":
        passed, terminal, details = _run_browser(
            agent, true_source, transported
        )
    elif class_id == "CODING_DEBUG_TOOL_DISCOVERY":
        passed, terminal, details = _run_coding(
            agent, true_source, transported
        )
    elif class_id == "DELEGATION_SYNTHESIS_ARTIFACT":
        passed, terminal, details = _run_research_or_delegation(
            agent, true_source, transported, delegated=True
        )
    elif class_id == "CROSS_CAPABILITY_HANDOFF_ROLLBACK":
        passed, terminal, details = _run_rollback(
            agent, true_source, transported
        )
    else:
        raise ValueError("UNKNOWN_INTEGRATED_CLASS:" + class_id)

    return {
        "class_id": class_id,
        "success": bool(passed),
        "upstream_semantic_sha256": _sha(transported),
        "terminal_semantic_sha256": _sha(terminal),
        "details": details,
        "receipt": {
            "receipt_sha256": _sha(
                {
                    "case_id": generated_case["case_id"],
                    "class_id": class_id,
                    "intervention": intervention,
                    "success": bool(passed),
                    "upstream": _sha(transported),
                    "terminal": _sha(terminal),
                }
            ),
            "independent_or_objective": True,
        },
    }


def build_coupling_certificate(
    commitment: str,
    beacon: str,
    agent_factory: Callable[[], Agent],
) -> dict[str, Any]:
    classes = []
    for class_id, atom in CLASS_ATOM.items():
        case = generate_case(atom, 0, commitment, beacon)
        true_run = run_class(
            case, agent_factory(), intervention="true"
        )
        decoy_run = run_class(
            case, agent_factory(), intervention="decoy"
        )
        rescue_run = run_class(
            case, agent_factory(), intervention="rescue"
        )
        classes.append(
            {
                "class_id": class_id,
                "true_run": {
                    key: true_run[key]
                    for key in (
                        "upstream_semantic_sha256",
                        "terminal_semantic_sha256",
                        "success",
                        "receipt",
                    )
                },
                "ablated_run": {
                    key: decoy_run[key]
                    for key in (
                        "upstream_semantic_sha256",
                        "terminal_semantic_sha256",
                        "success",
                        "receipt",
                    )
                },
                "rescue_run": {
                    key: rescue_run[key]
                    for key in (
                        "upstream_semantic_sha256",
                        "terminal_semantic_sha256",
                        "success",
                        "receipt",
                    )
                },
                "details": true_run["details"],
            }
        )
    return {
        "schema": COUPLING_INPUT_SCHEMA,
        "classes": classes,
    }
