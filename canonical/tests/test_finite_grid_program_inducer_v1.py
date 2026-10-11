from canonical.runtime.finite_grid_program_inducer_v1 import induce, predict


def test_discovers_two_step_crop_then_flip():
    train = [
        {
            "input": [[0, 0, 0, 0], [0, 1, 2, 0], [0, 3, 4, 0], [0, 0, 0, 0]],
            "output": [[2, 1], [4, 3]],
        },
        {
            "input": [[0, 0, 0, 0, 0], [0, 5, 6, 7, 0], [0, 0, 0, 0, 0]],
            "output": [[7, 6, 5]],
        },
    ]
    shallow = induce(train, max_depth=1)
    assert shallow["status"] == "NO_EXACT_PROGRAM"

    result = induce(train, max_depth=2)
    assert result["status"] == "EXACT_PROGRAMS"
    assert ["CROP_NONZERO", "FLIP_HORIZONTAL"] in result["programs"]

    out = predict(
        ["CROP_NONZERO", "FLIP_HORIZONTAL"],
        [[0, 0, 0, 0], [0, 8, 9, 0], [0, 0, 0, 0]],
    )
    assert out["prediction"] == [[9, 8]]


def test_discovers_two_step_dedupe_then_remove_zero_lines():
    train = [
        {
            "input": [
                [0, 0, 0, 0, 0],
                [0, 1, 1, 0, 0],
                [0, 1, 1, 0, 0],
                [0, 2, 2, 0, 0],
                [0, 2, 2, 0, 0],
            ],
            "output": [[1], [2]],
        }
    ]
    result = induce(train, max_depth=2)
    assert result["status"] == "EXACT_PROGRAMS"
    assert ["DEDUPE_ADJACENT_LINES", "REMOVE_ZERO_LINES"] in result["programs"]


def test_equal_minimum_ambiguity_is_preserved():
    train = [
        {
            "input": [[1, 2], [3, 4]],
            "output": [[4, 3], [2, 1]],
        }
    ]
    result = induce(train, max_depth=2)
    assert result["status"] == "EXACT_PROGRAMS"
    assert result["minimum_cost"] == 1
    assert ["ROTATE_180"] in result["programs"]
    assert result["complete_within_declared_bound"] is True


def test_no_exact_program_is_truthful():
    train = [
        {
            "input": [[1, 0], [0, 0]],
            "output": [[1, 1, 1], [1, 1, 1], [1, 1, 1]],
        }
    ]
    result = induce(train, max_depth=2)
    assert result["status"] == "NO_EXACT_PROGRAM"
    assert result["complete_within_declared_bound"] is True


def test_search_bound_overflow_fails_closed():
    train = [
        {
            "input": [[1, 2], [3, 4]],
            "output": [[9]],
        }
    ]
    result = induce(train, max_depth=3, max_programs=5)
    assert result["status"] == "SEARCH_BOUND_EXCEEDED"
    assert result["complete_within_declared_bound"] is False


def test_malformed_input_fails_closed():
    result = induce([{"input": [[1, 2], [3]], "output": [[1]]}], max_depth=2)
    assert result["status"] == "FAIL_CLOSED"
