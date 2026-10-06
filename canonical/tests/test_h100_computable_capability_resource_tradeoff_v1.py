import unittest
from canonical.runtime import h100_computable_capability_resource_tradeoff_v1 as r

class H100ComputableCapabilityResourceTradeoffTests(unittest.TestCase):
    def test_zero_bound_under_exact_theorem_assumptions(self):
        out=r.logical_learned_state_lower_bound(
            input_complete=True,
            total_computable=True,
            deterministic_program_allowed=True,
            deterministic_program_bits_count_as_learned=False,
        )
        self.assertTrue(out["theorem_applies"])
        self.assertEqual(out["logical_learned_state_lower_bound_bits"],0)

    def test_missing_input_completeness_disables_theorem(self):
        out=r.logical_learned_state_lower_bound(
            input_complete=False,
            total_computable=True,
            deterministic_program_allowed=True,
            deterministic_program_bits_count_as_learned=False,
        )
        self.assertFalse(out["theorem_applies"])
        self.assertIsNone(out["logical_learned_state_lower_bound_bits"])

    def test_program_disallowed_disables_theorem(self):
        out=r.logical_learned_state_lower_bound(
            input_complete=True,
            total_computable=True,
            deterministic_program_allowed=False,
            deterministic_program_bits_count_as_learned=False,
        )
        self.assertFalse(out["theorem_applies"])

    def test_program_counted_as_learned_disables_zero_learned_claim(self):
        out=r.logical_learned_state_lower_bound(
            input_complete=True,
            total_computable=True,
            deterministic_program_allowed=True,
            deterministic_program_bits_count_as_learned=True,
        )
        self.assertFalse(out["theorem_applies"])

    def test_lookup_moves_cost_into_deterministic_bits(self):
        v=r.finite_lookup_resource(case_count=100,key_bits_per_case=64,answer_bits_per_case=16)
        self.assertEqual(v.learned_bits,0)
        self.assertEqual(v.deterministic_capability_bits,8000)

    def test_hidden_lookup_rejected_as_general_capability(self):
        out=r.finite_lookup_capability_credit(hidden_cases_encoded=True,scope_general_rule_proved=False)
        self.assertFalse(out["admissible_general_capability_evidence"])
        self.assertEqual(out["status"],"REJECT__HELDOUT_OR_CASE_MEMORIZATION")

    def test_pareto_dominance(self):
        a=r.ResourceVector(0,100,1000,0,0)
        b=r.ResourceVector(1,100,1000,0,0)
        self.assertTrue(r.pareto_dominates(a,b))
        self.assertFalse(r.pareto_dominates(b,a))

    def test_learned_only_metric_can_hide_large_code_cost(self):
        a=r.ResourceVector(0,1_000_000,1_000_000,0,0)
        b=r.ResourceVector(8,1000,1000,0,0)
        out=r.learned_only_comparison_can_reverse(a,b)
        self.assertEqual(out["learned_only_preference"],"A")
        self.assertFalse(out["a_pareto_dominates_b"])
        self.assertFalse(out["b_pareto_dominates_a"])

    def test_certificate_zero_terminal_credit(self):
        c=r.certificate()
        self.assertEqual(c["h100_terminal_credit_delta"],0)
        self.assertEqual(c["logical_zero_bound"]["logical_learned_state_lower_bound_bits"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
