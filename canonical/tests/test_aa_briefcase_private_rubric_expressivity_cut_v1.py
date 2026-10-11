import unittest
from canonical.runtime import aa_briefcase_private_rubric_expressivity_cut_v1 as cut

class Tests(unittest.TestCase):
    def test_opposite_worlds(self):
        x = cut.opposite_order_witness("A", "B")
        self.assertTrue(x["opposite_order"])

    def test_distinct_required(self):
        with self.assertRaises(ValueError):
            cut.separating_worlds("A", "A")

    def test_no_public_strict_order_without_bound_restriction(self):
        self.assertFalse(cut.universal_nontrivial_order_exists(
            ["A", "B"],
            private_rubric_semantics_publicly_restricted=False,
        ))

    def test_singleton_is_trivial(self):
        self.assertTrue(cut.universal_nontrivial_order_exists(
            ["A"],
            private_rubric_semantics_publicly_restricted=False,
        ))

    def test_restriction_must_be_explicit(self):
        with self.assertRaises(ValueError):
            cut.universal_nontrivial_order_exists(
                ["A", "B"],
                private_rubric_semantics_publicly_restricted=True,
            )

    def test_current_projection_blocks_top_support(self):
        out = cut.internal_route_projection(
            artifact_domain_size=2,
            private_rubric_semantics_publicly_restricted=False,
            aggregate_rubric_bypass_proved=False,
        )
        self.assertTrue(out["top_support_route_blocked_by_rubric_expressivity"])

    def test_bypass_would_make_cut_nondecisive(self):
        out = cut.internal_route_projection(
            artifact_domain_size=2,
            private_rubric_semantics_publicly_restricted=False,
            aggregate_rubric_bypass_proved=True,
        )
        self.assertFalse(out["top_support_route_blocked_by_rubric_expressivity"])

if __name__ == "__main__":
    unittest.main()
