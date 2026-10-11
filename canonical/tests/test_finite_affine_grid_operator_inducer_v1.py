from canonical.runtime.finite_affine_grid_operator_inducer_v1 import induce, predict


def test_infers_rotation_across_different_grid_sizes():
    train=[
        {
            "input":[[1,2,3],[4,5,6]],
            "output":[[4,1],[5,2],[6,3]],
        },
        {
            "input":[[7,8],[9,1],[2,3]],
            "output":[[2,9,7],[3,1,8]],
        },
    ]
    result=induce(train)
    assert result["status"]=="EXACT_OPERATORS", result
    out=predict(result,[[1,2,3,4],[5,6,7,8],[9,1,2,3]])
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==[
        [9,5,1],
        [1,6,2],
        [2,7,3],
        [3,8,4],
    ]


def test_infers_content_relative_bbox_crop_across_positions_and_sizes():
    train=[
        {
            "input":[
                [0,0,0,0,0],
                [0,1,2,0,0],
                [0,3,4,0,0],
                [0,0,0,0,0],
            ],
            "output":[[1,2],[3,4]],
        },
        {
            "input":[
                [0,0,0,0,0,0],
                [0,0,5,6,7,0],
                [0,0,8,9,1,0],
                [0,0,0,0,0,0],
            ],
            "output":[[5,6,7],[8,9,1]],
        },
    ]
    result=induce(train)
    assert result["status"]=="EXACT_OPERATORS", result
    out=predict(
        result,
        [
            [0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0],
            [0,2,3,4,5,0,0],
            [0,6,7,8,9,0,0],
            [0,0,0,0,0,0,0],
        ],
    )
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==[[2,3,4,5],[6,7,8,9]]


def test_infers_bbox_then_rotate_without_named_composite_operator():
    train=[
        {
            "input":[
                [0,0,0,0,0],
                [0,1,2,3,0],
                [0,4,5,6,0],
                [0,0,0,0,0],
            ],
            "output":[[4,1],[5,2],[6,3]],
        },
        {
            "input":[
                [0,0,0,0,0,0],
                [0,0,7,8,0,0],
                [0,0,9,1,0,0],
                [0,0,2,3,0,0],
                [0,0,0,0,0,0],
            ],
            "output":[[2,9,7],[3,1,8]],
        },
    ]
    result=induce(train)
    assert result["status"]=="EXACT_OPERATORS", result
    out=predict(
        result,
        [
            [0,0,0,0,0,0],
            [0,4,5,6,7,0],
            [0,8,9,1,2,0],
            [0,0,0,0,0,0],
        ],
    )
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==[
        [8,4],
        [9,5],
        [1,6],
        [2,7],
    ]


def test_non_affine_recolor_has_no_operator():
    result=induce([
        {
            "input":[[1,0],[0,1]],
            "output":[[2,0],[0,2]],
        }
    ])
    assert result["status"]=="NO_OPERATOR", result


def test_bound_overflow_fails_closed():
    result=induce(
        [{"input":[[1,2],[3,4]],"output":[[9,9],[9,9]]}],
        max_candidates=1,
    )
    assert result["status"]=="SEARCH_BOUND_EXCEEDED", result
    assert result["complete_within_declared_bound"] is False
