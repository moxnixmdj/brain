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

    def test_barrier_order_is_backward_compatible_without_root_state(self):
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

    def test_positive_root1_gap_gets_first_capability_repair_barrier(self):
        authority = {
            "truth": {"achieved": False},
            "atomic_acceptance_frontier": {"proved": 12, "unresolved": 26, "total": 38},
        }
        root_state = {
            "roots": {
                "root_1_capability_missing": {
                    "current_positive_root1_blockers": [
                        {"predicate_id": "LIVEBENCH_IF_GE_65_7"}
                    ]
                }
            }
        }
        registry = {
            "repairs": [
                {
                    "predicate_id": "LIVEBENCH_IF_GE_65_7",
                    "repair_id": "ROOT1_LIVEBENCH_GENERAL_SEMANTIC_CORE",
                    "required_capability_layer": "GENERAL_SEMANTIC_SEED_PRODUCTION",
                    "repair_frontier": "frontier.json",
                    "score_only_quarantine": "quarantine.json",
                    "next_minimum_action": "QUALIFY_LOCAL_SEMANTIC_CORE",
                }
            ]
        }
        plan = compile_causal_depth_plan(
            authority, {"actions": []}, {"claims": []}, root_state, registry
        )
        self.assertEqual(plan["barriers"][0]["id"], "BARRIER_0_POSITIVE_ROOT1_CAPABILITY_REPAIR")
        self.assertEqual(
            plan["barriers"][0]["repair_actions"][0]["repair_id"],
            "ROOT1_LIVEBENCH_GENERAL_SEMANTIC_CORE",
        )
        self.assertTrue(plan["barriers"][0]["scheduler_ready"])
        self.assertEqual(plan["positive_root1_predicate_ids"], ["LIVEBENCH_IF_GE_65_7"])
        self.assertEqual(
            [b["id"] for b in plan["barriers"][1:]],
            [
                "BARRIER_1_ZERO_REALITY_MEGABATCH",
                "BARRIER_2_MINIMUM_REALITY_TRANSACTION",
                "BARRIER_3_ATOMIC_FINALITY",
            ],
        )

    def test_unbound_positive_root1_gap_fails_closed(self):
        authority = {
            "truth": {"achieved": False},
            "atomic_acceptance_frontier": {"proved": 12, "unresolved": 26, "total": 38},
        }
        root_state = {
            "roots": {
                "root_1_capability_missing": {
                    "current_positive_root1_blockers": [
                        {"predicate_id": "LIVEBENCH_IF_GE_65_7"}
                    ]
                }
            }
        }
        plan = compile_causal_depth_plan(
            authority, {"actions": []}, {"claims": []}, root_state, {"repairs": []}
        )
        root1 = plan["barriers"][0]
        self.assertFalse(root1["scheduler_ready"])
        self.assertEqual(root1["blocking_unbound_predicates"], ["LIVEBENCH_IF_GE_65_7"])
        self.assertEqual(root1["repair_actions"], [])


if __name__ == "__main__":
    unittest.main()
