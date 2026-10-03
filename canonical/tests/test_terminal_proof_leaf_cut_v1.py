from canonical.runtime.terminal_proof_leaf_cut_v1 import evaluate


def test_shared_leaf_is_paid_once_and_exact_optimum_is_proved():
    doc = {
        "roots": ["ROOT"],
        "nodes": [
            {"id": "ROOT", "kind": "AND", "children": ["A", "B"]},
            {"id": "A", "kind": "OR", "children": ["SHARED", "EXPENSIVE"]},
            {"id": "B", "kind": "AND", "children": ["SHARED"]},
            {"id": "SHARED", "kind": "LEAF", "cost_state": "KNOWN", "reality_units": 1},
            {"id": "EXPENSIVE", "kind": "LEAF", "cost_state": "KNOWN", "reality_units": 4},
        ],
    }
    out = evaluate(doc)
    assert out["status"] == "EXACT_OPTIMUM_PROVED"
    assert out["selected_leaf_ids"] == ["SHARED"]
    assert out["lower_bound_reality_units"] == 1
    assert out["upper_bound_reality_units"] == 1
    assert out["optimality_certificate"]["optimality_proved"] is True


def test_unknown_cost_blocks_exact_optimality_when_it_can_beat_known_route():
    doc = {
        "roots": ["ROOT"],
        "nodes": [
            {"id": "ROOT", "kind": "OR", "children": ["KNOWN", "UNKNOWN"]},
            {"id": "KNOWN", "kind": "LEAF", "cost_state": "KNOWN", "reality_units": 5},
            {"id": "UNKNOWN", "kind": "LEAF", "cost_state": "UNKNOWN"},
        ],
    }
    out = evaluate(doc)
    assert out["status"] == "LOWER_BOUND_ONLY_UNKNOWN_COSTS_REMAIN"
    assert out["selected_leaf_ids"] == ["UNKNOWN"]
    assert out["lower_bound_reality_units"] == 0
    assert out["upper_bound_reality_units"] == 5
    assert out["optimality_certificate"]["optimality_proved"] is False


def test_unknown_route_does_not_block_optimum_when_known_zero_route_matches_lower_bound():
    doc = {
        "roots": ["ROOT"],
        "nodes": [
            {"id": "ROOT", "kind": "OR", "children": ["ZERO", "UNKNOWN"]},
            {"id": "ZERO", "kind": "LEAF", "cost_state": "KNOWN", "reality_units": 0},
            {"id": "UNKNOWN", "kind": "LEAF", "cost_state": "UNKNOWN"},
        ],
    }
    out = evaluate(doc)
    assert out["status"] == "EXACT_OPTIMUM_PROVED"
    assert out["selected_leaf_ids"] == ["ZERO"]
    assert out["lower_bound_reality_units"] == 0
    assert out["upper_bound_reality_units"] == 0


def test_impossible_branch_is_deleted_but_impossible_root_fails_closed():
    doc = {
        "roots": ["ROOT"],
        "nodes": [
            {"id": "ROOT", "kind": "OR", "children": ["IMP", "L"]},
            {"id": "IMP", "kind": "IMPOSSIBLE"},
            {"id": "L", "kind": "LEAF", "cost_state": "KNOWN", "reality_units": 2},
        ],
    }
    out = evaluate(doc)
    assert out["status"] == "EXACT_OPTIMUM_PROVED"
    assert out["selected_leaf_ids"] == ["L"]

    impossible = {"roots": ["IMP"], "nodes": [{"id": "IMP", "kind": "IMPOSSIBLE"}]}
    out2 = evaluate(impossible)
    assert out2["status"] == "FAIL_CLOSED"
    assert "ROOTS_UNSATISFIABLE" in out2["errors"]


def test_cycle_fails_closed():
    doc = {
        "roots": ["A"],
        "nodes": [
            {"id": "A", "kind": "AND", "children": ["B"]},
            {"id": "B", "kind": "OR", "children": ["A"]},
        ],
    }
    out = evaluate(doc)
    assert out["status"] == "FAIL_CLOSED"
    assert any(x.startswith("CYCLE_DETECTED:") for x in out["errors"])
