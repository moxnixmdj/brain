from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Tests(unittest.TestCase):
    def test_parent_to_children_is_exact_partition(self):
        frontier = json.loads((ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
        candidate = json.loads((ROOT / "canonical/governance/MULTITARGET_CERTIFICATE_TARGET_REFINEMENT_CANDIDATE_V1.json").read_text())
        by_id = {row["id"]: row for row in frontier["certificate_candidates"]}

        for parent_spec in candidate["parents"]:
            parent = by_id[parent_spec["certificate_id"]]
            child_targets = []
            child_requires = []
            seen_targets = set()
            seen_requires = set()
            for child in parent_spec["children"]:
                self.assertEqual(len(child["target_predicates"]), 1)
                self.assertEqual(len(child["requires"]), 1)
                t = child["target_predicates"][0]
                r = child["requires"][0]
                self.assertNotIn(t, seen_targets)
                self.assertNotIn(r, seen_requires)
                seen_targets.add(t)
                seen_requires.add(r)
                child_targets.append(t)
                child_requires.append(r)

            self.assertEqual(sorted(child_targets), sorted(parent["target_predicates"]))
            self.assertEqual(sorted(child_requires), sorted(parent["requires"]))

        self.assertEqual(candidate["capability_credit_delta"], 0)
        self.assertEqual(candidate["family_credit_delta"], 0)
        self.assertFalse(candidate["execution_authority"])
        self.assertFalse(candidate["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
