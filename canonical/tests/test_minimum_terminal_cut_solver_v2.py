from canonical.runtime.minimum_terminal_cut_solver_v2 import evaluate


def base_predicates():
    return [
        {"id": "P1", "state": "OPEN"},
        {"id": "P2", "state": "OPEN"},
    ]


def test_parallel_fast_pair_beats_slower_single_action():
    payload = {
        "status": "PASS",
        "predicates": base_predicates(),
        "actions": [
            {
                "id": "wide_slow",
                "unresolved_target_predicates": ["P1", "P2"],
                "available_now": True,
                "unsatisfied_preconditions": [],
                "new_reality_units": 0,
                "wall_clock_seconds": 20,
                "probability_lower": 1.0,
                "probability_upper": 1.0,
                "information_gain": 1.0,
                "downstream_action_deletion": 0,
                "causal_phase": "ZERO_REALITY",
                "correlation_group": "wide",
            },
            {
                "id": "p1_fast",
                "unresolved_target_predicates": ["P1"],
                "available_now": True,
                "unsatisfied_preconditions": [],
                "new_reality_units": 0,
                "wall_clock_seconds": 5,
                "probability_lower": 1.0,
                "probability_upper": 1.0,
                "information_gain": 1.0,
                "downstream_action_deletion": 0,
                "causal_phase": "ZERO_REALITY",
                "correlation_group": "p1",
            },
            {
                "id": "p2_fast",
                "unresolved_target_predicates": ["P2"],
                "available_now": True,
                "unsatisfied_preconditions": [],
                "new_reality_units": 0,
                "wall_clock_seconds": 5,
                "probability_lower": 1.0,
                "probability_upper": 1.0,
                "information_gain": 1.0,
                "downstream_action_deletion": 0,
                "causal_phase": "ZERO_REALITY",
                "correlation_group": "p2",
            },
        ],
    }
    out = evaluate(payload)
    assert out["pass"] is True, out
    assert out["selected_actions"] == ["p1_fast", "p2_fast"], out
    assert out["selected_critical_path_seconds"] == 5.0, out
    assert out["covered_predicate_count"] == 2, out


def test_sequential_phase_barrier_is_counted_on_critical_path():
    payload = {
        "status": "PASS",
        "predicates": base_predicates(),
        "actions": [
            {
                "id": "zero",
                "unresolved_target_predicates": ["P1"],
                "available_now": True,
                "unsatisfied_preconditions": [],
                "new_reality_units": 0,
                "wall_clock_seconds": 4,
                "probability_lower": 1.0,
                "probability_upper": 1.0,
                "causal_phase": "ZERO_REALITY",
                "correlation_group": "z",
            },
            {
                "id": "fresh",
                "unresolved_target_predicates": ["P2"],
                "available_now": True,
                "unsatisfied_preconditions": [],
                "new_reality_units": 1,
                "wall_clock_seconds": 7,
                "probability_lower": 1.0,
                "probability_upper": 1.0,
                "causal_phase": "MINIMUM_REALITY",
                "correlation_group": "r",
            },
        ],
    }
    out = evaluate(payload)
    assert out["selected_actions"] == ["fresh", "zero"], out
    assert out["selected_critical_path_seconds"] == 11.0, out


def test_zero_probability_route_is_deleted():
    payload = {
        "status": "PASS",
        "predicates": [{"id": "P1", "state": "OPEN"}],
        "actions": [
            {
                "id": "impossible",
                "unresolved_target_predicates": ["P1"],
                "available_now": True,
                "unsatisfied_preconditions": [],
                "new_reality_units": 0,
                "wall_clock_seconds": 1,
                "probability_lower": 0.0,
                "probability_upper": 0.0,
                "causal_phase": "ZERO_REALITY",
                "correlation_group": "dead",
            },
            {
                "id": "live",
                "unresolved_target_predicates": ["P1"],
                "available_now": True,
                "unsatisfied_preconditions": [],
                "new_reality_units": 0,
                "wall_clock_seconds": 3,
                "probability_lower": 0.2,
                "probability_upper": 1.0,
                "causal_phase": "ZERO_REALITY",
                "correlation_group": "live",
            },
        ],
    }
    out = evaluate(payload)
    assert out["selected_actions"] == ["live"], out
    assert out["zero_probability_deleted_actions"] == ["impossible"], out


def test_invalid_probability_interval_fails_closed():
    payload = {
        "status": "PASS",
        "predicates": [{"id": "P1", "state": "OPEN"}],
        "actions": [
            {
                "id": "bad",
                "unresolved_target_predicates": ["P1"],
                "available_now": True,
                "unsatisfied_preconditions": [],
                "new_reality_units": 0,
                "wall_clock_seconds": 1,
                "probability_lower": 0.9,
                "probability_upper": 0.2,
                "causal_phase": "ZERO_REALITY",
                "correlation_group": "bad",
            }
        ],
    }
    out = evaluate(payload)
    assert out["pass"] is False, out
    assert any("ACTION_PROBABILITY_INTERVAL_INVALID:bad" == x for x in out["errors"])


def test_no_authority_or_credit():
    payload = {
        "status": "PASS",
        "predicates": [],
        "actions": [],
    }
    out = evaluate(payload)
    assert out["pass"] is True, out
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["capability_credit_delta"] == 0
    assert out["family_credit_delta"] == 0
    assert out["ownership_credit_delta"] == 0
    assert out["new_reality_units_consumed"] == 0
