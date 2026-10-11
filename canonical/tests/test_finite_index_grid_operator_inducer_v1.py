from canonical.runtime.finite_index_grid_operator_inducer_v1 import induce, predict


def _scale(g, kr, kc):
    out=[]
    for row in g:
        expanded=[]
        for v in row:
            expanded.extend([v]*kc)
        for _ in range(kr):
            out.append(expanded[:])
    return out


def _tile(g, kr, kc):
    h=len(g); w=len(g[0])
    return [[g[r%h][c%w] for c in range(w*kc)] for r in range(h*kr)]


def _transpose(g):
    return [list(row) for row in zip(*g)]


def _rot180(g):
    return [list(reversed(row)) for row in reversed(g)]


def test_infers_uniform_scale_2_across_sizes():
    train=[
        {"input":[[1,2],[3,4]],"output":_scale([[1,2],[3,4]],2,2)},
        {"input":[[5,6,7]],"output":_scale([[5,6,7]],2,2)},
    ]
    result=induce(train)
    assert result["status"]=="EXACT_OPERATORS", result
    test=[[8,9,1],[2,3,4]]
    out=predict(result,test)
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==_scale(test,2,2)


def test_infers_row_only_scale_3():
    train=[
        {"input":[[1,2],[3,4]],"output":_scale([[1,2],[3,4]],3,1)},
        {"input":[[5,6,7]],"output":_scale([[5,6,7]],3,1)},
    ]
    result=induce(train)
    assert result["status"]=="EXACT_OPERATORS", result
    test=[[8],[9],[1]]
    out=predict(result,test)
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==_scale(test,3,1)


def test_infers_tiling_2_by_3():
    train=[
        {"input":[[1,2],[3,4]],"output":_tile([[1,2],[3,4]],2,3)},
        {"input":[[5,6,7]],"output":_tile([[5,6,7]],2,3)},
    ]
    result=induce(train)
    assert result["status"]=="EXACT_OPERATORS", result
    test=[[8,9],[1,2],[3,4]]
    out=predict(result,test)
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==_tile(test,2,3)


def test_infers_transpose_then_scale_2():
    train=[
        {"input":[[1,2,3],[4,5,6]],"output":_scale(_transpose([[1,2,3],[4,5,6]]),2,2)},
        {"input":[[7,8],[9,1],[2,3]],"output":_scale(_transpose([[7,8],[9,1],[2,3]]),2,2)},
    ]
    result=induce(train)
    assert result["status"]=="EXACT_OPERATORS", result
    test=[[4,5,6,7],[8,9,1,2]]
    out=predict(result,test)
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==_scale(_transpose(test),2,2)


def test_infers_rotate180_then_scale_2():
    train=[
        {"input":[[1,2,3],[4,5,6]],"output":_scale(_rot180([[1,2,3],[4,5,6]]),2,2)},
        {"input":[[7,8],[9,1],[2,3]],"output":_scale(_rot180([[7,8],[9,1],[2,3]]),2,2)},
    ]
    result=induce(train)
    assert result["status"]=="EXACT_OPERATORS", result
    test=[[4,5],[6,7],[8,9]]
    out=predict(result,test)
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==_scale(_rot180(test),2,2)


def test_non_index_color_change_has_no_operator():
    result=induce([
        {"input":[[1,2],[3,4]],"output":[[9,9],[9,9]]}
    ])
    assert result["status"]=="NO_OPERATOR", result


def test_search_bound_overflow_fails_closed():
    result=induce(
        [{"input":[[1,2],[3,4]],"output":_scale([[1,2],[3,4]],4,4)}],
        max_candidates=1,
    )
    assert result["status"]=="SEARCH_BOUND_EXCEEDED", result
    assert result["complete_within_declared_bound"] is False
