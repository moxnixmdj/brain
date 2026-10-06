from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

VERSION = "MATCHED_SUCCESS_CAUSAL_TASK_KERNEL_V4"
REPETITIONS = 4

ATOM_CLASS = {
    "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types":
        "AGENCY_THREE_TOOL_LONG_HORIZON",
    "dimension:long_horizon_state_retention":
        "AGENCY_THREE_TOOL_LONG_HORIZON",
    "dimension:minimal_oversight_completion":
        "AGENCY_THREE_TOOL_LONG_HORIZON",
    "dimension:multi_constraint_instruction_compliance":
        "INSTRUCTION_CHANGE_CONTROL",
    "dimension:requirement_change":
        "INSTRUCTION_CHANGE_CONTROL",
    "dimension:research_plus_tool_use_plus_artifact_creation":
        "RESEARCH_TOOL_ARTIFACT",
    "dimension:browser_or_computer_action_plus_memory_plus_recovery":
        "BROWSER_MEMORY_RECOVERY",
    "dimension:coding_plus_debugging_plus_tool_discovery":
        "CODING_DEBUG_TOOL_DISCOVERY",
    "dimension:delegation_plus_evidence_synthesis_plus_artifact_production":
        "DELEGATION_SYNTHESIS_ARTIFACT",
    "dimension:cross_capability_state_handoff_and_rollback":
        "CROSS_CAPABILITY_HANDOFF_ROLLBACK",
}

CLASS_ATOMS: dict[str, tuple[str, ...]] = {}
for _atom, _class in ATOM_CLASS.items():
    CLASS_ATOMS.setdefault(_class, tuple())
    CLASS_ATOMS[_class] = CLASS_ATOMS[_class] + (_atom,)


class CoverageError(ValueError):
    pass


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


def _seed(commitment: str, beacon: str, case_id: str) -> int:
    if not all(isinstance(x, str) and x for x in (commitment, beacon, case_id)):
        raise ValueError("NONEMPTY_COMMITMENT_BEACON_CASE_ID_REQUIRED")
    raw = (
        VERSION.encode()
        + b"\0"
        + commitment.encode()
        + b"\0"
        + beacon.encode()
        + b"\0"
        + case_id.encode()
    )
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _token(label: str, seed: int, n: int = 12) -> str:
    return hashlib.sha256(
        f"{VERSION}\0{label}\0{seed}".encode()
    ).hexdigest()[:n]


def _case_id(atom: str, variant: int) -> str:
    slug = atom.split(":", 1)[1].replace("_", "-")
    return f"{VERSION}::{slug}::variant::{variant:02d}"


def _agency(seed: int) -> dict[str, Any]:
    source = _token("agency-source", seed)
    return {
        "public": {
            "goal": "Produce the final authorization token through the declared three-stage action graph.",
            "action_types": [
                "observe_source",
                "transform_state",
                "delegate_finalize",
            ],
            "dependency_edges": [
                ["observe_source", "transform_state"],
                ["transform_state", "delegate_finalize"],
            ],
            "oversight_budget_after_start": 0,
            "final_contract": {
                "must_use_stage_1_memory_after_two_component_boundaries": True,
                "must_complete_all_three_action_types": True,
            },
        },
        "oracle": {
            "stage_1_source_token": source,
            "stage_2_transform": "sha256(stage_1_source_token + ':stage2')",
            "stage_3_expected": (
                "sha256(stage_2_output + ':' + stage_1_source_token)"
            ),
            "stage_1_value_not_replayed_at_stage_3": True,
        },
        "intervention": {
            "load_bearing_source": "oracle.stage_1_source_token",
            "same_shape_decoy_required": True,
            "decoy_must_change_final_acceptance": True,
            "rescue_must_restore_final_acceptance": True,
        },
    }


def _instruction(seed: int) -> dict[str, Any]:
    lineage = _token("instruction-lineage", seed, 24)
    return {
        "public": {
            "task_lineage": lineage,
            "initial_constraints": {
                "prefix": "A:",
                "suffix": ":END",
                "max_words": 6,
            },
            "change_event": {
                "same_task_lineage": lineage,
                "replace": {"prefix": "B:", "max_words": 4},
                "preserve": ["suffix"],
            },
            "stale_prechange_output_forbidden": True,
        },
        "oracle": {
            "initial_constraint_count": 3,
            "postchange_constraint_count": 3,
            "stale_output_must_fail_postchange": True,
            "revised_output_must_pass_all_postchange_constraints": True,
        },
        "intervention": {
            "load_bearing_source": "public.change_event.replace",
            "same_shape_decoy_required": True,
            "decoy_must_change_final_acceptance": True,
            "rescue_must_restore_final_acceptance": True,
        },
    }


def _research(seed: int) -> dict[str, Any]:
    key = _token("research-key", seed)
    fact_a = _token("research-fact-a", seed)
    fact_b = _token("research-fact-b", seed)
    return {
        "public": {
            "question": "Retrieve both source facts, synthesize the keyed conclusion, and emit the required artifact.",
            "available_tools": ["search_source_a", "search_source_b"],
            "required_source_count": 2,
            "artifact_schema": {
                "type": "json",
                "required_fields": ["conclusion", "sources"],
            },
        },
        "oracle": {
            "source_a_result": {"key": key, "fact": fact_a},
            "source_b_result": {"key": key, "fact": fact_b},
            "expected_conclusion": _sha([key, fact_a, fact_b]),
            "artifact_requires_both_source_ids": True,
        },
        "intervention": {
            "load_bearing_source": "oracle.source_a_result.fact",
            "same_shape_decoy_required": True,
            "decoy_must_change_synthesis_and_artifact_acceptance": True,
            "rescue_must_restore_final_acceptance": True,
        },
    }


def _browser(seed: int) -> dict[str, Any]:
    token = _token("browser-once", seed)
    return {
        "public": {
            "initial_page": "/one-time",
            "next_page": "/workspace",
            "injected_failure": "STALE_VIEW_AFTER_NAVIGATION",
            "recovery_action_required": True,
            "final_prompt": "Return the one-time token after recovery.",
        },
        "oracle": {
            "one_time_token": token,
            "token_visible_only_before_navigation": True,
            "token_absent_from_post_navigation_public_state": True,
            "recovery_must_preserve_token": True,
        },
        "intervention": {
            "load_bearing_source": "oracle.one_time_token",
            "same_shape_decoy_required": True,
            "decoy_must_change_final_acceptance": True,
            "rescue_must_restore_final_acceptance": True,
        },
    }


def _coding(seed: int) -> dict[str, Any]:
    a = 2 + seed % 7
    b = 3 + (seed // 7) % 11
    bad_b = b + 1
    return {
        "public": {
            "language": "AFFINE_DSL_V1",
            "specification": "f(x) = a*x + b",
            "buggy_program": {"a": a, "b": bad_b},
            "available_tools": [
                {"id": "test_runner", "capability_hidden_until_probe": True},
                {"id": "formatter", "capability_hidden_until_probe": True},
                {"id": "docs", "capability_hidden_until_probe": True},
            ],
            "probe_budget": 2,
        },
        "oracle": {
            "correct_program": {"a": a, "b": b},
            "tests": [
                {"x": 0, "y": b},
                {"x": 1, "y": a + b},
                {"x": 3, "y": 3 * a + b},
            ],
            "required_tool_route": "test_runner",
            "bug_field": "b",
        },
        "intervention": {
            "load_bearing_source": "oracle.tests",
            "same_shape_decoy_required": True,
            "decoy_must_change_repair_acceptance": True,
            "rescue_must_restore_final_acceptance": True,
        },
    }


def _delegation(seed: int) -> dict[str, Any]:
    shards = [
        _token("delegation-shard-" + str(i), seed)
        for i in range(3)
    ]
    return {
        "public": {
            "workers": ["worker_a", "worker_b", "worker_c"],
            "subtasks": ["extract_a", "extract_b", "extract_c"],
            "fan_in_required": True,
            "artifact_schema": {
                "type": "json",
                "required_fields": ["synthesis", "worker_evidence"],
            },
        },
        "oracle": {
            "worker_results": {
                "worker_a": shards[0],
                "worker_b": shards[1],
                "worker_c": shards[2],
            },
            "expected_synthesis": _sha(shards),
            "artifact_requires_all_worker_evidence": True,
        },
        "intervention": {
            "load_bearing_source": "oracle.worker_results.worker_b",
            "same_shape_decoy_required": True,
            "decoy_must_change_synthesis_and_artifact_acceptance": True,
            "rescue_must_restore_final_acceptance": True,
        },
    }


def _rollback(seed: int) -> dict[str, Any]:
    value = _token("rollback-state", seed)
    pre = {
        "semantic_value": value,
        "phase": "checkpoint",
        "history": ["start"],
    }
    mutated = {
        "semantic_value": value + "::CORRUPTED",
        "phase": "handoff_failed",
        "history": ["start", "bad_handoff"],
    }
    return {
        "public": {
            "capability_chain": [
                "delegation",
                "tool_action",
                "verification",
                "artifact_revision",
            ],
            "checkpoint_required_before_handoff": True,
            "failed_handoff_requires_exact_rollback": True,
            "alternate_route_required_after_rollback": True,
        },
        "oracle": {
            "pre_mutation_state": pre,
            "pre_mutation_state_sha256": _sha(pre),
            "mutated_state": mutated,
            "mutated_state_sha256": _sha(mutated),
            "post_rollback_state_must_equal_pre_mutation": True,
        },
        "intervention": {
            "load_bearing_source": "oracle.pre_mutation_state.semantic_value",
            "same_shape_decoy_required": True,
            "decoy_must_change_post_handoff_acceptance": True,
            "rescue_must_restore_final_acceptance": True,
        },
    }


BUILDERS = {
    "AGENCY_THREE_TOOL_LONG_HORIZON": _agency,
    "INSTRUCTION_CHANGE_CONTROL": _instruction,
    "RESEARCH_TOOL_ARTIFACT": _research,
    "BROWSER_MEMORY_RECOVERY": _browser,
    "CODING_DEBUG_TOOL_DISCOVERY": _coding,
    "DELEGATION_SYNTHESIS_ARTIFACT": _delegation,
    "CROSS_CAPABILITY_HANDOFF_ROLLBACK": _rollback,
}


def generate_case(
    atom: str,
    variant: int,
    commitment: str,
    beacon: str,
) -> dict[str, Any]:
    if atom not in ATOM_CLASS:
        raise ValueError("UNKNOWN_ATOM:" + atom)
    if not isinstance(variant, int) or not 0 <= variant < REPETITIONS:
        raise ValueError("VARIANT_OUT_OF_RANGE")
    cid = _case_id(atom, variant)
    seed = _seed(commitment, beacon, cid)
    class_id = ATOM_CLASS[atom]
    definition = BUILDERS[class_id](seed)
    payload = {
        "version": VERSION,
        "case_id": cid,
        "primary_atom": atom,
        "class_id": class_id,
        "class_atoms": list(CLASS_ATOMS[class_id]),
        "definition": definition,
    }
    initial_state = {
        "case_id": cid,
        "mutable_namespace": _sha(
            {"version": VERSION, "case_id": cid, "payload": _sha(payload)}
        ),
        "cross_case_memory": None,
        "result_history": [],
    }
    return {
        "case_id": cid,
        "seed": seed,
        "primary_atom": atom,
        "class_id": class_id,
        "case_payload": payload,
        "case_payload_sha256": _sha(payload),
        "case_initial_state": initial_state,
        "case_initial_state_sha256": _sha(initial_state),
    }


def generate_cases(commitment: str, beacon: str) -> list[dict[str, Any]]:
    rows = [
        generate_case(atom, variant, commitment, beacon)
        for atom in sorted(ATOM_CLASS)
        for variant in range(REPETITIONS)
    ]
    if len(rows) != 40:
        raise AssertionError("EXPECTED_40_NEW_INTEGRATED_CASES")
    return rows


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise CoverageError(reason)


def verify_case_coverage(case: Mapping[str, Any]) -> dict[str, Any]:
    try:
        payload = case.get("case_payload")
        if not isinstance(payload, Mapping):
            raise CoverageError("PAYLOAD_INVALID")
        if case.get("case_payload_sha256") != _sha(payload):
            raise CoverageError("CASE_PAYLOAD_SHA256_MISMATCH")
        initial_state = case.get("case_initial_state")
        if not isinstance(initial_state, Mapping):
            raise CoverageError("INITIAL_STATE_INVALID")
        if case.get("case_initial_state_sha256") != _sha(initial_state):
            raise CoverageError("CASE_INITIAL_STATE_SHA256_MISMATCH")
        expected_namespace = _sha(
            {
                "version": VERSION,
                "case_id": case.get("case_id"),
                "payload": case.get("case_payload_sha256"),
            }
        )
        if initial_state.get("mutable_namespace") != expected_namespace:
            raise CoverageError("INITIAL_STATE_NAMESPACE_PAYLOAD_BINDING_MISMATCH")
        if initial_state.get("cross_case_memory") is not None:
            raise CoverageError("INITIAL_STATE_CROSS_CASE_MEMORY_NOT_EMPTY")
        if initial_state.get("result_history") != []:
            raise CoverageError("INITIAL_STATE_RESULT_HISTORY_NOT_EMPTY")
        if case.get("case_id") != payload.get("case_id"):
            raise CoverageError("CASE_ID_MISMATCH")
        atom = payload.get("primary_atom")
        class_id = payload.get("class_id")
        if case.get("primary_atom") != atom:
            raise CoverageError("PRIMARY_ATOM_MISMATCH")
        if case.get("class_id") != class_id:
            raise CoverageError("CLASS_ID_MISMATCH")
        if atom not in ATOM_CLASS:
            raise CoverageError("ATOM_INVALID")
        if ATOM_CLASS[atom] != class_id:
            raise CoverageError("ATOM_CLASS_MISMATCH")
        expected_class_atoms = set(CLASS_ATOMS[str(class_id)])
        if set(payload.get("class_atoms") or []) != expected_class_atoms:
            raise CoverageError("CLASS_ATOM_SET_MISMATCH")
        definition = payload.get("definition")
        if not isinstance(definition, Mapping):
            raise CoverageError("DEFINITION_INVALID")
        public = definition.get("public")
        oracle = definition.get("oracle")
        intervention = definition.get("intervention")
        if not all(
            isinstance(x, Mapping)
            for x in (public, oracle, intervention)
        ):
            raise CoverageError("PUBLIC_ORACLE_INTERVENTION_INVALID")

        if class_id == "AGENCY_THREE_TOOL_LONG_HORIZON":
            actions = public.get("action_types")
            edges = public.get("dependency_edges")
            _require(
                isinstance(actions, list)
                and len(actions) >= 3
                and len(set(actions)) >= 3,
                "AGENCY_ACTION_TYPES_LT_3",
            )
            _require(
                isinstance(edges, list)
                and len(edges) >= 2,
                "AGENCY_DEPENDENCY_GRAPH_TOO_SMALL",
            )
            _require(
                public.get("oversight_budget_after_start") == 0,
                "AGENCY_OVERSIGHT_BUDGET_NOT_ZERO",
            )
            final = public.get("final_contract") or {}
            _require(
                final.get(
                    "must_use_stage_1_memory_after_two_component_boundaries"
                )
                is True,
                "AGENCY_LONG_HORIZON_MEMORY_NOT_LOAD_BEARING",
            )
            _require(
                oracle.get("stage_1_value_not_replayed_at_stage_3") is True,
                "AGENCY_MEMORY_REPLAY_NOT_FORBIDDEN",
            )

        elif class_id == "INSTRUCTION_CHANGE_CONTROL":
            initial = public.get("initial_constraints")
            change = public.get("change_event")
            _require(
                isinstance(initial, Mapping) and len(initial) >= 3,
                "INSTRUCTION_CONSTRAINT_COUNT_LT_3",
            )
            _require(
                isinstance(change, Mapping)
                and change.get("same_task_lineage")
                == public.get("task_lineage"),
                "INSTRUCTION_CHANGE_NOT_SAME_LINEAGE",
            )
            _require(
                isinstance(change.get("replace"), Mapping)
                and bool(change["replace"]),
                "INSTRUCTION_CHANGE_EMPTY",
            )
            _require(
                public.get("stale_prechange_output_forbidden") is True
                and oracle.get("stale_output_must_fail_postchange") is True,
                "INSTRUCTION_STALE_OUTPUT_NOT_FORBIDDEN",
            )

        elif class_id == "RESEARCH_TOOL_ARTIFACT":
            tools = public.get("available_tools")
            schema = public.get("artifact_schema") or {}
            _require(
                isinstance(tools, list)
                and len(tools) >= 2
                and public.get("required_source_count", 0) >= 2,
                "RESEARCH_MULTI_SOURCE_TOOL_USE_MISSING",
            )
            _require(
                {"conclusion", "sources"}.issubset(
                    set(schema.get("required_fields") or [])
                ),
                "RESEARCH_ARTIFACT_FIELDS_MISSING",
            )
            _require(
                oracle.get("artifact_requires_both_source_ids") is True,
                "RESEARCH_SOURCE_PROVENANCE_NOT_LOAD_BEARING",
            )

        elif class_id == "BROWSER_MEMORY_RECOVERY":
            _require(
                bool(public.get("initial_page"))
                and bool(public.get("next_page"))
                and public.get("initial_page") != public.get("next_page"),
                "BROWSER_STATE_TRANSITION_MISSING",
            )
            _require(
                bool(public.get("injected_failure"))
                and public.get("recovery_action_required") is True,
                "BROWSER_RECOVERY_NOT_REQUIRED",
            )
            _require(
                oracle.get("token_visible_only_before_navigation") is True
                and oracle.get(
                    "token_absent_from_post_navigation_public_state"
                )
                is True
                and oracle.get("recovery_must_preserve_token") is True,
                "BROWSER_MEMORY_NOT_CAUSALLY_REQUIRED",
            )

        elif class_id == "CODING_DEBUG_TOOL_DISCOVERY":
            buggy = public.get("buggy_program")
            correct = oracle.get("correct_program")
            tools = public.get("available_tools")
            tests = oracle.get("tests")
            _require(
                isinstance(buggy, Mapping)
                and isinstance(correct, Mapping)
                and dict(buggy) != dict(correct),
                "CODING_REAL_BUG_MISSING",
            )
            _require(
                isinstance(tests, list) and len(tests) >= 3,
                "CODING_TEST_ORACLE_TOO_SMALL",
            )
            _require(
                isinstance(tools, list)
                and len(tools) >= 2
                and oracle.get("required_tool_route") == "test_runner",
                "CODING_TOOL_DISCOVERY_NOT_LOAD_BEARING",
            )

        elif class_id == "DELEGATION_SYNTHESIS_ARTIFACT":
            workers = public.get("workers")
            subtasks = public.get("subtasks")
            schema = public.get("artifact_schema") or {}
            results = oracle.get("worker_results")
            _require(
                isinstance(workers, list)
                and isinstance(subtasks, list)
                and len(workers) >= 3
                and len(workers) == len(subtasks),
                "DELEGATION_FANOUT_TOO_SMALL",
            )
            _require(
                isinstance(results, Mapping)
                and set(results) == set(workers),
                "DELEGATION_WORKER_RESULT_SET_MISMATCH",
            )
            _require(
                public.get("fan_in_required") is True
                and oracle.get("artifact_requires_all_worker_evidence") is True,
                "DELEGATION_FANIN_NOT_LOAD_BEARING",
            )
            _require(
                {"synthesis", "worker_evidence"}.issubset(
                    set(schema.get("required_fields") or [])
                ),
                "DELEGATION_ARTIFACT_FIELDS_MISSING",
            )

        elif class_id == "CROSS_CAPABILITY_HANDOFF_ROLLBACK":
            chain = public.get("capability_chain")
            pre = oracle.get("pre_mutation_state")
            mutated = oracle.get("mutated_state")
            _require(
                isinstance(chain, list)
                and len(chain) >= 3
                and len(set(chain)) >= 3,
                "ROLLBACK_CROSS_CAPABILITY_CHAIN_TOO_SMALL",
            )
            _require(
                public.get("checkpoint_required_before_handoff") is True
                and public.get("failed_handoff_requires_exact_rollback") is True,
                "ROLLBACK_CONTRACT_MISSING",
            )
            _require(
                _sha(pre) == oracle.get("pre_mutation_state_sha256")
                and _sha(mutated) == oracle.get("mutated_state_sha256")
                and _sha(pre) != _sha(mutated),
                "ROLLBACK_STATE_DIGESTS_INVALID",
            )
            _require(
                oracle.get(
                    "post_rollback_state_must_equal_pre_mutation"
                )
                is True,
                "ROLLBACK_EXACT_RESTORE_NOT_REQUIRED",
            )

        else:
            raise CoverageError("UNKNOWN_CLASS")

        _require(
            intervention.get("same_shape_decoy_required") is True,
            "INTERVENTION_DECOY_NOT_REQUIRED",
        )
        _require(
            intervention.get("rescue_must_restore_final_acceptance") is True,
            "INTERVENTION_RESCUE_NOT_REQUIRED",
        )
        load_source = intervention.get("load_bearing_source")
        _require(
            isinstance(load_source, str)
            and load_source.startswith("oracle."),
            "INTERVENTION_LOAD_BEARING_SOURCE_INVALID",
        )

        return {
            "schema": "PROJECT_BRAIN_MATCHED_SUCCESS_CAUSAL_TASK_COVERAGE_V4",
            "status": "PASS__STRUCTURAL_SEMANTIC_COVERAGE",
            "pass": True,
            "case_id": case.get("case_id"),
            "primary_atom": atom,
            "class_id": class_id,
            "covered_atoms": sorted(expected_class_atoms),
            "case_payload_sha256": case.get("case_payload_sha256"),
            "coverage_semantics_sha256": _sha(
                {
                    "class_id": class_id,
                    "covered_atoms": sorted(expected_class_atoms),
                    "definition": definition,
                }
            ),
            "terminal_result_used": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except CoverageError as exc:
        return {
            "schema": "PROJECT_BRAIN_MATCHED_SUCCESS_CAUSAL_TASK_COVERAGE_V4",
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [str(exc)],
            "covered_atoms": [],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
