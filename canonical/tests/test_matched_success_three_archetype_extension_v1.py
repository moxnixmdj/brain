from canonical.runtime.matched_success_three_archetype_extension_v1 import _load, evaluate, validate, PLAN, LEGACY


def test_current_plan_passes():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["required_dimension_count"] == 16
    assert out["legacy_reused_dimension_count"] == 6
    assert out["new_dimension_count"] == 10
    assert out["archetype_count"] == 3
    assert out["terminal_cases_generated"] is False


def test_missing_load_bearing_atom_fails():
    plan = _load(PLAN)
    legacy = _load(LEGACY)
    plan["archetypes"][0]["coverage"].remove(
        "dimension:browser_or_computer_action_plus_memory_plus_recovery"
    )
    out = validate(plan, legacy)
    assert out["pass"] is False


def test_guard_substitution_fails():
    plan = _load(PLAN)
    legacy = _load(LEGACY)
    plan["atom_guards"]["dimension:requirement_change"][1] = "INVALID_MUTATION"
    out = validate(plan, legacy)
    assert out["pass"] is False


def test_hidden_oracle_fails():
    plan = _load(PLAN)
    legacy = _load(LEGACY)
    plan["information_boundary"]["candidate_receives_hidden_oracle"] = True
    out = validate(plan, legacy)
    assert out["pass"] is False


def test_terminal_generation_overclaim_fails():
    plan = _load(PLAN)
    legacy = _load(LEGACY)
    plan["generator_policy"]["terminal_cases_generated_now"] = True
    out = validate(plan, legacy)
    assert out["pass"] is False


def test_authority_stays_zero():
    out = evaluate()
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_delta"] == 0
