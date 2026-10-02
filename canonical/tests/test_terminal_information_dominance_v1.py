import unittest

from canonical.runtime.terminal_information_dominance_v1 import evaluate


class Tests(unittest.TestCase):
    def test_exact_dominance_and_full_bundle(self):
        doc = {
            "unresolved_predicates": ["P1", "P2", "P3"],
            "certificates": [
                {"id": "A", "target_predicates": ["P1", "P2"], "requires": ["R1"], "new_reality_units": 0},
                {"id": "B", "target_predicates": ["P1"], "requires": ["R1", "R2"], "new_reality_units": 0},
                {"id": "C", "target_predicates": ["P3"], "requires": ["R3"], "new_reality_units": 0},
            ],
        }
        out = evaluate(doc)
        self.assertEqual(out["status"], "EXACT_INFORMATION_DOMINANCE_COMPUTED")
        self.assertEqual(out["dominated_certificate_ids"], ["B"])
        self.assertEqual(out["dominated_by"]["B"], ["A"])
        self.assertEqual(out["best_full_frontier_bundle"]["certificate_ids"], ["A", "C"])
        self.assertEqual(out["best_full_frontier_bundle"]["unique_requirement_count"], 2)
        self.assertTrue(out["reality_cost_degenerate_for_ordering"])
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])

    def test_shared_requirement_synergy_is_structural_only(self):
        doc = {
            "unresolved_predicates": ["P1", "P2"],
            "certificates": [
                {"id": "A", "target_predicates": ["P1"], "requires": ["SHARED", "RA"], "new_reality_units": 0},
                {"id": "B", "target_predicates": ["P2"], "requires": ["SHARED", "RB"], "new_reality_units": 0},
            ],
        }
        out = evaluate(doc, max_synergy_order=2)
        row = out["synergy_bundles"][0]
        self.assertEqual(row["certificate_ids"], ["A", "B"])
        self.assertEqual(row["shared_requirement_savings"], 1)
        self.assertEqual(row["covered_predicate_count"], 2)

    def test_distinct_scope_requirements_remain_distinct(self):
        doc = {
            "unresolved_predicates": ["P1", "P2"],
            "certificates": [
                {"id": "A", "target_predicates": ["P1"], "requires": ["TOOL_SCOPE_COMPLETE"], "new_reality_units": 0},
                {"id": "B", "target_predicates": ["P2"], "requires": ["DELEGATION_SCOPE_COMPLETE"], "new_reality_units": 0},
            ],
        }
        out = evaluate(doc, max_synergy_order=2)
        rows = [r for r in out["synergy_bundles"] if r["certificate_ids"] == ["A", "B"]]
        self.assertEqual(rows[0]["shared_requirement_savings"], 0)

    def test_fail_closed_on_outside_target(self):
        doc = {
            "unresolved_predicates": ["P1"],
            "certificates": [{"id": "A", "target_predicates": ["P2"], "requires": ["R"], "new_reality_units": 0}],
        }
        out = evaluate(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CERTIFICATE_TARGETS_INVALID:A", out["errors"])

    def test_fail_closed_on_empty_requirements(self):
        doc = {
            "unresolved_predicates": ["P1"],
            "certificates": [{"id": "A", "target_predicates": ["P1"], "requires": [], "new_reality_units": 0}],
        }
        out = evaluate(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CERTIFICATE_REQUIRES_INVALID:A", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
