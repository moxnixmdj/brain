"""Independent adversarial verification for the structured-method universal ceiling candidate.

This test uses the exact bound compiler contract and demonstrates two facts:
1. mutually inconsistent declared invariants are preserved as text but are not checked,
   yet the compiler returns COMPILED;
2. the emitted acceptance plan is a fixed checklist, not an independently generated
   discriminating consequence of the rule/operator.

Therefore the current compiler cannot by itself establish the behavioral-contract
success condition requiring invariant consistency and independently generated
acceptance checks for each material graph edge.
"""
from canonical.runtime.structured_method_normalized_rule_graph_v3 import compile_graph


def _task(operator: str):
    return {
        "behavior_id": "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
        "task": {
            "inputs": [
                {"id": "x", "type": "scalar", "dimension": "dimensionless"},
            ],
            "requirements": [
                {"id": "REQ1", "source_kind": "formula", "status": "applicable"},
            ],
            "normalized_rules": [
                {
                    "id": "R1",
                    "inputs": ["x"],
                    "output": "y",
                    "operator": operator,
                    "input_contracts": [
                        {"type": "scalar", "dimension": "dimensionless"},
                    ],
                    "type": "scalar",
                    "dimension": "dimensionless",
                    "consumes_requirements": ["REQ1"],
                    "invariants": [
                        {
                            "kind": "RANGE",
                            "statement": "OUTPUT y MUST BE STRICTLY POSITIVE",
                        },
                        {
                            "kind": "RANGE",
                            "statement": "OUTPUT y MUST BE NONPOSITIVE",
                        },
                    ],
                }
            ],
            "required_outputs": ["y"],
        },
    }


def test_inconsistent_invariants_do_not_fail_closed():
    result = compile_graph(_task("IDENTITY"))
    assert result["status"] == "COMPILED"
    invariants = result["rules"][0]["invariants"]
    assert [x["statement"] for x in invariants] == [
        "OUTPUT y MUST BE STRICTLY POSITIVE",
        "OUTPUT y MUST BE NONPOSITIVE",
    ]


def test_acceptance_plan_is_not_operator_discriminating():
    a = compile_graph(_task("IDENTITY"))
    b = compile_graph(_task("NEGATE"))
    assert a["status"] == "COMPILED"
    assert b["status"] == "COMPILED"
    assert a["acceptance_checks"] == b["acceptance_checks"]
    assert a["rules"][0]["operator"] != b["rules"][0]["operator"]
