import unittest

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import (
    compile_state,
    resolve_common_policy,
)


def atom(x):
    return {"op": "ATOM", "id": x}


def neg(x):
    return {"op": "NOT", "arg": atom(x)}


class MonotoneSemanticConstraintKernelTests(unittest.TestCase):
    def test_missing_fact_stays_broad_and_cannot_false_positive(self):
        out = resolve_common_policy(
            ["A", "B"],
            {"p": {"op": "AND", "args": [atom("A"), atom("B")]}},
            formal_source_constraints=[atom("A"), atom("B")],
            proposed_refinements=[atom("A")],
        )
        self.assertEqual(out["status"], "UNRESOLVED")
        self.assertEqual(out["certified_common_policies"], [])
        self.assertEqual(out["model_count"], 2)

    def test_supported_constraint_can_certify_policy(self):
        out = resolve_common_policy(
            ["A"],
            {"p": atom("A")},
            formal_source_constraints=[atom("A")],
            proposed_refinements=[atom("A")],
        )
        self.assertEqual(out["status"], "COMMON_POLICY_CERTIFIED")
        self.assertEqual(out["certified_common_policies"], ["p"])

    def test_unproved_constraint_is_rejected_not_trusted(self):
        out = resolve_common_policy(
            ["A", "B"],
            {"p": {"op": "AND", "args": [atom("A"), atom("B")]}},
            formal_source_constraints=[atom("A")],
            proposed_refinements=[atom("A"), atom("B")],
        )
        self.assertEqual(out["status"], "UNRESOLVED")
        self.assertEqual(len(out["rejected_refinements"]), 1)
        self.assertEqual(out["model_count"], 2)

    def test_correlation_is_preserved(self):
        xor = {"op": "XOR", "args": [atom("A"), atom("B")]}
        out = resolve_common_policy(
            ["A", "B"],
            {
                "p_xor": xor,
                "p_A": atom("A"),
            },
            formal_source_constraints=[xor],
            proposed_refinements=[xor],
        )
        self.assertEqual(out["status"], "COMMON_POLICY_CERTIFIED")
        self.assertIn("p_xor", out["certified_common_policies"])
        self.assertNotIn("p_A", out["certified_common_policies"])
        self.assertEqual(out["model_count"], 2)

    def test_multiple_interpretations_same_policy_need_not_be_unique(self):
        xor = {"op": "XOR", "args": [atom("A"), atom("B")]}
        out = resolve_common_policy(
            ["A", "B"],
            {"p_shared": xor},
            formal_source_constraints=[xor],
            proposed_refinements=[xor],
        )
        self.assertEqual(out["model_count"], 2)
        self.assertEqual(out["certified_common_policies"], ["p_shared"])

    def test_distinct_policy_regions_remain_unresolved_without_discriminator(self):
        out = resolve_common_policy(
            ["A"],
            {"p_true": atom("A"), "p_false": neg("A")},
        )
        self.assertEqual(out["status"], "UNRESOLVED")
        self.assertEqual(out["model_count"], 2)

    def test_bad_atom_fails_closed(self):
        out = compile_state(
            ["A"],
            formal_source_constraints=[atom("B")],
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
