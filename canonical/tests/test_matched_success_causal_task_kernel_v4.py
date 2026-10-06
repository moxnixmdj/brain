from __future__ import annotations

import copy
import json

from canonical.runtime.matched_success_causal_task_kernel_v4 import (
    ATOM_CLASS,
    CLASS_ATOMS,
    generate_case,
    generate_cases,
    verify_case_coverage,
    _sha,
)


COMMITMENT = "V4_REHEARSAL_COMMITMENT"
BEACON = "V4_REHEARSAL_BEACON"


def case_for(atom):
    return generate_case(atom, 0, COMMITMENT, BEACON)


def rebind(case):
    payload_sha = _sha(case["case_payload"])
    case["case_payload_sha256"] = payload_sha
    initial = case["case_initial_state"]
    initial["mutable_namespace"] = _sha(
        {
            "version": "MATCHED_SUCCESS_CAUSAL_TASK_KERNEL_V4",
            "case_id": case["case_id"],
            "payload": payload_sha,
        }
    )
    case["case_initial_state_sha256"] = _sha(initial)
    return case


def test_v4_generates_exactly_40_unique_preexposure_cases():
    rows = generate_cases(COMMITMENT, BEACON)
    assert len(rows) == 40
    assert len({row["case_id"] for row in rows}) == 40
    assert len({row["case_payload_sha256"] for row in rows}) == 40
    assert len({row["case_initial_state_sha256"] for row in rows}) == 40


def test_every_missing_atom_has_structurally_verified_case_coverage():
    for atom in sorted(ATOM_CLASS):
        out = verify_case_coverage(case_for(atom))
        assert out["pass"] is True, (atom, out)
        assert atom in out["covered_atoms"]
        assert set(out["covered_atoms"]) == set(
            CLASS_ATOMS[ATOM_CLASS[atom]]
        )
        assert out["terminal_result_used"] is False
        assert out["fresh_reality_authority"] is False


def test_hidden_causal_oracle_is_not_part_of_public_surface():
    for atom in sorted(ATOM_CLASS):
        case = case_for(atom)
        definition = case["case_payload"]["definition"]
        public_text = json.dumps(definition["public"], sort_keys=True)
        oracle_text = json.dumps(definition["oracle"], sort_keys=True)
        assert public_text != oracle_text

        class_id = case["class_id"]
        if class_id == "AGENCY_THREE_TOOL_LONG_HORIZON":
            assert definition["oracle"]["stage_1_source_token"] not in public_text
        elif class_id == "RESEARCH_TOOL_ARTIFACT":
            assert definition["oracle"]["source_a_result"]["fact"] not in public_text
            assert definition["oracle"]["source_b_result"]["fact"] not in public_text
        elif class_id == "BROWSER_MEMORY_RECOVERY":
            assert definition["oracle"]["one_time_token"] not in public_text
        elif class_id == "CODING_DEBUG_TOOL_DISCOVERY":
            assert json.dumps(
                definition["oracle"]["correct_program"], sort_keys=True
            ) not in public_text
        elif class_id == "DELEGATION_SYNTHESIS_ARTIFACT":
            for value in definition["oracle"]["worker_results"].values():
                assert value not in public_text


def test_agency_label_fails_if_three_action_requirement_is_removed():
    atom = (
        "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types"
    )
    case = case_for(atom)
    case["case_payload"]["definition"]["public"]["action_types"] = [
        "observe_source",
        "transform_state",
    ]
    rebind(case)
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "AGENCY_ACTION_TYPES_LT_3" in out["errors"][0]


def test_instruction_label_fails_if_multi_constraint_structure_is_removed():
    atom = "dimension:multi_constraint_instruction_compliance"
    case = case_for(atom)
    case["case_payload"]["definition"]["public"]["initial_constraints"] = {
        "prefix": "A:"
    }
    rebind(case)
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "INSTRUCTION_CONSTRAINT_COUNT_LT_3" in out["errors"][0]


def test_research_label_fails_without_real_multi_source_tool_structure():
    atom = "dimension:research_plus_tool_use_plus_artifact_creation"
    case = case_for(atom)
    case["case_payload"]["definition"]["public"]["available_tools"] = [
        "search_source_a"
    ]
    rebind(case)
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "RESEARCH_MULTI_SOURCE_TOOL_USE_MISSING" in out["errors"][0]


def test_browser_label_fails_if_post_navigation_state_still_exposes_token():
    atom = "dimension:browser_or_computer_action_plus_memory_plus_recovery"
    case = case_for(atom)
    case["case_payload"]["definition"]["oracle"][
        "token_absent_from_post_navigation_public_state"
    ] = False
    rebind(case)
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "BROWSER_MEMORY_NOT_CAUSALLY_REQUIRED" in out["errors"][0]


def test_coding_label_fails_without_a_real_bug():
    atom = "dimension:coding_plus_debugging_plus_tool_discovery"
    case = case_for(atom)
    correct = copy.deepcopy(
        case["case_payload"]["definition"]["oracle"]["correct_program"]
    )
    case["case_payload"]["definition"]["public"]["buggy_program"] = correct
    rebind(case)
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "CODING_REAL_BUG_MISSING" in out["errors"][0]


def test_delegation_label_fails_if_worker_result_fanin_is_incomplete():
    atom = "dimension:delegation_plus_evidence_synthesis_plus_artifact_production"
    case = case_for(atom)
    results = case["case_payload"]["definition"]["oracle"]["worker_results"]
    results.pop("worker_c")
    rebind(case)
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "DELEGATION_WORKER_RESULT_SET_MISMATCH" in out["errors"][0]


def test_rollback_label_fails_if_mutation_does_not_change_state():
    atom = "dimension:cross_capability_state_handoff_and_rollback"
    case = case_for(atom)
    oracle = case["case_payload"]["definition"]["oracle"]
    oracle["mutated_state"] = copy.deepcopy(oracle["pre_mutation_state"])
    oracle["mutated_state_sha256"] = _sha(oracle["mutated_state"])
    rebind(case)
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "ROLLBACK_STATE_DIGESTS_INVALID" in out["errors"][0]


def test_any_class_loses_coverage_if_rescue_is_not_required():
    for atom in sorted(ATOM_CLASS):
        case = case_for(atom)
        case["case_payload"]["definition"]["intervention"][
            "rescue_must_restore_final_acceptance"
        ] = False
        rebind(case)
        out = verify_case_coverage(case)
        assert out["status"] == "FAIL_CLOSED", atom
        assert "INTERVENTION_RESCUE_NOT_REQUIRED" in out["errors"][0]


def test_generator_is_deterministic_and_beacon_sensitive():
    atom = sorted(ATOM_CLASS)[0]
    a = generate_case(atom, 0, COMMITMENT, BEACON)
    b = generate_case(atom, 0, COMMITMENT, BEACON)
    c = generate_case(atom, 0, COMMITMENT, BEACON + "_OTHER")
    assert a == b
    assert a["case_payload_sha256"] != c["case_payload_sha256"]


def test_stale_content_address_fails_before_semantic_credit():
    atom = "dimension:requirement_change"
    case = case_for(atom)
    case["case_payload"]["definition"]["public"]["stale_prechange_output_forbidden"] = False
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "CASE_PAYLOAD_SHA256_MISMATCH" in out["errors"][0]


def test_initial_namespace_must_bind_the_exact_payload_hash():
    atom = "dimension:requirement_change"
    case = case_for(atom)
    case["case_initial_state"]["mutable_namespace"] = "0" * 64
    case["case_initial_state_sha256"] = _sha(case["case_initial_state"])
    out = verify_case_coverage(case)
    assert out["status"] == "FAIL_CLOSED"
    assert "INITIAL_STATE_NAMESPACE_PAYLOAD_BINDING_MISMATCH" in out["errors"][0]
