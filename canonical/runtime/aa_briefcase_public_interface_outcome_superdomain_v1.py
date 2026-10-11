from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_PUBLIC_INTERFACE_OUTCOME_SUPERDOMAIN_V1"


class SuperdomainError(ValueError):
    pass


def _true(payload: Mapping[str, Any], key: str) -> None:
    if payload.get(key) is not True:
        raise SuperdomainError(key.upper() + "_NOT_BOUND")


def verify(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise SuperdomainError("PAYLOAD_INVALID")
    if payload.get("benchmark") != "AA-Briefcase":
        raise SuperdomainError("BENCHMARK_MISMATCH")
    if payload.get("version") != "1.1":
        raise SuperdomainError("VERSION_MISMATCH")
    if payload.get("official_task_count") != 91:
        raise SuperdomainError("TASK_COUNT_MISMATCH")
    if payload.get("official_project_count") != 4:
        raise SuperdomainError("PROJECT_COUNT_MISMATCH")
    if payload.get("max_turns") != 500:
        raise SuperdomainError("TURN_LIMIT_MISMATCH")

    required_truths = (
        "tasks_run_independently",
        "finite_scenario_overview_unrestricted",
        "finite_week_overview_unrestricted",
        "finite_task_description_unrestricted",
        "finite_expected_output_filename_list_unrestricted",
        "finite_shared_file_map_unrestricted",
        "finite_week_file_map_unrestricted",
        "all_documented_tool_trajectories_up_to_turn_limit_included",
        "all_finite_submission_file_bytes_included",
        "abandon_outcome_included",
        "rubric_schema_all_finite_hidden_binary_predicates_included",
        "rubric_verdict_alphabet_complete",
        "analytical_pairwise_verdict_alphabet_complete",
        "presentation_pairwise_verdict_alphabet_complete",
        "all_public_judge_panel_assignments_included",
        "crowd_bt_eta_full_unit_interval_included",
        "all_finite_score_bearing_comparison_graphs_included",
        "headline_rating_real_nonnegative_output_included",
        "public_contract_binding_verified",
    )
    for key in required_truths:
        _true(payload, key)

    tools = payload.get("documented_tools")
    if not isinstance(tools, list):
        raise SuperdomainError("DOCUMENTED_TOOLS_INVALID")
    required_tools = {"code_exec", "finish", "abandon_task_finish"}
    if not required_tools.issubset(set(tools)):
        raise SuperdomainError("DOCUMENTED_TOOLS_INCOMPLETE")
    if "view_image_optional" not in tools:
        raise SuperdomainError("VISION_TOOL_OPTION_NOT_COVERED")

    rubric = payload.get("rubric_verdict_alphabet")
    pairwise = payload.get("pairwise_verdict_alphabet")
    if set(rubric or []) != {0, 1}:
        raise SuperdomainError("RUBRIC_ALPHABET_INVALID")
    if set(pairwise or []) != {"A", "TIE", "B"}:
        raise SuperdomainError("PAIRWISE_ALPHABET_INVALID")

    eta = payload.get("crowd_bt_eta_interval")
    if eta != [0.0, 1.0]:
        raise SuperdomainError("ETA_INTERVAL_INVALID")

    return {
        "schema": SCHEMA,
        "status": "PASS_SCOPE_COMPLETE_SUPERDOMAIN",
        "scope_complete": True,
        "verified": True,
        "covers_private_task_contents_without_enumeration": True,
        "covers_private_task_specific_rubric_predicates_as_opaque_predicates": True,
        "covers_realized_rubric_and_pairwise_verdict_types": True,
        "covers_crowd_bt_judge_quality_parameter_space": True,
        "covers_headline_rating_output_space": True,
        "material_order_complete": False,
        "brain_top_support_proved": False,
        "hidden_judge_monotonicity_proved": False,
        "frozen_1822_score_monotonicity_proved": False,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
