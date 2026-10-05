import math
import unittest

from canonical.runtime import h100_universal_proposal_bound_v1 as u


class H100UniversalProposalBoundTests(unittest.TestCase):
    def test_quantitative_ceiling(self):
        self.assertEqual(u.quantitative_uniform_bound_ceiling(100),0.01)

    def test_any_positive_uniform_bound_gets_finite_contradiction(self):
        for e in (0.5,0.25,0.1,0.01,1e-6):
            c=u.uniform_positive_lower_bound_contradiction(e)
            self.assertTrue(c["contradiction"])
            self.assertGreater(c["required_mass_if_all_ge_epsilon"],1.0)

    def test_kraft_prefix_examples(self):
        self.assertTrue(u.validate_prefix_lengths([1])["prefix_code_exists"])
        self.assertTrue(u.validate_prefix_lengths([2,2,2,2])["prefix_code_exists"])
        self.assertFalse(u.validate_prefix_lengths([1,1,2])["prefix_code_exists"])

    def test_complexity_conditioned_mass_is_positive(self):
        for L in (1,2,8,32,128):
            self.assertGreater(u.proposal_mass_lower_bound(L),0.0)

    def test_n95_matches_direct_for_moderate_lengths(self):
        for L in (1,2,4,8,16,32):
            p=2.0**(-L)
            want=math.ceil(math.log(0.05)/math.log1p(-p))
            self.assertEqual(u.stochastic_n95_for_code_length(L),want)

    def test_prefix_candidate_count_bound(self):
        self.assertEqual(u.prefix_candidate_count_bound(1),2)
        self.assertEqual(u.prefix_candidate_count_bound(10),1024)

    def test_dovetail_bound(self):
        self.assertEqual(u.deterministic_dovetail_step_bound(10,1000),1_024_000)

    def test_certificate_has_zero_learned_state_and_no_terminal_credit(self):
        c=u.certificate(20,500)
        self.assertEqual(c["persistent_learned_bytes"],0)
        self.assertEqual(c["external_learned_capability_calls"],0)
        self.assertEqual(c["h100_terminal_credit_delta"],0)
        self.assertEqual(c["deterministic_dovetail_candidate_step_bound"],(1<<20)*500)


if __name__=="__main__":
    unittest.main(verbosity=2)
