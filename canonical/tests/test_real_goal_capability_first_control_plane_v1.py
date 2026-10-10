import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REAL="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"

def load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

def test_general_capability_parent_objective_and_benchmark_demotions():
    a=load("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
    d=load("canonical/governance/CURRENT_DEVELOPMENT_AUTHORITY.json")
    g=load("canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V12.json")
    o=load("canonical/governance/EXECUTION_FIRST_SELF_PROVING_OPTIMIZER_V2.json")
    assert a["terminal_objective"]==REAL
    assert d["terminal_objective"]==REAL
    assert o["terminal_objective"]==REAL
    assert a["active_program"]=="GENERAL_CAPABILITY_MAXIMIZATION_AND_VERIFIED_SELF_IMPROVEMENT_V1"
    assert a["benchmark_policy"]["red_row_is_job"] is False
    assert a["benchmark_policy"]["score_delta_is_general_progress"] is False
    assert d["development_scheduler"]["benchmark_rank_is_scheduling_authority"] is False
    assert d["development_scheduler"]["acceptance_family_red_state_is_scheduling_authority"] is False
    assert d["development_scheduler"]["score_delta_is_development_credit"] is False
    assert "BENCHMARK_OR_FAMILY_ROW_NOT_PARENT_OBJECTIVE" in g["required_checks"]
    assert "SCORE_DELTA_ALONE_ZERO_GENERAL_DEVELOPMENT_CREDIT" in g["required_checks"]
    assert "TERMINAL_TARGET_OPUS_5_5_CAPABILITY_OWNERSHIP" not in g["required_checks"]
    assert "CAPABILITY_ACCEPTANCE_BAR_GREATER_THAN_OR_EQUAL_TO_OPUS_5_5" not in g["required_checks"]
    assert "TERMINAL_TARGET_NOT_OPUS_5_5_CAPABILITY_OWNERSHIP" not in g["automatic_abort_conditions"]
    assert "UNDERLYING_CAPABILITY_INVENTION_SELECTED" not in g["automatic_abort_conditions"]
    assert o["scheduling"]["benchmark_rank_serialization_forbidden"] is True
    assert o["scheduling"]["score_delta_alone_zero_development_credit"] is True

def test_reuse_before_new_primitive_and_precedence():
    a=load("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
    d=load("canonical/governance/CURRENT_DEVELOPMENT_AUTHORITY.json")
    assert d["route_order"][-1]=="SYNTHESIZE_NEW_PRIMITIVE"
    assert d["new_primitive_admission"]["default_authorized"] is False
    assert a["control_plane_precedence"]["development_scheduling"]=="canonical/governance/CURRENT_DEVELOPMENT_AUTHORITY.json"
    assert a["control_plane_precedence"]["terminal_or_milestone_truth"]=="canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
