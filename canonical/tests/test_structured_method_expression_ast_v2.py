from __future__ import annotations

import unittest

from canonical.runtime.structured_method_expression_ast_candidate_v2 import compile_graph
from canonical.runtime.structured_method_expression_ast_proof_v2 import generate_case, public_case, run_batch


class StructuredMethodExpressionASTV2Tests(unittest.TestCase):
    def test_generated_population_passes_independent_oracle(self):
        out = run_batch(20261002,  ninety_six := 96, compile_graph)
        self.assertEqual(out["case_count"], ninety_six)
        self.assertTrue(out["all_pass"], out["failures"][:5])
        self.assertEqual(out["failed"], 0)
        self.assertEqual(set(out["by_branch"]), {"REGULATED", "STANDARD", "STRESS"})
        required_ops = {
            "ref", "const", "add", "sub", "min", "max", "mul", "div",
            "abs", "pow_int", "gt", "ge", "lt", "eq", "and", "or", "not", "if",
        }
        self.assertTrue(required_ops.issubset(set(out["operation_coverage"])))

    def test_dimension_mismatch_fails_closed(self):
        case = generate_case(17, 0)
        case["common_rules"][0]["output_dimension"] = "count"
        out = compile_graph(public_case(case))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DECLARED_OUTPUT_TYPE_OR_DIMENSION_MISMATCH", out["reason"])

    def test_missing_requirement_consumer_fails_closed(self):
        case = generate_case(17, 1)
        case["common_rules"] = [
            r for r in case["common_rules"]
            if "REQ_CALLOUT" not in r.get("consumes_requirements", [])
        ]
        out = compile_graph(public_case(case))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("APPLICABLE_REQUIREMENT_WITHOUT_CONSUMER", out["reason"])

    def test_ambiguous_branch_fails_closed(self):
        case = generate_case(17, 0)
        case["branches"].append(dict(case["branches"][0], id="DUPLICATE"))
        out = compile_graph(public_case(case))
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("BRANCH_SELECTION_NOT_UNIQUE", out["reason"])


if __name__ == "__main__":
    unittest.main()
