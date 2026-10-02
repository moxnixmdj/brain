from __future__ import annotations

from copy import deepcopy
import inspect
import unittest

from canonical.runtime import structured_method_graph_candidate_v1 as candidate
from canonical.runtime import structured_method_graph_proof_v1 as proof


class StructuredMethodWholeDimensionTests(unittest.TestCase):
    def test_candidate_does_not_import_oracle(self):
        src = inspect.getsource(candidate)
        self.assertNotIn("structured_method_graph_proof_v1", src)
        self.assertNotIn("_oracle", src)

    def test_generated_population_passes_both_branches(self):
        out = proof.run_batch(20261002, 80, candidate.compile_graph)
        self.assertTrue(out["all_pass"], out)
        self.assertEqual(out["by_branch"]["REGULATED"]["pass"], 40)
        self.assertEqual(out["by_branch"]["STANDARD"]["pass"], 40)

    def test_missing_intermediate_fails_oracle(self):
        case = proof.generate_case(9, 0)
        out = candidate.compile_graph(proof.public_case(case))
        self.assertEqual(out["status"], "COMPILED")
        bad = deepcopy(out)
        bad["nodes"] = [x for x in bad["nodes"] if x["rule_id"] != "R_SUBTOTAL"]
        self.assertFalse(proof.score(case, bad)["pass"])

    def test_wrong_exclusion_fails_oracle(self):
        case = proof.generate_case(9, 1)
        out = candidate.compile_graph(proof.public_case(case))
        bad = deepcopy(out)
        bad["justified_exclusions"] = []
        self.assertFalse(proof.score(case, bad)["pass"])

    def test_dimension_mismatch_fails_closed(self):
        case = proof.generate_case(9, 0)
        case["schema_fields"][1]["dimension"] = "mass"
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("DIMENSION", out["reason"])

    def test_ambiguous_branch_fails_closed(self):
        case = proof.generate_case(9, 0)
        case["branches"].append({
            "id": "ALSO",
            "when": [{"field": "mode", "op": "eq", "value": "regulated"}],
            "rules": deepcopy(case["branches"][0]["rules"]),
        })
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("BRANCH_SELECTION_NOT_UNIQUE", out["reason"])

    def test_applicable_requirement_without_consumer_fails_closed(self):
        case = proof.generate_case(9, 0)
        case["requirements"].append({"id": "REQ_UNCONSUMED", "source_kind": "standard"})
        out = candidate.compile_graph(case)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("WITHOUT_CONSUMER", out["reason"])

    def test_wrong_output_value_fails_oracle(self):
        case = proof.generate_case(9, 0)
        out = candidate.compile_graph(case)
        bad = deepcopy(out)
        bad["outputs"][0]["value"] += 1
        self.assertFalse(proof.score(case, bad)["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
