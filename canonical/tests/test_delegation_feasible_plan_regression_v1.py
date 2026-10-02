import unittest

from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as proof


class DelegationFeasiblePlanRegressionTests(unittest.TestCase):
    def _task(self):
        return {
            "initial_facts": ["start"],
            "required_outputs": ["goal"],
            "resource_capacities": {},
            "steps": [
                {
                    "id": "cheap_unstaffable",
                    "requires": ["start"],
                    "produces": ["goal"],
                    "capability": "rare",
                    "cost": 1,
                    "writes": [],
                    "evidence_outputs": ["ev_cheap"],
                    "available": True,
                },
                {
                    "id": "costlier_feasible",
                    "requires": ["start"],
                    "produces": ["goal"],
                    "capability": "common",
                    "cost": 2,
                    "writes": [],
                    "evidence_outputs": ["ev_good"],
                    "available": True,
                },
            ],
            "workers": [
                {"id": "w1", "capabilities": ["common"]},
            ],
        }

    def test_candidate_skips_cheapest_unschedulable_fact_plan(self):
        out = candidate.solve_initial({"task": self._task()})
        self.assertEqual(out["task_ids"], ["costlier_feasible"])
        self.assertEqual(out["assignment"], {"costlier_feasible": "w1"})
        self.assertEqual(out["wave_count"], 1)
        self.assertEqual(out["total_cost"], 2.0)

    def test_independent_oracle_selects_same_feasible_optimum(self):
        task = self._task()
        out = proof._optimal_plan(task)
        self.assertEqual(out["task_ids"], ["costlier_feasible"])
        self.assertEqual(out["total_cost"], 2.0)

    def test_no_schedulable_plan_fails_closed(self):
        task = self._task()
        task["steps"] = [task["steps"][0]]
        with self.assertRaises(candidate.DelegationV2Error):
            candidate.solve_initial({"task": task})
        with self.assertRaises(ValueError):
            proof._optimal_plan(task)


if __name__ == "__main__":
    unittest.main(verbosity=2)
