"""Independent adversarial verification for the structured-method universal ceiling candidate.

This test uses the exact bound compiler and its independent structural oracle.
It demonstrates that the current proof route accepts a witness whose declared
invariants are mutually inconsistent, because both programs preserve invariant
text but neither checks semantic consistency. It also shows that the emitted
acceptance plan is invariant across different operator identities rather than an
operator-specific independently generated consequence.

The frozen behavioral contract requires invariant consistency and independently
generated acceptance checks for each material graph edge. Therefore the current
compiler+oracle route does not establish that success condition universally.
"""
from canonical.runtime.structured_method_normalized_rule_graph_v3 import compile_graph
from canonical.runtime.structured_method_normalized_rule_oracle_v3 import score


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


def test_compiler_and_oracle_accept_semantically_inconsistent_invariants():
    public = _task("IDENTITY")
    candidate = compile_graph(public)
    assert candidate["status"] == "COMPILED"
    assert score(public, candidate) == {"pass": True, "reason": "PASS"}
    invariants = candidate["rules"][0]["invariants"]
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
