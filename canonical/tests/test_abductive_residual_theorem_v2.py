from __future__ import annotations
import unittest

from canonical.runtime.abductive_residual_theorem_v2 import evaluate


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
    def test_simple_exact_compatibility(self):
        out = evaluate({
            "targets": ["T"],
            "baseline_facts": ["A"],
            "implications": [edge("e1", ["A", "B"], ["T"])],
        })
        self.assertEqual(out["status"], "EXACT_WEAKEST_SUFFICIENT_RESIDUALS_COMPUTED")
        self.assertTrue(out["exact"])
        self.assertEqual(out["target_residuals"]["T"]["minimum_residual_sets"], [["B"]])

    def test_joint_can_need_locally_nonshortest_alternative(self):
        doc = {
            "targets": ["T1", "T2"],
            "baseline_facts": [],
            "implications": [
                edge("t1-short", ["A"], ["T1"]),
                edge("t1-shared", ["B", "C"], ["T1"]),
                edge("t2-shared", ["B", "C"], ["T2"]),
            ],
        }
        out = evaluate(doc)
        self.assertTrue(out["exact"])
        self.assertEqual(out["target_residuals"]["T1"]["minimum_residual_sets"], [["A"]])
        self.assertIn(["B", "C"], out["target_residuals"]["T1"]["all_inclusion_minimal_residual_sets"])
        self.assertEqual(out["minimum_joint_residual_size"], 2)
        self.assertEqual(out["minimum_joint_residual_sets"], [["B", "C"]])

    def test_cap_binding_is_explicitly_incomplete(self):
        implications = []
        groups = []
        for i in range(8):
            g = f"G{i}"
            groups.append(g)
            implications.append(edge(f"x{i}", [f"X{i}"], [g]))
            implications.append(edge(f"y{i}", [f"Y{i}"], [g]))
        implications.append(edge("terminal", groups, ["T"]))
        out = evaluate({
            "targets": ["T"],
            "baseline_facts": [],
            "implications": implications,
        })
        self.assertEqual(out["status"], "BOUNDED_INCOMPLETE__NO_GLOBAL_EXACTNESS_CLAIM")
        self.assertFalse(out["exact"])
        self.assertTrue(out["bounded_incomplete"])
        self.assertTrue(out["bounded_events"])

    def test_cycle_does_not_self_prove(self):
        out = evaluate({
            "targets": ["T"],
            "baseline_facts": [],
            "implications": [
                edge("e1", ["A"], ["T"]),
                edge("e2", ["T"], ["A"]),
            ],
        })
        self.assertEqual(out["status"], "RESIDUAL_GRAPH_CONTAINS_UNREACHABLE_TARGETS")
        self.assertFalse(out["exact"])

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
