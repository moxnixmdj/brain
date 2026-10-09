from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime.structured_method_edge_consequence_certificate_v1 import verify
from canonical.runtime.structured_method_expression_ast_candidate_v2 import compile_graph
from canonical.runtime.structured_method_expression_ast_proof_v2 import score


def ref(x: str):
    return {"op": "ref", "id": x}


def num(v: float):
    return {"op": "const", "type": "number", "dimension": "dimensionless", "value": float(v)}


def case():
    return {
        "schema_fields": [
            {"id": "x", "type": "number", "dimension": "dimensionless", "value": 2.0},
            {"id": "y", "type": "number", "dimension": "dimensionless", "value": 3.0},
            {"id": "mode", "type": "enum", "dimension": "dimensionless", "value": "go"},
        ],
        "requirements": [
            {"id": "REQ_SUM", "source_kind": "formula"},
            {"id": "REQ_SCALE", "source_kind": "formula"},
            {"id": "REQ_FINAL", "source_kind": "standard"},
        ],
        "common_rules": [
            {
                "id": "R_SUM",
                "expr": {"op": "add", "left": ref("x"), "right": ref("y")},
                "output": "z",
                "output_type": "number",
                "output_dimension": "dimensionless",
                "consumes_requirements": ["REQ_SUM"],
                "invariants": [
                    {"op": "gt", "left": ref("z"), "right": num(0)},
                    {"op": "eq", "left": ref("z"), "right": num(5)},
                ],
            },
            {
                "id": "R_SCALE",
                "expr": {"op": "mul", "left": ref("z"), "right": num(2)},
                "output": "scaled",
                "output_type": "number",
                "output_dimension": "dimensionless",
                "consumes_requirements": ["REQ_SCALE"],
                "invariants": [
                    {"op": "eq", "left": ref("scaled"), "right": num(10)},
                ],
            },
        ],
        "branches": [
            {
                "id": "GO",
                "when": {
                    "op": "eq",
                    "left": ref("mode"),
                    "right": {"op": "const", "type": "enum", "dimension": "dimensionless", "value": "go"},
                },
                "rules": [
                    {
                        "id": "R_FINAL",
                        "expr": {"op": "add", "left": ref("scaled"), "right": num(1)},
                        "output": "final",
                        "output_type": "number",
                        "output_dimension": "dimensionless",
                        "consumes_requirements": ["REQ_FINAL"],
                        "invariants": [
                            {"op": "eq", "left": ref("final"), "right": num(11)},
                        ],
                    }
                ],
            }
        ],
        "required_outputs": ["final"],
    }


def certificates():
    return [
        {"rule_id": "R_SUM", "source_id": "x", "alternate_value": 4.0},
        {"rule_id": "R_SUM", "source_id": "y", "alternate_value": 5.0},
        {"rule_id": "R_SCALE", "source_id": "z", "alternate_value": 6.0},
        {"rule_id": "R_FINAL", "source_id": "scaled", "alternate_value": 12.0},
    ]


class Tests(unittest.TestCase):
    def test_admitted_case_passes_existing_candidate_and_independent_oracle(self):
        public = case()
        out = compile_graph(public)
        self.assertEqual(out["status"], "COMPILED", out)
        self.assertTrue(score(public, out)["pass"])

    def test_semantic_invariants_and_every_rule_edge_have_witnesses(self):
        out = verify(case(), certificates())
        self.assertEqual(out["status"], "PASS", out)
        self.assertTrue(out["invariant_semantics_checked"])
        self.assertTrue(out["edge_consequence_coverage_complete"])
        self.assertEqual(out["semantic_edge_witness_count"], 4)
        self.assertFalse(out["whole_leaf_credit"])

    def test_contradictory_or_false_invariant_fails_closed(self):
        public = case()
        public["common_rules"][0]["invariants"].append(
            {"op": "eq", "left": ref("z"), "right": num(6)}
        )
        out = verify(public, certificates())
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("INVARIANT_SEMANTIC_FAILURE", out["reason"])

    def test_missing_edge_certificate_fails_closed(self):
        out = verify(case(), certificates()[:-1])
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("CERTIFICATE_COVERAGE_MISMATCH", out["reason"])

    def test_nonconsequential_witness_fails_closed(self):
        bad = certificates()
        bad[0] = {"rule_id": "R_SUM", "source_id": "x", "alternate_value": 2.0}
        out = verify(case(), bad)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("ALTERNATE_EQUALS_BASELINE", out["reason"])

    def test_wrong_but_distinct_witness_that_does_not_change_output_fails_closed(self):
        public = case()
        public["common_rules"][1]["expr"] = {
            "op": "mul",
            "left": ref("z"),
            "right": num(0),
        }
        public["common_rules"][1]["invariants"] = [
            {"op": "eq", "left": ref("scaled"), "right": num(0)}
        ]
        public["branches"][0]["rules"][0]["invariants"] = [
            {"op": "eq", "left": ref("final"), "right": num(1)}
        ]
        out = verify(public, certificates())
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("NO_SEMANTIC_EDGE_CONSEQUENCE", out["reason"])

    def test_opaque_invariant_is_not_smuggled_into_typed_claim(self):
        public = case()
        public["common_rules"][0]["invariants"] = [
            {"kind": "equality", "statement": "z == 5"}
        ]
        out = verify(public, certificates())
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_extra_certificate_fails_closed(self):
        bad = certificates() + [
            {"rule_id": "R_SUM", "source_id": "mode", "alternate_value": "stop"}
        ]
        out = verify(case(), bad)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("CERTIFICATE_COVERAGE_MISMATCH", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
