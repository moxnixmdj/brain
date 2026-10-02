from __future__ import annotations

from copy import deepcopy
import inspect
import unittest

from canonical.runtime import structured_method_expression_ast_candidate_v2 as candidate
from canonical.runtime import structured_method_expression_ast_proof_v2 as proof


CLAIMED_OPS = {
    "ref","const","add","sub","min","max","mul","div","neg","abs","pow_int",
    "exp","log","sqrt","gt","ge","lt","le","eq","neq","isclose","and","or","not","if",
}


class StructuredMethodExpressionAstV2Tests(unittest.TestCase):
    def test_candidate_is_independent_from_proof(self):
        src = inspect.getsource(candidate)
        self.assertNotIn("structured_method_expression_ast_proof_v2", src)
        self.assertNotIn("_expected", src)

    def test_randomized_cross_grammar_population_passes(self):
        out = proof.run_batch(20261002, 300, candidate.compile_graph)
        self.assertTrue(out["all_pass"], out)
        self.assertEqual(out["by_branch"]["REGULATED"]["pass"], 100)
        self.assertEqual(out["by_branch"]["STANDARD"]["pass"], 100)
        self.assertEqual(out["by_branch"]["STRESS"]["pass"], 100)
        self.assertEqual(set(out["operation_coverage"]), CLAIMED_OPS)

    def test_floating_reconstruction_regression_115(self):
        case = proof.generate_case(20261002, 115)
        out = candidate.compile_graph(proof.public_case(case))
        self.assertEqual(out["status"], "COMPILED", out)
        self.assertTrue(proof.score(case, out)["pass"], out)

    def test_recursive_expression_is_load_bearing(self):
        case = proof.generate_case(17, 2)  # stress branch uses nested if/or/mul/sub/add
        out = candidate.compile_graph(proof.public_case(case))
        self.assertTrue(proof.score(case, out)["pass"])
        bad = deepcopy(out)
        final = next(x for x in bad["nodes"] if x["rule_id"] == "R_FINAL_STRESS")
        final["evaluated_value"] = float(final["evaluated_value"]) + 1.0
        self.assertFalse(proof.score(case, bad)["pass"])

    def test_requirement_exclusion_is_load_bearing(self):
        case = proof.generate_case(29, 0)
        out = candidate.compile_graph(proof.public_case(case))
        self.assertTrue(proof.score(case, out)["pass"])
        bad = deepcopy(out)
        bad["justified_exclusions"] = []
        self.assertFalse(proof.score(case, bad)["pass"])

    def test_lineage_is_load_bearing(self):
        case = proof.generate_case(31, 1)
        out = candidate.compile_graph(proof.public_case(case))
        self.assertTrue(proof.score(case, out)["pass"])
        bad = deepcopy(out)
        bad["requirement_lineage"][0]["consumer_rule_ids"] = []
        self.assertFalse(proof.score(case, bad)["pass"])

    def test_dimension_error_fails_closed(self):
        case = proof.generate_case(37, 0)
        # Addition of currency and mass must fail dimension checking.
        case["schema_fields"][1]["dimension"] = "mass"
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DIMENSION", out["reason"])

    def test_composite_dimension_is_derived_not_declared_by_fiat(self):
        case = proof.generate_case(41, 0)
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "COMPILED", out)
        unit_price = next(x for x in out["outputs"] if x["id"] == "unit_price")
        self.assertEqual(unit_price["dimension"], "count^-1*currency")

    def test_ambiguous_branch_fails_closed(self):
        case = proof.generate_case(43, 0)
        case["branches"].append(deepcopy(case["branches"][0]))
        case["branches"][-1]["id"] = "DUPLICATE_TRUE_BRANCH"
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("BRANCH_SELECTION_NOT_UNIQUE", out["reason"])

    def test_unconsumed_applicable_requirement_fails_closed(self):
        case = proof.generate_case(47, 1)
        case["requirements"].append({"id":"REQ_ORPHAN","source_kind":"standard"})
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("WITHOUT_CONSUMER", out["reason"])

    def test_invariant_violation_fails_closed(self):
        case = proof.generate_case(53, 0)
        # Add a deliberately false invariant to an otherwise valid rule.
        case["common_rules"][0]["invariants"].append({
            "op":"lt",
            "left":{"op":"ref","id":"subtotal"},
            "right":{"op":"const","type":"number","dimension":"currency","value":-1.0},
        })
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("INVARIANT_FAILED", out["reason"])

    def test_unsupported_operation_fails_closed(self):
        case = proof.generate_case(59, 0)
        case["common_rules"][0]["expr"] = {"op":"magic_hidden_solver","arg":{"op":"ref","id":"amount_a"}}
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("UNSUPPORTED", out["reason"])

    def test_wrong_terminal_output_is_rejected_by_independent_oracle(self):
        case = proof.generate_case(61, 2)
        out = candidate.compile_graph(case)
        self.assertTrue(proof.score(case, out)["pass"])
        bad = deepcopy(out)
        bad["outputs"][0]["value"] = float(bad["outputs"][0]["value"]) + 0.5
        self.assertFalse(proof.score(case, bad)["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
