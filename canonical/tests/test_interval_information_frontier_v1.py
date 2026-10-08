import unittest

from canonical.runtime.interval_information_frontier_v1 import solve


def world(world_id, signature):
    return {
        "world_id": world_id,
        "terminal_signature_complete": True,
        "terminal_signature": {"output_class": signature},
    }


def query(query_id, intervals, cost=1):
    return {
        "query_id": query_id,
        "cost_units": cost,
        "prediction_intervals_complete": True,
        "prediction_intervals": intervals,
    }


class IntervalInformationFrontierTests(unittest.TestCase):
    def base(self):
        return {
            "hypothesis_cover_complete": True,
            "interval_soundness_bound": True,
            "worlds": [world("a", "A"), world("b", "B")],
            "queries": [query("q", {"a": [0, 1], "b": [2, 3]})],
        }

    def test_disjoint_intervals_resolve_in_one_query(self):
        out = solve(self.base())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["first_query_id"], "q")
        self.assertEqual(out["minimum_worst_case_cost_units"], 1.0)

    def test_terminal_equivalent_worlds_need_no_query(self):
        p = self.base()
        p["worlds"] = [world("a", "SAME"), world("b", "SAME")]
        out = solve(p)
        self.assertTrue(out["pass"], out)
        self.assertIsNone(out["first_query_id"])
        self.assertEqual(out["minimum_worst_case_cost_units"], 0.0)

    def test_overlap_that_can_preserve_all_worlds_is_not_guaranteed_progress(self):
        p = self.base()
        p["queries"] = [query("q", {"a": [0, 2], "b": [1, 3]})]
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertIn("NOT_WORST_CASE_SEPARABLE", out["status"])

    def test_two_step_noisy_policy(self):
        p = {
            "hypothesis_cover_complete": True,
            "interval_soundness_bound": True,
            "worlds": [
                world("a", "A"),
                world("b", "B"),
                world("c", "C"),
                world("d", "D"),
            ],
            "queries": [
                query(
                    "split_ab_cd",
                    {
                        "a": [0.0, 0.1],
                        "b": [0.0, 0.1],
                        "c": [1.0, 1.1],
                        "d": [1.0, 1.1],
                    },
                ),
                query(
                    "split_a_b",
                    {
                        "a": [0.0, 0.1],
                        "b": [1.0, 1.1],
                        "c": [0.0, 1.1],
                        "d": [0.0, 1.1],
                    },
                ),
                query(
                    "split_c_d",
                    {
                        "a": [0.0, 1.1],
                        "b": [0.0, 1.1],
                        "c": [0.0, 0.1],
                        "d": [1.0, 1.1],
                    },
                ),
            ],
        }
        out = solve(p)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["first_query_id"], "split_ab_cd")
        self.assertEqual(out["minimum_worst_case_cost_units"], 2.0)

    def test_incomplete_hypothesis_cover_fails_closed(self):
        p = self.base()
        p["hypothesis_cover_complete"] = False
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "HYPOTHESIS_COVER_COMPLETENESS_UNPROVED")

    def test_interval_soundness_must_be_bound(self):
        p = self.base()
        p["interval_soundness_bound"] = False
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "INTERVAL_SOUNDNESS_UNPROVED")

    def test_query_must_cover_every_world(self):
        p = self.base()
        del p["queries"][0]["prediction_intervals"]["b"]
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertIn("DOMAIN_MISMATCH", out["reason"])

    def test_budget_gate_is_fail_closed(self):
        p = self.base()
        p["max_worst_case_cost_units"] = 0
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__MINIMUM_WORST_CASE_COST_EXCEEDS_BUDGET",
        )
        self.assertEqual(out["minimum_worst_case_cost_units"], 1.0)

    def test_touching_intervals_correctly_preserve_ambiguity_at_boundary(self):
        p = self.base()
        p["queries"] = [query("q", {"a": [0, 1], "b": [1, 2]})]
        out = solve(p)
        self.assertFalse(out["pass"])
        self.assertIn("NOT_WORST_CASE_SEPARABLE", out["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
