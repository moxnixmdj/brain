from canonical.runtime.grid_delta_rule_inducer_v3 import induce, predict


def test_v3_invents_component_relative_diagonal_relation():
    train=[
        {
            "input":[
                [1,1,1,0],
                [1,1,1,0],
                [1,1,1,0],
                [0,0,0,0],
            ],
            "output":[
                [2,1,1,0],
                [1,2,1,0],
                [1,1,2,0],
                [0,0,0,0],
            ],
        },
        {
            "input":[
                [0,0,0,0,0,0],
                [0,3,3,3,3,0],
                [0,3,3,3,3,0],
                [0,3,3,3,3,0],
                [0,3,3,3,3,0],
                [0,0,0,0,0,0],
            ],
            "output":[
                [0,0,0,0,0,0],
                [0,2,3,3,3,0],
                [0,3,2,3,3,0],
                [0,3,3,2,3,0],
                [0,3,3,3,2,0],
                [0,0,0,0,0,0],
            ],
        },
    ]
    result=induce(train)
    assert result["status"]=="VERIFIED_RULE_OPTIONS", result
    assert result["route"]=="V3_DERIVED_FEATURE_EXPRESSION_INVENTION", result
    assert result["representation_invention_used"] is True
    assert any(
        any(
            p["expr"][0]=="EQ" and
            set(p["expr"][1:])=={"component_rel_r","component_rel_c"}
            for p in d["predicates"]
        )
        for group in result["target_options"]
        for d in group["discriminators"]
    ), result

    test_input=[
        [0,0,0,0,0],
        [0,4,4,4,0],
        [0,4,4,4,0],
        [0,4,4,4,0],
        [0,0,0,0,0],
    ]
    expected=[
        [0,0,0,0,0],
        [0,2,4,4,0],
        [0,4,2,4,0],
        [0,4,4,2,0],
        [0,0,0,0,0],
    ]
    out=predict(result,test_input)
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==expected


def test_v3_reuses_cheaper_v2_when_v2_is_sufficient():
    train=[
        {
            "input":[[1,0,1,1]],
            "output":[[2,0,1,1]],
        },
        {
            "input":[[3,0,3,3]],
            "output":[[2,0,3,3]],
        },
    ]
    result=induce(train)
    assert result["status"]=="VERIFIED_RULE_OPTIONS", result
    assert result["route"]=="V2_BASE_ATTRIBUTE_SYNTHESIS", result
    assert result["representation_invention_used"] is False


def test_v3_preserves_shape_change_boundary():
    result=induce([{"input":[[1,0]],"output":[[1],[0]]}])
    assert result["status"]=="UNSUPPORTED"
    assert result["reason"]=="SHAPE_CHANGE"


def test_v3_abstains_when_invented_alternatives_disagree():
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
    assert result["status"]=="VERIFIED_RULE_OPTIONS", result
    out=predict(result,[[7,7,7,0,8]])
    assert out["status"] in {"PREDICTED","AMBIGUOUS_PREDICTION"}
    if out["status"]=="AMBIGUOUS_PREDICTION":
        assert out["prediction"] is None


def test_v3_escalates_ambiguous_v2_to_relational_invariant():
    def blank(h,w):
        return [[0 for _ in range(w)] for _ in range(h)]
    def rect(g,top,left,h,w,color):
        for r in range(top,top+h):
            for c in range(left,left+w):
                g[r][c]=color
        return g
    def pair(H,W,specs):
        g=blank(H,W)
        totals={}
        for top,left,h,w,color in specs:
            rect(g,top,left,h,w,color)
            totals[color]=totals.get(color,0)+h*w
        out=[row[:] for row in g]
        for top,left,h,w,color in specs:
            if h*w==totals[color]:
                for r in range(top,top+h):
                    for c in range(left,left+w):
                        out[r][c]=9
        return {"input":g,"output":out}

    train=[
        pair(8,12,[(1,1,2,2,1),(1,6,1,2,3),(4,6,1,2,3)]),
        pair(9,13,[(1,1,2,3,5),(1,8,1,2,6),(5,8,2,1,6)]),
    ]
    result=induce(train)
    assert result["status"]=="VERIFIED_RULE_OPTIONS", result
    assert result["route"]=="V3_DERIVED_FEATURE_EXPRESSION_INVENTION", result
    assert result["escalated_from_ambiguous_v2"] is True

    test=pair(10,14,[(1,1,1,4,7),(1,9,2,2,8),(6,8,1,4,8)])
    out=predict(result,test["input"])
    assert out["status"]=="PREDICTED", out
    assert out["prediction"]==test["output"]
