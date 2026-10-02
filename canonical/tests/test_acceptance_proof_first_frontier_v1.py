from __future__ import annotations
import unittest
from canonical.runtime.acceptance_proof_first_frontier_v1 import evaluate


class Tests(unittest.TestCase):
    def test_proof_beats_reality(self):
        gap = {"actions": [
            {
                "id": "RUN",
                "action_class": "REALITY_QUERY",
                "executable": True,
                "useful": True,
                "new_reality_units": 5,
                "affected_unresolved_count": 1,
                "affected_family_count": 1,
                "critical_path": True,
                "unresolved_target_predicates": ["P1"],
            },
            {
                "id": "PROVE",
                "action_class": "PROOF_SEARCH",
                "executable": True,
                "useful": True,
                "new_reality_units": 0,
                "affected_unresolved_count": 13,
                "affected_family_count": 6,
                "critical_path": False,
                "unresolved_target_predicates": ["P2"],
                "bounded_proof_action": True,
            },
        ]}
        out = evaluate(gap)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_action"]["id"], "PROVE")
        self.assertEqual(out["selection_reason"], "PROOF_FIRST_ZERO_REALITY_ACTION")

    def test_saturated_proof_allows_reality(self):
        gap = {"actions": [
            {
                "id": "RUN",
                "action_class": "REALITY_QUERY",
                "executable": True,
                "useful": True,
                "new_reality_units": 1,
                "affected_unresolved_count": 1,
                "affected_family_count": 1,
                "critical_path": True,
                "unresolved_target_predicates": ["P1"],
            },
            {
                "id": "PROVE",
                "action_class": "PROOF_SEARCH",
                "executable": True,
                "useful": True,
                "new_reality_units": 0,
                "affected_unresolved_count": 13,
                "affected_family_count": 6,
                "critical_path": True,
                "unresolved_target_predicates": ["P2"],
                "bounded_proof_action": True,
                "proof_saturated": True,
            },
        ]}
        out = evaluate(gap)
        self.assertEqual(out["selected_action"]["id"], "RUN")

    def test_largest_proof_cut_first(self):
        gap = {"actions": [
            {
                "id": "A",
                "action_class": "PROOF_COMPILE",
                "executable": True,
                "useful": True,
                "new_reality_units": 0,
                "affected_unresolved_count": 2,
                "affected_family_count": 2,
                "critical_path": True,
                "unresolved_target_predicates": ["P1", "P2"],
                "bounded_proof_action": True,
            },
            {
                "id": "B",
                "action_class": "PROOF_SEARCH",
                "executable": True,
                "useful": True,
                "new_reality_units": 0,
                "affected_unresolved_count": 13,
                "affected_family_count": 6,
                "critical_path": False,
                "unresolved_target_predicates": ["P3"],
                "bounded_proof_action": True,
            },
        ]}
        out = evaluate(gap)
        self.assertEqual(out["selected_action"]["id"], "B")


if __name__ == "__main__":
    unittest.main(verbosity=2)
