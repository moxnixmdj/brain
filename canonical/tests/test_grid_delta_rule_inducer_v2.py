from canonical.runtime.grid_delta_rule_inducer_v2 import induce, predict


def _any(result, grid, expected):
    return any(
        predict(rule_set, grid).get("prediction") == expected
        for rule_set in result["rule_sets"]
    )


def test_component_relative_center_rule():
    train = [
        {
            "input": [
                [1, 1, 1, 0],
                [1, 1, 1, 0],
                [1, 1, 1, 0],
                [0, 0, 0, 0],
            ],
            "output": [
                [1, 1, 1, 0],
                [1, 2, 1, 0],
                [1, 1, 1, 0],
                [0, 0, 0, 0],
            ],
        },
        {
            "input": [
                [0, 0, 0, 0, 0],
                [0, 3, 3, 3, 0],
                [0, 3, 3, 3, 0],
                [0, 3, 3, 3, 0],
                [0, 0, 0, 0, 0],
            ],
            "output": [
                [0, 0, 0, 0, 0],
                [0, 3, 3, 3, 0],
                [0, 3, 2, 3, 0],
                [0, 3, 3, 3, 0],
                [0, 0, 0, 0, 0],
            ],
        },
    ]
    result=induce(train)
    assert result["status"]=="VERIFIED_RULE_SETS", result
    assert any(
        "component_rel_r" in rule["attributes"] and "component_rel_c" in rule["attributes"]
        for rs in result["rule_sets"] for rule in rs["rules"]
    ), result
    assert _any(
        result,
        [
            [0,4,4,4,0],
            [0,4,4,4,0],
            [0,4,4,4,0],
            [0,0,0,0,0],
        ],
        [
            [0,4,4,4,0],
            [0,4,2,4,0],
            [0,4,4,4,0],
            [0,0,0,0,0],
        ],
    )


def test_global_color_frequency_rule():
    train=[
        {
            "input":[
                [1,1,1,0],
                [2,0,0,0],
            ],
            "output":[
                [1,1,1,0],
                [5,0,0,0],
            ],
        },
        {
            "input":[
                [3,3,0,4],
                [3,0,0,0],
            ],
            "output":[
                [3,3,0,5],
                [3,0,0,0],
            ],
        },
    ]
    result=induce(train)
    assert result["status"]=="VERIFIED_RULE_SETS", result
    assert any(
        "color_frequency" in rule["attributes"]
        for rs in result["rule_sets"] for rule in rs["rules"]
    ), result
    assert _any(
        result,
        [[7,7,7,0,8]],
        [[7,7,7,0,5]],
    )


def test_multi_target_component_area_rules():
    train=[
        {
            "input":[[1,0,1,1,0,1,1,1]],
            "output":[[2,0,3,3,0,4,4,4]],
        },
        {
            "input":[[5,0,5,5,0,5,5,5]],
            "output":[[2,0,3,3,0,4,4,4]],
        },
    ]
    result=induce(train)
    assert result["status"]=="VERIFIED_RULE_SETS", result
    assert result["changed_target_colors"]==[2,3,4]
    assert _any(
        result,
        [[9,0,9,9,0,9,9,9]],
        [[2,0,3,3,0,4,4,4]],
    )


def test_shape_change_remains_explicitly_out_of_scope():
    result=induce([{"input":[[1,0]],"output":[[1],[0]]}])
    assert result["status"]=="UNSUPPORTED"
    assert result["reason"]=="SHAPE_CHANGE"
