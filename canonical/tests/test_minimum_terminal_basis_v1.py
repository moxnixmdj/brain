from __future__ import annotations
import copy
import unittest

from canonical.runtime.minimum_terminal_basis_v1 import evaluate


def base():
    return {
        "targets": ["T1", "T2"],
        "baseline_facts": ["B"],
        "candidate_facts": ["A", "C", "D"],
        "implications": [
            {"edge_id": "e1", "if_all": ["A"], "then": ["T1"], "verified": True, "independent": True, "receipt": "r://e1"},
            {"edge_id": "e2", "if_all": ["A", "B"], "then": ["T2"], "verified": True, "independent": True, "receipt": "r://e2"},
            {"edge_id": "e3", "if_all": ["C", "D"], "then": ["T1", "T2"], "verified": True, "independent": True, "receipt": "r://e3"},
        ],
        "terminal_false_worlds": [
            {"world_id": "w1", "eliminated_by": ["A", "C"]},
            {"world_id": "w2", "eliminated_by": ["A", "D"]},
        ],
    }


class Tests(unittest.TestCase):
    def test_minimum_basis_prefers_single_stronger_fact(self):
        out = evaluate(base())
        self.assertEqual(out["status"], "EXACT_MINIMUM_TERMINAL_BASIS_AND_HITTING_SET_COMPUTED")
        self.assertEqual(out["minimum_generating_basis_size"], 1)
        self.assertEqual(out["minimum_generating_bases"], [["A"]])

    def test_hitting_set_exact(self):
        out = evaluate(base())
        self.assertEqual(out["minimum_false_world_hitting_set_size"], 1)
        self.assertEqual(out["minimum_false_world_hitting_sets"], [["A"]])
        self.assertEqual(out["minimum_joint_terminal_cuts"], [["A"]])

    def test_transitive_closure(self):
        d = base()
        d["targets"] = ["Z"]
        d["candidate_facts"] = ["A"]
        d["terminal_false_worlds"] = []
        d["implications"] = [
            {"edge_id":"x","if_all":["A"],"then":["Y"],"verified":True,"independent":True,"receipt":"r://x"},
            {"edge_id":"y","if_all":["Y"],"then":["Z"],"verified":True,"independent":True,"receipt":"r://y"},
        ]
        out = evaluate(d)
        self.assertEqual(out["minimum_generating_bases"], [["A"]])

    def test_unverified_edge_fails_closed(self):
        d = base()
        d["implications"][0]["verified"] = False
        self.assertEqual(evaluate(d)["status"], "FAIL_CLOSED")

    def test_unreachable_targets_do_not_fake_basis(self):
        d = base()
        d["targets"] = ["NEVER"]
        out = evaluate(d)
        self.assertFalse(out["all_targets_derivable"])
        self.assertEqual(out["minimum_generating_bases"], [])

    def test_unknown_world_eliminator_fails_closed(self):
        d = base()
        d["terminal_false_worlds"][0]["eliminated_by"].append("UNKNOWN")
        self.assertEqual(evaluate(d)["status"], "FAIL_CLOSED")

    def test_candidate_limit_fails_closed(self):
        d = base()
        d["candidate_facts"] = [f"C{i}" for i in range(25)]
        d["terminal_false_worlds"] = []
        self.assertEqual(evaluate(d)["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
