from canonical.runtime.coding_static_verified_capability_route_theorem_v1 import (
    prove_route,
    verify_sources,
)

ROUTE = [
    {
        "requires": ["A"],
        "provides": ["B"],
        "planner_selected_plan_bound": True,
        "effect_semantics_authenticated": True,
        "verifier_total_sound_complete": True,
        "execution_total_success": True,
        "no_unresolved_irreversible_effect": True,
    },
    {
        "requires": ["B"],
        "provides": ["GOAL"],
        "planner_selected_plan_bound": True,
        "effect_semantics_authenticated": True,
        "verifier_total_sound_complete": True,
        "execution_total_success": True,
        "no_unresolved_irreversible_effect": True,
    },
]

def test_constructive_route_closes_targets():
    out = prove_route(
        initial_facts=["A"],
        target_effects=["GOAL"],
        route=ROUTE,
        cycle_budget=3,
        target_effects_task_correctness_complete=True,
        preterminal_information_admissible=True,
    )
    assert out["pass"] is True, out
    assert out["targets_reached"] is True
    assert out["constructive_liveness_proved_for_bound_cell"] is True

def test_missing_step_premise_fails_closed():
    bad = [dict(x) for x in ROUTE]
    bad[0]["execution_total_success"] = False
    out = prove_route(
        initial_facts=["A"], target_effects=["GOAL"], route=bad, cycle_budget=3,
        target_effects_task_correctness_complete=True,
        preterminal_information_admissible=True,
    )
    assert out["pass"] is False
    assert any("execution_total_success" in e for e in out["errors"])

def test_proxy_target_without_task_correctness_binding_fails():
    out = prove_route(
        initial_facts=["A"], target_effects=["GOAL"], route=ROUTE, cycle_budget=3,
        target_effects_task_correctness_complete=False,
        preterminal_information_admissible=True,
    )
    assert out["pass"] is False
    assert "TARGET_EFFECTS_TASK_CORRECTNESS_NOT_COMPLETE" in out["errors"]

def test_bound_v12_sources_are_exact():
    out = verify_sources()
    assert out["pass"] is True, out
