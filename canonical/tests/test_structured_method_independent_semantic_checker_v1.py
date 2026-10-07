from canonical.runtime.structured_method_independent_semantic_checker_v1 import verify

def base(expr=None, invariant=None):
    expr = expr or {
        "op":"add",
        "left":{"op":"ref","id":"x"},
        "right":{"op":"const","type":"number","dimension":"score","value":1.0},
    }
    invariant = invariant if invariant is not None else {
        "op":"gt","left":{"op":"ref","id":"y"},"right":{"op":"ref","id":"x"}
    }
    return {
        "schema_fields":[
            {"id":"x","type":"number","dimension":"score","value":2.0},
        ],
        "requirements":[{"id":"R1","source_kind":"constraint"}],
        "common_rules":[{
            "id":"RULE1",
            "expr":expr,
            "output":"y",
            "output_type":"number",
            "output_dimension":"score",
            "consumes_requirements":["R1"],
            "invariants":[invariant] if invariant else [],
        }],
        "branches":[{
            "id":"ONLY",
            "when":{"op":"const","type":"boolean","dimension":"dimensionless","value":True},
            "rules":[],
        }],
        "required_outputs":["y"],
    }

def test_passes_typed_invariant_and_independent_edge_sensitivity():
    out=verify(base())
    assert out["pass"] is True, out
    assert out["material_edge_count"] == 1
    assert out["invariant_check_count"] == 1
    assert out["edge_sensitivity_witnesses"][0]["ref_id"] == "x"

def test_rejects_old_false_invariant_failure_mode():
    bad={
        "op":"lt","left":{"op":"ref","id":"y"},"right":{"op":"ref","id":"x"}
    }
    out=verify(base(invariant=bad))
    assert out["pass"] is False
    assert "PRIMARY_COMPILER_REJECTED" in out["reason"]

def test_rejects_semantically_redundant_edge_even_when_graph_compiles():
    cancel={
        "op":"sub",
        "left":{"op":"ref","id":"x"},
        "right":{"op":"ref","id":"x"},
    }
    neutral={
        "op":"eq",
        "left":{"op":"ref","id":"y"},
        "right":{"op":"const","type":"number","dimension":"score","value":0.0},
    }
    out=verify(base(expr=cancel, invariant=neutral))
    assert out["pass"] is False
    assert "NO_INDEPENDENT_EDGE_SENSITIVITY_WITNESS:RULE1:x" in out["reason"]

def test_rejects_branch_or_domain_failure_fail_closed():
    bad=base(expr={"op":"log","arg":{"op":"ref","id":"x"}})
    bad["schema_fields"][0]["dimension"]="dimensionless"
    bad["schema_fields"][0]["value"]=-1.0
    bad["common_rules"][0]["output_dimension"]="dimensionless"
    bad["common_rules"][0]["invariants"]=[]
    out=verify(bad)
    assert out["pass"] is False
    assert "PRIMARY_COMPILER_REJECTED" in out["reason"]

def test_boolean_edge_sensitivity():
    public={
        "schema_fields":[{"id":"flag","type":"boolean","dimension":"dimensionless","value":True}],
        "requirements":[{"id":"R1","source_kind":"constraint"}],
        "common_rules":[{
            "id":"RULE1",
            "expr":{"op":"not","arg":{"op":"ref","id":"flag"}},
            "output":"y","output_type":"boolean","output_dimension":"dimensionless",
            "consumes_requirements":["R1"],"invariants":[],
        }],
        "branches":[{"id":"ONLY","when":{"op":"const","type":"boolean","dimension":"dimensionless","value":True},"rules":[]}],
        "required_outputs":["y"],
    }
    out=verify(public)
    assert out["pass"] is True, out
    assert out["material_edge_count"] == 1
