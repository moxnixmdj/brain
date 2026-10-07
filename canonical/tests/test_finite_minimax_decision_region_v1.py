import unittest

from canonical.runtime.finite_minimax_decision_region_v1 import solve


class FiniteMinimaxDecisionRegionTests(unittest.TestCase):
    def test_common_policy_stops_without_observation(self):
        out = solve({
            "hypothesis_set_complete": True,
            "worlds": [{"world_id": "w1"}, {"world_id": "w2"}],
            "policy_regions": [{
                "policy_id": "p",
                "world_ids": ["w1", "w2"],
                "region_complete": True,
            }],
            "observations": [],
        })
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"], "PASS__COMMON_POLICY_ALREADY_COVERS_VERSION_SPACE")
        self.assertEqual(out["minimum_worst_case_cost_units"], 0.0)

    def test_overlap_case_needs_one_query_not_world_identification(self):
        out = solve({
            "hypothesis_set_complete": True,
            "worlds": [{"world_id": "w1"}, {"world_id": "w2"}, {"world_id": "w3"}],
            "policy_regions": [
                {"policy_id": "p1", "world_ids": ["w1", "w3"], "region_complete": True},
                {"policy_id": "p2", "world_ids": ["w1", "w2"], "region_complete": True},
                {"policy_id": "p3", "world_ids": ["w2", "w3"], "region_complete": True},
            ],
            "observations": [{
                "observation_id": "q",
                "cost_units": 1,
                "outcome_map_complete": True,
                "outcomes": {"w1": "a", "w2": "b", "w3": "b"},
            }],
        })
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"], "PASS__EXACT_MINIMAX_DECISION_REGION_POLICY")
        self.assertEqual(out["first_observation_id"], "q")
        self.assertEqual(out["minimum_worst_case_cost_units"], 1.0)

    def test_cheaper_equally_resolving_query_wins(self):
        base = {
            "hypothesis_set_complete": True,
            "worlds": [{"world_id": "w1"}, {"world_id": "w2"}],
            "policy_regions": [
                {"policy_id": "p1", "world_ids": ["w1"], "region_complete": True},
                {"policy_id": "p2", "world_ids": ["w2"], "region_complete": True},
            ],
        }
        base["observations"] = [
            {
                "observation_id": "expensive",
                "cost_units": 5,
                "outcome_map_complete": True,
                "outcomes": {"w1": "x", "w2": "y"},
            },
            {
                "observation_id": "cheap",
                "cost_units": 1,
                "outcome_map_complete": True,
                "outcomes": {"w1": "x", "w2": "y"},
            },
        ]
        out = solve(base)
        self.assertEqual(out["first_observation_id"], "cheap")

    def test_indistinguishable_incompatible_worlds_fail_closed(self):
        out = solve({
            "hypothesis_set_complete": True,
            "worlds": [{"world_id": "w1"}, {"world_id": "w2"}],
            "policy_regions": [
                {"policy_id": "p1", "world_ids": ["w1"], "region_complete": True},
                {"policy_id": "p2", "world_ids": ["w2"], "region_complete": True},
            ],
            "observations": [{
                "observation_id": "q",
                "cost_units": 1,
                "outcome_map_complete": True,
                "outcomes": {"w1": "same", "w2": "same"},
            }],
        })
        self.assertFalse(out["pass"])
        self.assertIn(["w1", "w2"], out["unresolved_pair_witnesses"])

    def test_incomplete_region_fails_closed(self):
        out = solve({
            "hypothesis_set_complete": True,
            "worlds": [{"world_id": "w1"}],
            "policy_regions": [{
                "policy_id": "p",
                "world_ids": ["w1"],
                "region_complete": False,
            }],
            "observations": [],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "POLICY_REGION_COMPLETENESS_UNPROVED:p")


if __name__ == "__main__":
    unittest.main()
