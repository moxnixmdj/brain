import unittest

from canonical.runtime.terminal_causal_depth_controller_v1 import compile_causal_depth_plan


class TerminalCausalDepthControllerTests(unittest.TestCase):
    def test_parallelizes_available_zero_reality_actions_only(self):
        authority = {
            "truth": {"achieved": False},
            "atomic_acceptance_frontier": {"proved": 8, "unresolved": 30, "total": 38},
        }
        graph = {
            "actions": [
                {"id": "A", "new_reality_units": 0, "preconditions": []},
                {"id": "B", "new_reality_units": 0, "preconditions": [{"id": "X", "satisfied": True}]},
                {"id": "C", "new_reality_units": 0, "preconditions": [{"id": "Y", "satisfied": False}]},
                {"id": "D", "new_reality_units": 1, "preconditions": []},
            ]
        }
        plan = compile_causal_depth_plan(authority, graph, {"claims": []})
        self.assertEqual(plan["barriers"][0]["parallel_actions"], ["A", "B"])
        self.assertFalse(plan["barriers"][0]["fresh_reality_authorized"])

    def test_subtracts_actions_whose_targets_are_already_proved(self):
        authority = {
            "truth": {"achieved": False},
            "atomic_acceptance_frontier": {"proved": 8, "unresolved": 30, "total": 38},
        }
        graph = {
            "actions": [
                {
                    "id": "STALE_DELEGATION",
                    "new_reality_units": 0,
                    "target_predicates": ["DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"],
                    "preconditions": [],
                },
                {
                    "id": "OPEN_TOOL",
                    "new_reality_units": 0,
                    "target_predicates": ["TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"],
                    "preconditions": [],
                },
            ]
        }
        bindings = {
            "claims": [
                {
                    "predicate_id": "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
                    "state": "PROVED",
                }
            ]
        }
        plan = compile_causal_depth_plan(authority, graph, bindings)
        self.assertEqual(plan["barriers"][0]["parallel_actions"], ["OPEN_TOOL"])

    def test_preserves_current_truth_without_granting_credit(self):
        authority = {
            "truth": {"achieved": False},
            "atomic_acceptance_frontier": {"proved": 8, "unresolved": 30, "total": 38},
        }
        plan = compile_causal_depth_plan(authority, {"actions": []}, {"claims": []})
        self.assertEqual(plan["truth_snapshot"]["proved_atomic_predicates"], 8)
        self.assertEqual(plan["truth_snapshot"]["unresolved_atomic_predicates"], 30)
        self.assertEqual(plan["credit_delta"], 0)
        self.assertFalse(plan["execution_authority"])
        self.assertFalse(plan["promotion_authority"])

    def test_barrier_order_is_causal(self):
        authority = {
            "truth": {"achieved": False},
            "atomic_acceptance_frontier": {"proved": 8, "unresolved": 30, "total": 38},
        }
        plan = compile_causal_depth_plan(authority, {"actions": []}, {"claims": []})
        self.assertEqual(
            [b["id"] for b in plan["barriers"]],
            [
                "BARRIER_1_ZERO_REALITY_MEGABATCH",
                "BARRIER_2_MINIMUM_REALITY_TRANSACTION",
                "BARRIER_3_ATOMIC_FINALITY",
            ],
        )


if __name__ == "__main__":
    unittest.main()
