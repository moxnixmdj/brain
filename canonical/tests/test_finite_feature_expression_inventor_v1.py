from canonical.runtime.finite_feature_expression_inventor_v1 import (
    LabeledRow,
    evaluate,
    invent,
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
