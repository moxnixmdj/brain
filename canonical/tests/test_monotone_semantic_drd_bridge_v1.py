import unittest

from canonical.runtime.monotone_semantic_drd_bridge_v1 import solve


def atom(x):
    return {"op": "ATOM", "id": x}


def neg(x):
    return {"op": "NOT", "arg": atom(x)}


class MonotoneSemanticDRDBridgeTests(unittest.TestCase):
    def test_unresolved_binary_policy_choice_selects_exact_query(self):
        out = solve(
            ["A"],
            {
                "p_true": {"condition": atom("A"), "adequacy_certificate_id": "cert-true"},
                "p_false": {"condition": neg("A"), "adequacy_certificate_id": "cert-false"},
            },
            [{
                "observation_id": "ask_A",
                "formula": atom("A"),
                "cost_units": 1,
                "truthfulness_certificate_id": "query-cert",
            }],
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["first_observation_id"], "ask_A")
        self.assertEqual(out["minimum_worst_case_cost_units"], 1.0)

    def test_proved_fact_yields_common_policy_without_query(self):
        out = solve(
            ["A"],
            {
                "p_true": {"condition": atom("A"), "adequacy_certificate_id": "cert-true"},
                "p_false": {"condition": neg("A"), "adequacy_certificate_id": "cert-false"},
            },
            [],
            formal_source_constraints=[atom("A")],
            proposed_refinements=[atom("A")],
        )
        self.assertTrue(out["pass"])
        self.assertIn("p_true", out["common_policy_ids"])
        self.assertIsNone(out["first_observation_id"])

    def test_overlapping_policy_region_avoids_unnecessary_identification(self):
        xor = {"op": "XOR", "args": [atom("A"), atom("B")]}
        either = {"op": "OR", "args": [atom("A"), atom("B")]}
        out = solve(
            ["A", "B"],
            {
                "p_shared": {"condition": either, "adequacy_certificate_id": "cert-shared"},
            },
            [],
            formal_source_constraints=[xor],
            proposed_refinements=[xor],
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["abstract_world_count"], 2)
        self.assertIn("p_shared", out["common_policy_ids"])

    def test_contradictory_semantic_state_fails_closed(self):
        out = solve(
            ["A"],
            {"p": {"condition": atom("A"), "adequacy_certificate_id": "cert"}},
            [],
            formal_source_constraints=[atom("A"), neg("A")],
            proposed_refinements=[atom("A"), neg("A")],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_missing_observation_certificate_fails_closed(self):
        out = solve(
            ["A"],
            {
                "p_true": {"condition": atom("A"), "adequacy_certificate_id": "cert-true"},
                "p_false": {"condition": neg("A"), "adequacy_certificate_id": "cert-false"},
            },
            [{
                "observation_id": "ask_A",
                "formula": atom("A"),
                "cost_units": 1,
                "truthfulness_certificate_id": "",
            }],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
