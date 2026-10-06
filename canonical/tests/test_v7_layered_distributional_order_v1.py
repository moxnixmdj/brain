import unittest

from canonical.runtime.v7_layered_distributional_order_v1 import (
    absolute_promotion_feasible,
    capability_noninferior,
    qualifies,
    select_best_qualifying_route,
)


SUCCESS = {"failure": 0.0, "success": 1.0}
LOW_COMPUTE = {"high_compute": 0.0, "low_compute": 1.0}


def route(
    law,
    *,
    owned=True,
    donor=True,
    spend=0.0,
    absolute_ok=True,
    wall=1.0,
    durable=1.0,
    complexity=1.0,
):
    return {
        "law": law,
        "brain_owned": owned,
        "donor_independent": donor,
        "incremental_spend_usd": spend,
        "absolute_project_constraints_ok": absolute_ok,
        "wall_clock_to_verified_ownership": wall,
        "durable_resource_compute_footprint": durable,
        "complexity": complexity,
    }


class V7LayeredDistributionalOrderTests(unittest.TestCase):
    def test_more_internal_compute_does_not_fail_capability_when_not_in_contract(self):
        target = {"success": 1.0}
        brain = route({"success": 1.0}, durable=2.0)
        self.assertTrue(capability_noninferior(brain["law"], target, evaluators=[SUCCESS]))
        self.assertTrue(qualifies(brain, target, evaluators=[SUCCESS]))

    def test_faster_smaller_route_cannot_rescue_capability_failure(self):
        target = {"success": 1.0}
        bad = route(
            {"success": 0.5, "failure": 0.5},
            wall=0.01,
            durable=0.01,
            complexity=0.01,
        )
        self.assertFalse(qualifies(bad, target, evaluators=[SUCCESS]))

    def test_superior_capability_cannot_rescue_unowned_route(self):
        target = {"success": 0.9, "failure": 0.1}
        unowned = route({"success": 1.0}, owned=False)
        self.assertTrue(
            capability_noninferior(unowned["law"], target, evaluators=[SUCCESS])
        )
        self.assertFalse(absolute_promotion_feasible(unowned))
        self.assertFalse(qualifies(unowned, target, evaluators=[SUCCESS]))

    def test_nonzero_incremental_spend_fails_absolute_gate_not_capability(self):
        target = {"success": 1.0}
        paid = route({"success": 1.0}, spend=1.0)
        self.assertTrue(
            capability_noninferior(paid["law"], target, evaluators=[SUCCESS])
        )
        self.assertFalse(qualifies(paid, target, evaluators=[SUCCESS]))

    def test_optimization_runs_only_among_qualifying_routes(self):
        target = {"success": 1.0}
        fast_bad = route(
            {"success": 0.0, "failure": 1.0},
            wall=0.01,
            durable=0.01,
            complexity=0.01,
        )
        slow_good = route(
            {"success": 1.0},
            wall=2.0,
            durable=2.0,
            complexity=2.0,
        )
        best = select_best_qualifying_route(
            [fast_bad, slow_good],
            target,
            evaluators=[SUCCESS],
        )
        self.assertIs(best, slow_good)

    def test_lexicographic_brain_route_selection(self):
        target = {"success": 1.0}
        a = route({"success": 1.0}, wall=1.0, durable=5.0, complexity=1.0)
        b = route({"success": 1.0}, wall=1.0, durable=2.0, complexity=9.0)
        c = route({"success": 1.0}, wall=1.0, durable=2.0, complexity=3.0)
        best = select_best_qualifying_route([a, b, c], target, evaluators=[SUCCESS])
        self.assertIs(best, c)

    def test_resource_becomes_capability_dimension_only_when_explicitly_load_bearing(self):
        target = {"success": 0.5, "low_compute": 0.5}
        brain = {"success": 0.5, "high_compute": 0.5}
        self.assertTrue(capability_noninferior(brain, target, evaluators=[SUCCESS]))
        self.assertFalse(
            capability_noninferior(
                brain,
                target,
                evaluators=[SUCCESS, LOW_COMPUTE],
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
