from __future__ import annotations
import unittest

from canonical.runtime.abductive_residual_theorem_v1 import evaluate


def edge(edge_id, lhs, rhs):
    return {
        "edge_id": edge_id,
        "if_all": lhs,
        "then": rhs,
        "verified": True,
        "independent": True,
        "receipt": "r://" + edge_id,
    }


class Tests(unittest.TestCase):
    def test_synthesizes_unlisted_leaf_residual(self):
        doc = {
            "targets": ["T"],
            "baseline_facts": ["A"],
            "implications": [edge("e1", ["A", "B"], ["T"])],
        }
        out = evaluate(doc)
        self.assertEqual(out["status"], "EXACT_WEAKEST_SUFFICIENT_RESIDUALS_COMPUTED")
        self.assertEqual(out["target_residuals"]["T"]["minimum_residual_sets"], [["B"]])
        self.assertEqual(out["primitive_residual_facts"], ["B"])

    def test_transitive_backward_residual(self):
        doc = {
            "targets": ["T"],
            "baseline_facts": ["A"],
            "implications": [
                edge("e1", ["A", "B"], ["Y"]),
                edge("e2", ["Y", "C"], ["T"]),
            ],
        }
        out = evaluate(doc)
        self.assertEqual(out["target_residuals"]["T"]["minimum_residual_sets"], [["B", "C"]])

    def test_prefers_weaker_alternative_proof(self):
        doc = {
            "targets": ["T"],
            "baseline_facts": [],
            "implications": [
                edge("e1", ["A"], ["T"]),
                edge("e2", ["B", "C"], ["T"]),
            ],
        }
        out = evaluate(doc)
        self.assertEqual(out["target_residuals"]["T"]["minimum_residual_sets"], [["A"]])

    def test_equal_size_alternatives_preserved(self):
        doc = {
            "targets": ["T"],
            "baseline_facts": [],
            "implications": [
                edge("e1", ["A"], ["T"]),
                edge("e2", ["B"], ["T"]),
            ],
        }
        out = evaluate(doc)
        self.assertEqual(out["target_residuals"]["T"]["minimum_residual_sets"], [["A"], ["B"]])

    def test_shared_residual_quotient(self):
        doc = {
            "targets": ["T1", "T2"],
            "baseline_facts": ["K"],
            "implications": [
                edge("e1", ["K", "X"], ["T1"]),
                edge("e2", ["K", "X"], ["T2"]),
            ],
        }
        out = evaluate(doc)
        self.assertEqual(out["minimum_joint_residual_sets"], [["X"]])
        self.assertEqual(out["shared_residual_groups"][0]["targets"], ["T1", "T2"])

    def test_joint_residual_deduplicates_shared_fact(self):
        doc = {
            "targets": ["T1", "T2"],
            "baseline_facts": [],
            "implications": [
                edge("e1", ["X", "A"], ["T1"]),
                edge("e2", ["X", "B"], ["T2"]),
            ],
        }
        out = evaluate(doc)
        self.assertEqual(out["minimum_joint_residual_sets"], [["A", "B", "X"]])

    def test_known_target_needs_empty_residual(self):
        out = evaluate({"targets": ["T"], "baseline_facts": ["T"], "implications": []})
        self.assertEqual(out["target_residuals"]["T"]["minimum_residual_sets"], [[]])

    def test_cycle_does_not_self_prove(self):
        doc = {
            "targets": ["T"],
            "baseline_facts": [],
            "implications": [
                edge("e1", ["A"], ["T"]),
                edge("e2", ["T"], ["A"]),
            ],
        }
        out = evaluate(doc)
        self.assertEqual(out["status"], "RESIDUAL_GRAPH_CONTAINS_UNREACHABLE_TARGETS")
        self.assertFalse(out["target_residuals"]["T"]["reachable"])

    def test_unverified_edge_fails_closed(self):
        bad = edge("e1", ["A"], ["T"])
        bad["verified"] = False
        out = evaluate({"targets": ["T"], "baseline_facts": [], "implications": [bad]})
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_receipt_required(self):
        bad = edge("e1", ["A"], ["T"])
        bad["receipt"] = ""
        out = evaluate({"targets": ["T"], "baseline_facts": [], "implications": [bad]})
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_no_credit_or_authority(self):
        out = evaluate({
            "targets": ["T"],
            "baseline_facts": [],
            "implications": [edge("e1", ["A"], ["T"])],
        })
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
