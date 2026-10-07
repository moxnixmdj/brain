from canonical.runtime.adaptive_cover_least_fixed_point_v1 import compute_cover


def _edge(edge_id, state, successors, **overrides):
    row = {
        "edge_id": edge_id,
        "state_id": state,
        "brain_owned": True,
        "safety_authenticated": True,
        "outcome_model_complete_authenticated": True,
        "true_world_preservation_authenticated": True,
        "resource_authenticated": True,
        "outcomes": [
            {"outcome_id": f"o{i}", "successor_state_id": s}
            for i, s in enumerate(successors)
        ],
    }
    row.update(overrides)
    return row


def _terminal(state, *, adequacy=True, safety=True):
    return {
        "state_id": state,
        "adequacy_authenticated": adequacy,
        "safety_authenticated": safety,
    }


def test_chain_induces_strict_entry_stage_rank():
    out = compute_cover({
        "states": ["a", "b", "t"],
        "terminal_states": [_terminal("t")],
        "progress_edges": [
            _edge("b_to_t", "b", ["t"]),
            _edge("a_to_b", "a", ["b"]),
        ],
    })
    assert out["covered"] is True
    assert out["entry_stage_rank"] == {"a": 2, "b": 1, "t": 0}
    assert out["rank_strict_on_selected_progress_edges"] is True


def test_cycle_without_terminal_escape_remains_uncovered():
    out = compute_cover({
        "states": ["a", "b", "t"],
        "terminal_states": [_terminal("t")],
        "progress_edges": [
            _edge("a_to_b", "a", ["b"]),
            _edge("b_to_a", "b", ["a"]),
        ],
    })
    assert out["covered"] is False
    assert out["uncovered_states"] == ["a", "b"]


def test_nondeterministic_complete_outcomes_all_must_be_covered():
    out = compute_cover({
        "states": ["a", "b", "t"],
        "terminal_states": [_terminal("t")],
        "progress_edges": [
            _edge("b_to_t", "b", ["t"]),
            _edge("a_split", "a", ["b", "t"]),
        ],
    })
    assert out["covered"] is True
    assert out["entry_stage_rank"]["a"] == 2


def test_incomplete_outcome_authentication_does_not_enter_fixed_point():
    out = compute_cover({
        "states": ["a", "t"],
        "terminal_states": [_terminal("t")],
        "progress_edges": [
            _edge("a_to_t", "a", ["t"], outcome_model_complete_authenticated=False),
        ],
    })
    assert out["covered"] is False
    assert out["uncovered_states"] == ["a"]


def test_unsafe_terminal_is_not_terminal_cover():
    out = compute_cover({
        "states": ["t"],
        "terminal_states": [_terminal("t", safety=False)],
        "progress_edges": [],
    })
    assert out["covered"] is False
    assert out["uncovered_states"] == ["t"]


def test_unknown_successor_fails_closed():
    out = compute_cover({
        "states": ["a", "t"],
        "terminal_states": [_terminal("t")],
        "progress_edges": [_edge("a_bad", "a", ["missing"])],
    })
    assert out["status"] == "FAIL_CLOSED"
    assert out["covered"] is False


def test_authenticated_alternative_edge_can_cover_state_even_if_other_edge_cycles():
    out = compute_cover({
        "states": ["a", "t"],
        "terminal_states": [_terminal("t")],
        "progress_edges": [
            _edge("z_cycle", "a", ["a"]),
            _edge("a_terminal", "a", ["t"]),
        ],
    })
    assert out["covered"] is True
    assert out["witnesses"]["a"]["edge_id"] == "a_terminal"


def test_total_declared_cover_does_not_self_certify_global_trace_scope():
    out = compute_cover({
        "states": ["t"],
        "terminal_states": [_terminal("t")],
        "progress_edges": [],
    })
    assert out["covered"] is True
    assert out["scope_complete_for_s_trace_self_certified"] is False
    assert out["u_empty_authority"] is False
