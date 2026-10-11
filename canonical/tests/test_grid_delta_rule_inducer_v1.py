from canonical.runtime.grid_delta_rule_inducer_v1 import induce, predict


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
    assert result["status"] == "VERIFIED_RULES", result
    assert result["training_full_replay_verified"] is True
    assert result["target_color"] == 2

    solved = False
    test_input = [[1, 0, 1, 0, 1]]
    expected = [[1, 2, 1, 2, 1]]
    for rule in result["rules"]:
        if predict(rule, test_input)["prediction"] == expected:
            solved = True
            break
    assert solved, result


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
    assert result["status"] == "VERIFIED_RULES", result
    assert any(
        "COMP_AREA_EQ_1" in rule["rule_predicates"]
        for rule in result["rules"]
    ), result

    test_input = [[1, 0, 1, 1, 0, 1]]
    expected = [[3, 0, 1, 1, 0, 3]]
    assert any(predict(rule, test_input)["prediction"] == expected for rule in result["rules"])


def test_multiple_changed_to_colors_are_explicitly_unsupported():
    result = induce([
        {
            "input": [[1, 0, 0]],
            "output": [[2, 3, 0]],
        }
    ])
    assert result["status"] == "UNSUPPORTED"
    assert result["reason"] == "MULTIPLE_CHANGED_TO_COLORS"


def test_shape_change_is_explicitly_unsupported():
    result = induce([
        {
            "input": [[1, 0]],
            "output": [[1], [0]],
        }
    ])
    assert result["status"] == "UNSUPPORTED"
    assert result["reason"] == "SHAPE_CHANGE"
