from canonical.runtime.finite_feature_expression_inventor_v1 import (
    LabeledRow,
    evaluate,
    invent,
    invent_across_feature_packs,
)


def test_invents_cross_feature_equality_relation():
    rows=[
        LabeledRow("p1",{"a":0,"b":0,"noise":7},True),
        LabeledRow("p2",{"a":1,"b":1,"noise":8},True),
        LabeledRow("p3",{"a":3,"b":3,"noise":9},True),
        LabeledRow("n1",{"a":0,"b":1,"noise":7},False),
        LabeledRow("n2",{"a":2,"b":1,"noise":8},False),
        LabeledRow("n3",{"a":3,"b":2,"noise":9},False),
    ]
    result=invent(rows)
    assert result["status"]=="INVENTED_DISCRIMINATORS", result
    assert any(
        any(p["expr"][0]=="EQ" and set(p["expr"][1:])=={"a","b"} for p in d["predicates"])
        for d in result["discriminators"]
    ), result
    assert any(evaluate(d,{"a":5,"b":5,"noise":100}) for d in result["discriminators"])
    assert not any(evaluate(d,{"a":5,"b":4,"noise":100}) for d in result["discriminators"])


def test_invents_absolute_difference_relation():
    rows=[
        LabeledRow("p1",{"x":0,"y":1},True),
        LabeledRow("p2",{"x":3,"y":2},True),
        LabeledRow("p3",{"x":7,"y":8},True),
        LabeledRow("n1",{"x":0,"y":0},False),
        LabeledRow("n2",{"x":1,"y":4},False),
        LabeledRow("n3",{"x":8,"y":4},False),
    ]
    result=invent(rows)
    assert result["status"]=="INVENTED_DISCRIMINATORS", result
    assert any(
        any(p["expr"][0]=="ABS_DIFF" for p in d["predicates"])
        for d in result["discriminators"]
    ), result
    assert any(evaluate(d,{"x":10,"y":11}) for d in result["discriminators"])
    assert not any(evaluate(d,{"x":10,"y":13}) for d in result["discriminators"])


def test_preserves_equal_cost_ambiguity():
    rows=[
        LabeledRow("p1",{"a":0,"b":0,"c":1,"d":1},True),
        LabeledRow("p2",{"a":2,"b":2,"c":4,"d":4},True),
        LabeledRow("n1",{"a":0,"b":1,"c":1,"d":2},False),
        LabeledRow("n2",{"a":3,"b":2,"c":5,"d":4},False),
    ]
    result=invent(rows)
    assert result["status"]=="INVENTED_DISCRIMINATORS", result
    assert result["ambiguity_preserved"] is True
    assert result["discriminator_count"]>=2


def test_feature_schema_mismatch_fails_closed():
    result=invent([
        LabeledRow("p",{"a":1},True),
        LabeledRow("n",{"b":1},False),
    ])
    assert result["status"]=="FAIL_CLOSED"
    assert result["reason"]=="FEATURE_SCHEMA_MISMATCH"


def test_requires_both_classes():
    result=invent([
        LabeledRow("p1",{"a":1},True),
        LabeledRow("p2",{"a":2},True),
    ])
    assert result["status"]=="UNSUPPORTED"
    assert result["reason"]=="BOTH_CLASSES_REQUIRED"


def test_feature_pack_search_escapes_global_predicate_bound_without_heuristic_pruning():
    rows=[]
    for i in range(6):
        base={"a":i,"b":i}
        for j in range(8):
            base[f"noise{j}"]=(i+j)%5
        rows.append(LabeledRow(f"p{i}",base,True))
    for i in range(6):
        base={"a":i,"b":i+1}
        for j in range(8):
            base[f"noise{j}"]=(i*2+j)%5
        rows.append(LabeledRow(f"n{i}",base,False))
    direct=invent(rows)
    assert direct["status"] in {"SEARCH_BOUND_EXCEEDED","INVENTED_DISCRIMINATORS"}
    packed=invent_across_feature_packs(rows,max_pack_size=2,max_packs=1000)
    assert packed["status"]=="INVENTED_DISCRIMINATORS_ACROSS_FEATURE_PACKS", packed
    assert any(
        any(p["expr"][0]=="EQ" and set(p["expr"][1:])=={"a","b"} for p in d["predicates"])
        for d in packed["discriminators"]
    ), packed


def test_large_duplicate_population_compresses_before_g0():
    rows=[]
    for i in range(120):
        v=i%4
        rows.append(LabeledRow(f"p{i}",{"a":v,"b":v},True))
    for i in range(120):
        v=i%4
        rows.append(LabeledRow(f"n{i}",{"a":v,"b":(v+1)%4},False))
    result=invent(rows)
    assert result["status"]=="INVENTED_DISCRIMINATORS", result
    assert result["original_example_count"]==240
    assert result["compressed_example_count"]<128
    assert any(
        any(p["expr"][0]=="EQ" and set(p["expr"][1:])=={"a","b"} for p in d["predicates"])
        for d in result["discriminators"]
    ), result
