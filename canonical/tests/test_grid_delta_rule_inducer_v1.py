from canonical.runtime.grid_delta_rule_inducer_v1 import induce, predict


def _any_prediction(result, grid, expected):
    return any(
        predict(rule_set, grid).get("prediction") == expected
        for rule_set in result["rule_sets"]
    )


def test_infers_gap_rule_from_structural_predicates():
    train = [
        {
            "input": [[1, 0, 1, 0, 0]],
            "output": [[1, 2, 1, 0, 0]],
        },
        {
            "input": [[0, 1, 0, 1, 0]],
            "output": [[0, 1, 2, 1, 0]],
        },
    ]
    result = induce(train)
    assert result["status"] == "VERIFIED_RULE_SETS", result
    assert result["training_full_replay_verified"] is True
    assert result["changed_target_colors"] == [2]
    assert _any_prediction(result, [[1, 0, 1, 0, 1]], [[1, 2, 1, 2, 1]])


def test_infers_component_area_selector():
    train = [
        {
            "input": [
                [1, 0, 0, 1, 1],
                [0, 0, 0, 0, 0],
            ],
            "output": [
                [3, 0, 0, 1, 1],
                [0, 0, 0, 0, 0],
            ],
        },
        {
            "input": [
                [0, 1, 0, 0],
                [0, 0, 1, 1],
            ],
            "output": [
                [0, 3, 0, 0],
                [0, 0, 1, 1],
            ],
        },
    ]
    result = induce(train)
    assert result["status"] == "VERIFIED_RULE_SETS", result
    assert any(
        "COMP_AREA_EQ_1" in rule["rule_predicates"]
        for rule_set in result["rule_sets"]
        for rule in rule_set["rules"]
    ), result
    assert _any_prediction(result, [[1, 0, 1, 1, 0, 1]], [[3, 0, 1, 1, 0, 3]])


def test_infers_multiple_changed_to_colors_as_conflict_checked_rule_set():
    train = [
        {
            "input": [
                [1, 0, 1, 1],
                [0, 0, 0, 0],
            ],
            "output": [
                [2, 0, 3, 3],
                [0, 0, 0, 0],
            ],
        },
        {
            "input": [
                [0, 1, 0, 1],
                [0, 0, 0, 1],
            ],
            "output": [
                [0, 2, 0, 3],
                [0, 0, 0, 3],
            ],
        },
    ]
    result = induce(train)
    assert result["status"] == "VERIFIED_RULE_SETS", result
    assert result["changed_target_colors"] == [2, 3]
    assert all(len(x["rules"]) == 2 for x in result["rule_sets"])
    assert _any_prediction(
        result,
        [[1, 0, 1, 1, 0, 1]],
        [[2, 0, 3, 3, 0, 2]],
    )


def test_shape_change_is_explicitly_unsupported():
    result = induce([
        {
            "input": [[1, 0]],
            "output": [[1], [0]],
        }
    ])
    assert result["status"] == "UNSUPPORTED"
    assert result["reason"] == "SHAPE_CHANGE"
