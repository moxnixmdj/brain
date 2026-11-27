from canonical.runtime.arc_zero_learned_solver_v1 import solve_with_trace


def test_rot90_is_induced_from_examples():
    train = [
        {
            "input": [[1, 2, 3], [4, 5, 6]],
            "output": [[4, 1], [5, 2], [6, 3]],
        },
        {
            "input": [[7, 8], [9, 0], [1, 2]],
            "output": [[1, 9, 7], [2, 0, 8]],
        },
    ]
    out = solve_with_trace(train, [[3, 4], [5, 6]])
    assert out["status"] == "PREDICTION"
    assert out["prediction"] == [[5, 3], [6, 4]]
    assert out["persistent_learned_state_bytes"] == 0


def test_upscale2_is_induced_from_examples():
    train = [
        {
            "input": [[1, 2], [3, 4]],
            "output": [
                [1, 1, 2, 2],
                [1, 1, 2, 2],
                [3, 3, 4, 4],
                [3, 3, 4, 4],
            ],
        },
        {
            "input": [[5]],
            "output": [[5, 5], [5, 5]],
        },
    ]
    out = solve_with_trace(train, [[6, 7]])
    assert out["status"] == "PREDICTION"
    assert out["prediction"] == [[6, 6, 7, 7], [6, 6, 7, 7]]
    assert out["persistent_learned_state_bytes"] == 0


def test_consistent_color_mapping_is_inferred_only_from_training_examples():
    train = [
        {
            "input": [[0, 1], [1, 0]],
            "output": [[0, 2], [2, 0]],
        },
        {
            "input": [[1, 1, 0]],
            "output": [[2, 2, 0]],
        },
    ]
    out = solve_with_trace(train, [[1, 0, 1]])
    assert out["status"] == "PREDICTION"
    assert out["prediction"] == [[2, 0, 2]]
    assert out["persistent_learned_state_bytes"] == 0


def test_unexpressible_training_examples_fail_closed():
    train = [
        {
            "input": [[1, 2], [3, 4]],
            "output": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        },
        {
            "input": [[5, 6], [7, 8]],
            "output": [[9, 9, 9], [9, 9, 9], [9, 9, 9]],
        },
    ]
    out = solve_with_trace(train, [[1]])
    assert out["status"] == "NO_SOLUTION"
    assert out["prediction"] is None
    assert out["persistent_learned_state_bytes"] == 0
