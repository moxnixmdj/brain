from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from canonical.runtime.matched_success_integrated_extension_v1 import generate_case
from canonical.runtime.matched_success_semantic_coupling_contract_v3 import (
    INPUT_SCHEMA as V3_INPUT_SCHEMA,
)
from canonical.runtime.matched_success_public_projection_v1 import public_component

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


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _receipt(
    *,
    path: str,
    binding: Mapping[str, Any],
    documents: dict[str, str],
) -> dict[str, Any]:
    body = {
        **dict(binding),
        "independent_or_objective": True,
        "receipt_kind": "OBJECTIVE_DETERMINISTIC_SEMANTIC_HARNESS_V3",
    }
    data = _canon(body) + b"\n"
    documents[path] = data.decode("utf-8")
    return {
        "path": path,
        "git_blob_sha": _git_blob_sha(data),
        **body,
    }


def _shape_descriptor(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _shape_descriptor(value[key])
            for key in sorted(value, key=lambda x: str(x))
        }
    if isinstance(value, (list, tuple)):
        return [_shape_descriptor(item) for item in value]
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, str):
        return {"type": "str"}
    if isinstance(value, int):
        return {"type": "int"}
    if isinstance(value, float):
        return {"type": "float"}
    if value is None:
        return {"type": "null"}
    return {"type": type(value).__name__}


def _shape_sha(value: Any) -> str:
    return _digest(_shape_descriptor(value))


def _scalar_leaves(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda x: str(x)):
            rows.extend(_scalar_leaves(value[key], f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            rows.extend(_scalar_leaves(item, f"{path}[{index}]"))
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        if not (isinstance(value, str) and not value):
            rows.append((path, value))
    return rows


def _semantic_source(generated_case: Mapping[str, Any]) -> Any:
    body = generated_case["case_payload"]["payload"]
    first_component = body["components"][0]
    public = public_component(first_component)
    leaves = _scalar_leaves(public)
    if not leaves:
        raise ValueError("NO_SCALAR_SEMANTIC_SOURCE")
    index = int(generated_case["seed"]) % len(leaves)
    return leaves[index][1]


def _decoy(value: Any) -> Any:
    if isinstance(value, str):
        return value + "::DECOY"
    if isinstance(value, int) and not isinstance(value, bool):
        return value + 1
    if isinstance(value, float):
        return value + 1.0
    raise ValueError("UNSUPPORTED_SEMANTIC_VALUE_TYPE")


def _text(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _upstream_object(class_id: str, value: Any) -> Any:
    if class_id == "CODING_DEBUG_TOOL_DISCOVERY":
        return {"required_value": value, "status": "correct"}
    if class_id == "CROSS_CAPABILITY_HANDOFF_ROLLBACK":
        return {
            "semantic_value": value,
            "phase": "checkpoint",
            "history": ["start"],
        }
    return value


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


def _agency(
    agent: Agent,
    expected: Any,
    transported: Any,
) -> tuple[bool, Any, dict[str, Any]]:
    capture = _call(
        agent,
        "semantic_capture",
        {"source_value": transported, "action_type": "observe"},
        {"remember_for_final": True},
    )
    middle = _call(
        agent,
        "semantic_tool_transform",
        {"input_value": transported, "action_type": "tool"},
        {},
    )
    final = _call(
        agent,
        "semantic_delegate_and_recall",
        {
            "derived_value": middle.get("derived_value"),
            "action_type": "delegate",
        },
        {"recall_original_without_replay": True},
    )
    expected_middle = "tool::" + _text(expected)
    expected_terminal = (
        "delegate::" + expected_middle + "::" + _text(expected)
    )
    action_types = {
        capture.get("action_type"),
        middle.get("action_type"),
        final.get("action_type"),
    }
    terminal = final.get("final_value")
    passed = (
        capture.get("captured_value") == expected
        and middle.get("derived_value") == expected_middle
        and final.get("recalled_value") == expected
        and terminal == expected_terminal
        and len(action_types) >= 3
        and not any(
            row.get("oversight_request") is True
            for row in (capture, middle, final)
        )
    )
    details = {
        "distinct_action_type_count": len(action_types),
        "learned_early_value_sha256": _digest(expected),
        "final_recall_sha256": _digest(final.get("recalled_value")),
        "intervening_component_boundaries": 2,
        "early_value_replayed_to_final_stage": False,
        "oversight_requested_after_start": any(
            row.get("oversight_request") is True
            for row in (middle, final)
        ),
    }
    return passed, terminal, details


def _instruction(
    agent: Agent,
    expected: Any,
    transported: Any,
    lineage: str,
) -> tuple[bool, Any, dict[str, Any]]:
    initial_rule = {"prefix": "A", "suffix": "::v1"}
    changed_rule = {"prefix": "B", "suffix": "::v2"}
    initial = _call(
        agent,
        "instruction_initial",
        {
            "value": transported,
            "constraints": initial_rule,
            "lineage": lineage,
        },
        {},
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
    expected_initial = (
        initial_rule["prefix"] + _text(expected) + initial_rule["suffix"]
    )
    expected_terminal = (
        changed_rule["prefix"] + _text(expected) + changed_rule["suffix"]
    )
    stale_passes = initial.get("output") == expected_terminal
    terminal = revised.get("output")
    passed = (
        initial.get("output") == expected_initial
        and terminal == expected_terminal
        and stale_passes is False
    )
    details = {
        "prechange_semantic_sha256": _digest(expected),
        "prechange_task_lineage_sha256": lineage,
        "postchange_task_lineage_sha256": lineage,
        "mutation_sha256": _digest(
            {"from": initial_rule, "to": changed_rule}
        ),
        "revised_output_semantic_sha256": _digest(terminal),
        "stale_prechange_output_passes_postchange": stale_passes,
        "revised_output_passes_postchange":
            terminal == expected_terminal,
    }
    return passed, terminal, details


def _synthesis_artifact(
    agent: Agent,
    expected: Any,
    transported: Any,
    *,
    delegated: bool,
) -> tuple[bool, Any, dict[str, Any]]:
    synth = _call(
        agent,
        "semantic_synthesis",
        {
            "producer_kind": (
                "delegated_evidence" if delegated else "tool_evidence"
            ),
            "upstream_value": transported,
        },
        {},
    )
    artifact = _call(
        agent,
        "semantic_artifact",
        {"synthesis": synth.get("synthesis")},
        {},
    )
    expected_synthesis = "SYNTH::" + _text(expected)
    expected_terminal = "ARTIFACT[" + expected_synthesis + "]"
    terminal = artifact.get("artifact")
    passed = (
        synth.get("synthesis") == expected_synthesis
        and terminal == expected_terminal
    )
    details = {
        "producer_projection_sha256": _digest(expected),
        "synthesis_bound_upstream_sha256": _digest(transported),
        "synthesis_projection_sha256": _digest(
            synth.get("synthesis")
        ),
        "artifact_bound_upstream_sha256": _digest(
            synth.get("synthesis")
        ),
        "artifact_semantic_sha256": _digest(terminal),
    }
    return passed, terminal, details


def _browser_memory(
    agent: Agent,
    expected: Any,
    transported: Any,
) -> tuple[bool, Any, dict[str, Any]]:
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
    terminal = recovered.get("recalled_value")
    passed = (
        recovered.get("recovered") is True
        and terminal == expected
    )
    details = {
        "early_browser_projection_sha256": _digest(expected),
        "retained_memory_sha256": _digest(terminal),
        "recovered_state_semantic_sha256": _digest(terminal),
        "observable_failure_injected": True,
        "recovery_passes": recovered.get("recovered") is True,
        "goal_relevant_state_preserved": terminal == expected,
    }
    return passed, terminal, details


def _coding(
    agent: Agent,
    expected_upstream: Mapping[str, Any],
    transported_upstream: Mapping[str, Any],
) -> tuple[bool, Any, dict[str, Any]]:
    mutated = {
        "required_value": _decoy(
            transported_upstream["required_value"]
        ),
        "status": "broken",
        "failure_code": "INJECTED_SEMANTIC_MISMATCH",
    }
    debug = _call(
        agent,
        "debug_failure",
        {
            "mutated": mutated,
            "expected_required_value":
                transported_upstream["required_value"],
        },
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
            "required_value":
                transported_upstream["required_value"],
        },
        {},
    ).get("repaired")
    terminal = repaired
    passed = (
        debug.get("root_cause") == "required_value_mismatch"
        and tool.get("tool") == "semantic_value_restorer"
        and repaired == expected_upstream
    )
    details = {
        "premutation_solution_sha256": _digest(expected_upstream),
        "mutated_failure_sha256": _digest(mutated),
        "repaired_output_semantic_sha256": _digest(terminal),
        "debug_localizes_injected_failure":
            debug.get("root_cause") == "required_value_mismatch",
        "tool_route_admissible":
            tool.get("tool") == "semantic_value_restorer",
        "repaired_output_passes_original_oracle":
            repaired == expected_upstream,
    }
    return passed, terminal, details


def _rollback(
    agent: Agent,
    expected_upstream: Mapping[str, Any],
    transported_upstream: Mapping[str, Any],
) -> tuple[bool, Any, dict[str, Any]]:
    mutated = {
        **dict(transported_upstream),
        "phase": "mutated",
        "history": ["start", "bad_handoff"],
    }
    checkpoint_sha = _digest(transported_upstream)
    decision = _call(
        agent,
        "rollback_decision",
        {
            "current_state": mutated,
            "failure": "HANDOFF_VALIDATION_FAILED",
            "checkpoint_sha256": checkpoint_sha,
        },
        {"rollback_required": True},
    )
    terminal = (
        dict(transported_upstream)
        if decision.get("rollback") is True
        else mutated
    )
    passed = (
        decision.get("rollback") is True
        and terminal == expected_upstream
    )
    details = {
        "pre_mutation_state_sha256": _digest(expected_upstream),
        "mutated_state_sha256": _digest(mutated),
        "post_rollback_state_sha256": _digest(terminal),
        "state_restoration_independently_verified":
            terminal == expected_upstream,
    }
    return passed, terminal, details


def _run(
    generated_case: Mapping[str, Any],
    agent: Agent,
    *,
    role: str,
) -> dict[str, Any]:
    body = generated_case["case_payload"]["payload"]
    class_id = str(body["class_id"])
    source = _semantic_source(generated_case)
    transported_source = (
        _decoy(source) if role == "ablated" else source
    )
    expected_upstream = _upstream_object(class_id, source)
    transported_upstream = _upstream_object(
        class_id, transported_source
    )

    if class_id == "AGENCY_THREE_TOOL_LONG_HORIZON":
        success, terminal, details = _agency(
            agent, source, transported_source
        )
    elif class_id == "INSTRUCTION_CHANGE_CONTROL":
        lineage = _digest(
            {
                "case_id": generated_case["case_id"],
                "task": "instruction_change",
            }
        )
        success, terminal, details = _instruction(
            agent, source, transported_source, lineage
        )
    elif class_id == "RESEARCH_TOOL_ARTIFACT":
        success, terminal, details = _synthesis_artifact(
            agent, source, transported_source, delegated=False
        )
    elif class_id == "BROWSER_MEMORY_RECOVERY":
        success, terminal, details = _browser_memory(
            agent, source, transported_source
        )
    elif class_id == "CODING_DEBUG_TOOL_DISCOVERY":
        success, terminal, details = _coding(
            agent, expected_upstream, transported_upstream
        )
    elif class_id == "DELEGATION_SYNTHESIS_ARTIFACT":
        success, terminal, details = _synthesis_artifact(
            agent, source, transported_source, delegated=True
        )
    elif class_id == "CROSS_CAPABILITY_HANDOFF_ROLLBACK":
        success, terminal, details = _rollback(
            agent, expected_upstream, transported_upstream
        )
    else:
        raise ValueError("UNKNOWN_INTEGRATED_CLASS:" + class_id)

    return {
        "class_id": class_id,
        "run_role": role,
        "upstream_object": transported_upstream,
        "upstream_semantic_sha256": _digest(transported_upstream),
        "upstream_shape_sha256": _shape_sha(transported_upstream),
        "terminal_object": terminal,
        "terminal_semantic_sha256": _digest(terminal),
        "success": bool(success),
        "details": details,
    }


def build_v3_bundle(
    commitment: str,
    beacon: str,
    agent_factory: Callable[[], Agent],
) -> dict[str, Any]:
    documents: dict[str, str] = {}
    classes = []

    for class_id, atom in CLASS_ATOM.items():
        case = generate_case(atom, 0, commitment, beacon)
        runs = {
            role: _run(case, agent_factory(), role=role)
            for role in ("true", "ablated", "rescue")
        }

        row: dict[str, Any] = {"class_id": class_id}
        for role in ("true", "ablated", "rescue"):
            run = runs[role]
            semantic_record = {
                "class_id": class_id,
                "run_role": role,
                "upstream_semantic_sha256":
                    run["upstream_semantic_sha256"],
                "upstream_shape_sha256":
                    run["upstream_shape_sha256"],
                "terminal_semantic_sha256":
                    run["terminal_semantic_sha256"],
                "success": run["success"],
            }
            run_sha = _digest(semantic_record)
            binding = {
                "class_id": class_id,
                "run_role": role,
                "run_semantics_sha256": run_sha,
                "upstream_semantic_sha256":
                    run["upstream_semantic_sha256"],
                "terminal_semantic_sha256":
                    run["terminal_semantic_sha256"],
                "success": run["success"],
            }
            path = (
                "generated/verification/matched_success/"
                + class_id
                + "/"
                + role
                + ".json"
            )
            row[role + "_run"] = {
                **semantic_record,
                "run_semantics_sha256": run_sha,
                "receipt": _receipt(
                    path=path,
                    binding=binding,
                    documents=documents,
                ),
            }

        details = runs["true"]["details"]
        details_sha = _digest(details)
        details_path = (
            "generated/verification/matched_success/"
            + class_id
            + "/details.json"
        )
        row["details"] = details
        row["details_sha256"] = details_sha
        row["details_receipt"] = _receipt(
            path=details_path,
            binding={
                "class_id": class_id,
                "details_sha256": details_sha,
            },
            documents=documents,
        )
        classes.append(row)

    return {
        "certificate": {
            "schema": V3_INPUT_SCHEMA,
            "classes": classes,
        },
        "receipt_documents": documents,
        "terminal_case_generation": False,
        "fresh_reality_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
