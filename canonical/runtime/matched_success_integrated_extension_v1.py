from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import browser_state_information_safe_proof as browser
from canonical.runtime import delegation_structural_variety_proof_v3 as delegation_v3
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_v2
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as m0
from canonical.runtime import contract_native_proof_suites as contract
from canonical.runtime import native_artifact_cross_format_proof_v1 as native
from canonical.runtime.matched_success_scope_compiler_v1 import INPUT_SCHEMA as SCOPE_SCHEMA

VERSION = "MATCHED_SUCCESS_INTEGRATED_EXTENSION_V1"
REPETITIONS = 4

TARGET_BY_ATOM = {
    "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "dimension:state_change_after_actions_requiring_replanning": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "dimension:long_horizon_state_retention": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "dimension:tool_failure_and_recovery": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "dimension:subtask_dependency_and_fan_in": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "dimension:minimal_oversight_completion": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "dimension:multi_constraint_instruction_compliance": "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "dimension:authorization_and_scope_boundaries": "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "dimension:routine_ambiguity": "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "dimension:requirement_change": "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "dimension:explicit_abstention_and_fail_closed_cases": "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "dimension:research_plus_tool_use_plus_artifact_creation": "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "dimension:browser_or_computer_action_plus_memory_plus_recovery": "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "dimension:coding_plus_debugging_plus_tool_discovery": "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "dimension:delegation_plus_evidence_synthesis_plus_artifact_production": "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
    "dimension:cross_capability_state_handoff_and_rollback": "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

LEGACY_ROUTE = {
    "dimension:state_change_after_actions_requiring_replanning": "browser",
    "dimension:tool_failure_and_recovery": "browser",
    "dimension:subtask_dependency_and_fan_in": "delegation_v3",
    "dimension:authorization_and_scope_boundaries": "tool",
    "dimension:routine_ambiguity": "browser",
    "dimension:explicit_abstention_and_fail_closed_cases": "tool",
}

INTEGRATED_CLASS = {
    "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types": "AGENCY_THREE_TOOL_LONG_HORIZON",
    "dimension:long_horizon_state_retention": "AGENCY_THREE_TOOL_LONG_HORIZON",
    "dimension:minimal_oversight_completion": "AGENCY_THREE_TOOL_LONG_HORIZON",
    "dimension:multi_constraint_instruction_compliance": "INSTRUCTION_CHANGE_CONTROL",
    "dimension:requirement_change": "INSTRUCTION_CHANGE_CONTROL",
    "dimension:research_plus_tool_use_plus_artifact_creation": "RESEARCH_TOOL_ARTIFACT",
    "dimension:browser_or_computer_action_plus_memory_plus_recovery": "BROWSER_MEMORY_RECOVERY",
    "dimension:coding_plus_debugging_plus_tool_discovery": "CODING_DEBUG_TOOL_DISCOVERY",
    "dimension:delegation_plus_evidence_synthesis_plus_artifact_production": "DELEGATION_SYNTHESIS_ARTIFACT",
    "dimension:cross_capability_state_handoff_and_rollback": "CROSS_CAPABILITY_HANDOFF_ROLLBACK",
}

STRUCTURED = "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
P1 = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
P2 = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
P3 = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"

def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes_b64__": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, set):
        return sorted(_jsonable(v) for v in value)
    return value

def _canon(value: Any) -> bytes:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()

def _seed(commitment: str, beacon: str, case_id: str) -> int:
    if not all(isinstance(x, str) and x for x in (commitment, beacon, case_id)):
        raise ValueError("NONEMPTY_COMMITMENT_BEACON_CASE_ID_REQUIRED")
    raw = (
        b"PROJECT_BRAIN_MATCHED_SUCCESS_INTEGRATED_EXTENSION_V1\0"
        + commitment.encode()
        + b"\0"
        + beacon.encode()
        + b"\0"
        + case_id.encode()
    )
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big", signed=False)

def _subseed(seed: int, label: str) -> int:
    raw = seed.to_bytes(8, "big", signed=False) + b"\0" + label.encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big", signed=False)

def _legacy_payload(route: str, seed: int, ordinal: int) -> dict[str, Any]:
    if route == "browser":
        return {"route": route, "case": browser.generate_case(seed, ordinal)}
    if route == "delegation_v3":
        return {"route": route, "case": delegation_v3.generate_case(seed, ordinal)}
    if route == "tool":
        return {"route": route, "case": tool.generate_case(seed, ordinal)}
    raise ValueError("UNKNOWN_LEGACY_ROUTE:" + route)

def _component(kind: str, seed: int, ordinal: int) -> dict[str, Any]:
    s = _subseed(seed, kind)
    if kind == "browser":
        return {"kind": kind, "case": browser.generate_case(s, ordinal)}
    if kind == "delegation_v2":
        return {"kind": kind, "case": delegation_v2.generate_case(s, ordinal)}
    if kind == "delegation_v3":
        return {"kind": kind, "case": delegation_v3.generate_case(s, ordinal)}
    if kind == "tool":
        return {"kind": kind, "case": tool.generate_case(s, ordinal)}
    if kind in {"m0", "m0_change"}:
        # Force FLAT_COMPOUND for every variant so each instruction stage
        # contains at least two independently scored constraints.
        m0_ordinal = 3 + 8 * ordinal
        return {"kind": kind, "case": m0.generate_case(s, m0_ordinal)}
    if kind == "structured":
        return {"kind": kind, "case": contract.generate_case(STRUCTURED, s, 1 + ordinal % 5)}
    if kind == "p1":
        return {"kind": kind, "case": contract.generate_case(P1, s, 1 + ordinal % 5)}
    if kind == "p2":
        return {"kind": kind, "case": contract.generate_case(P2, s, 1 + ordinal % 5)}
    if kind == "p3":
        return {"kind": kind, "case": contract.generate_case(P3, s, 1 + ordinal % 5)}
    if kind == "native":
        fmt = tuple(native.FORMATS)[ordinal % len(tuple(native.FORMATS))]
        return {"kind": kind, "format": fmt, "case": native.generate_case(fmt, s)}
    raise ValueError("UNKNOWN_COMPONENT:" + kind)

def _integrated_payload(class_id: str, seed: int, ordinal: int) -> dict[str, Any]:
    if class_id == "AGENCY_THREE_TOOL_LONG_HORIZON":
        kinds = ("browser", "tool", "delegation_v2")
        contract_row = {
            "minimum_distinct_action_types": 3,
            "state_handoff_required": True,
            "memory_token_from_stage_1_required_at_stage_3": True,
            "oversight_budget_after_start": 0,
        }
    elif class_id == "INSTRUCTION_CHANGE_CONTROL":
        kinds = ("m0", "m0_change", "delegation_v2")
        contract_row = {
            "multi_constraint_instruction_set_required": True,
            "initial_and_changed_instruction_each_multi_constraint": True,
            "mid_trajectory_requirement_change_required": True,
            "stale_prechange_plan_must_be_rejected": True,
        }
    elif class_id == "RESEARCH_TOOL_ARTIFACT":
        kinds = ("tool", "p3", "native")
        contract_row = {
            "tool_evidence_must_flow_into_synthesis": True,
            "synthesis_must_flow_into_native_artifact": True,
            "unsupported_claims_forbidden": True,
        }
    elif class_id == "BROWSER_MEMORY_RECOVERY":
        kinds = ("browser", "p1")
        contract_row = {
            "early_observation_memory_token_required_later": True,
            "observable_failure_injected": True,
            "recovery_must_preserve_pre_failure_goal_state": True,
        }
    elif class_id == "CODING_DEBUG_TOOL_DISCOVERY":
        kinds = ("structured", "p1", "tool")
        contract_row = {
            "structured_solution_then_failure_localization": True,
            "tool_discovery_required_for_repair_route": True,
            "repair_must_preserve_original_acceptance_graph": True,
        }
    elif class_id == "DELEGATION_SYNTHESIS_ARTIFACT":
        kinds = ("delegation_v3", "p3", "native")
        contract_row = {
            "delegated_evidence_fanin_required": True,
            "fanin_must_feed_synthesis": True,
            "synthesis_must_feed_artifact": True,
        }
    elif class_id == "CROSS_CAPABILITY_HANDOFF_ROLLBACK":
        kinds = ("delegation_v2", "tool", "p1", "p2")
        contract_row = {
            "content_addressed_handoff_required_between_stages": True,
            "checkpoint_before_mutation_required": True,
            "rollback_on_failed_handoff_required": True,
            "post_rollback_state_must_equal_checkpoint": True,
        }
    else:
        raise ValueError("UNKNOWN_INTEGRATED_CLASS:" + class_id)

    components = [_component(kind, seed, ordinal) for kind in kinds]
    handoff_chain = [
        {
            "from": kinds[i],
            "to": kinds[i + 1],
            "required_digest": hashlib.sha256(
                f"{class_id}\0{ordinal}\0{i}".encode()
            ).hexdigest(),
        }
        for i in range(len(kinds) - 1)
    ]
    return {
        "class_id": class_id,
        "components": components,
        "integration_contract": contract_row,
        "handoff_chain": handoff_chain,
    }

def case_id(atom: str, variant: int) -> str:
    slug = atom.split(":", 1)[1].replace("_", "-")
    return f"{VERSION}::{slug}::variant::{variant:02d}"

def generate_case(atom: str, variant: int, commitment: str, beacon: str) -> dict[str, Any]:
    if atom not in TARGET_BY_ATOM:
        raise ValueError("UNKNOWN_ATOM:" + atom)
    if not isinstance(variant, int) or not 0 <= variant < REPETITIONS:
        raise ValueError("VARIANT_OUT_OF_RANGE")
    cid = case_id(atom, variant)
    seed = _seed(commitment, beacon, cid)
    if atom in LEGACY_ROUTE:
        payload = {
            "mode": "LEGACY_SUBSTRATE_REUSE",
            "primary_atom": atom,
            "payload": _legacy_payload(LEGACY_ROUTE[atom], seed, variant),
        }
    else:
        class_id = INTEGRATED_CLASS[atom]
        payload = {
            "mode": "INTEGRATED_EXTENSION",
            "primary_atom": atom,
            "payload": _integrated_payload(class_id, seed, variant),
        }

    payload_sha = _sha256(payload)
    initial_state = {
        "harness_version": VERSION,
        "case_id": cid,
        "payload_sha256": payload_sha,
        "cross_case_memory": None,
        "result_history": [],
        "mutable_namespace": hashlib.sha256(
            f"{VERSION}\0{cid}\0{payload_sha}".encode()
        ).hexdigest(),
    }
    return {
        "case_id": cid,
        "seed": seed,
        "primary_atom": atom,
        "target_predicate": TARGET_BY_ATOM[atom],
        "case_payload": payload,
        "case_payload_sha256": payload_sha,
        "case_initial_state": initial_state,
        "case_initial_state_sha256": _sha256(initial_state),
    }

def generate_cases(commitment: str, beacon: str) -> list[dict[str, Any]]:
    rows = [
        generate_case(atom, variant, commitment, beacon)
        for atom in sorted(TARGET_BY_ATOM)
        for variant in range(REPETITIONS)
    ]
    if len(rows) != 64:
        raise AssertionError("EXPECTED_64_CASES")
    return rows

def scope_input(
    commitment: str,
    beacon: str,
    *,
    generator_git_blob_sha: str,
    scorer_git_blob_sha: str,
    brain_commit_sha: str,
    tool_authority_sha256: str,
    target_interface_sha256: str,
) -> dict[str, Any]:
    cases = generate_cases(commitment, beacon)
    scope_cases = []
    for row in cases:
        target_atoms = {key: [] for key in set(TARGET_BY_ATOM.values())}
        target_atoms[row["target_predicate"]] = [row["primary_atom"]]
        coverage_basis = {
            "version": VERSION,
            "case_id": row["case_id"],
            "primary_atom": row["primary_atom"],
            "target_predicate": row["target_predicate"],
        }
        # Pre-verification generator output is deliberately non-authoritative.
        # A separate canonical binder may upgrade these rows only after exact
        # independent verification of the semantic coverage rule.
        coverage_receipt_sha = "0" * 64
        scope_cases.append({
            "case_id": row["case_id"],
            "case_payload_sha256": row["case_payload_sha256"],
            "case_initial_state_sha256": row["case_initial_state_sha256"],
            "coverage": {
                "independently_verified": False,
                "receipt_sha256": coverage_receipt_sha,
                "target_atoms": target_atoms,
            },
        })
    return {
        "schema": SCOPE_SCHEMA,
        "freeze": {
            "generator_content_addressed": True,
            "generator_frozen_before_case_exposure": True,
            "post_freeze_beacon_or_equivalent_precommitted_randomness": True,
            "case_count_fixed_before_first_result": True,
            "scorer_content_addressed": True,
            "brain_runtime_content_addressed": True,
            "tool_authority_content_addressed": True,
            "target_interface_content_addressed": True,
            "no_case_replacement_after_exposure": True,
            "no_adaptive_case_selection": True,
            "no_result_dependent_scope_edit": True,
            "generator_git_blob_sha": generator_git_blob_sha,
            "scorer_git_blob_sha": scorer_git_blob_sha,
            "brain_commit_sha": brain_commit_sha,
            "tool_authority_sha256": tool_authority_sha256,
            "target_interface_sha256": target_interface_sha256,
            "fixed_case_count": len(scope_cases),
        },
        "cases": scope_cases,
    }
