from canonical.runtime.bound_goal_plan_adapter_v1 import compile_bound_goal


def test_exact_literal_goal_compiles_without_execution_authority():
    out = compile_bound_goal('Respond with exactly "READY".')
    assert out["pass"] is True, out
    assert out["execution_authority"] is False
    assert out["compiled_plan"]["finish_summary"] == "READY"
    assert out["compiled_plan"]["clause_coverage_verified"] is True


def test_unknown_goal_remains_unresolved_not_guessed():
    out = compile_bound_goal("Perform an undefined transcendent operation over everything.")
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED"


def test_blank_goal_fails_closed():
    out = compile_bound_goal("")
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
