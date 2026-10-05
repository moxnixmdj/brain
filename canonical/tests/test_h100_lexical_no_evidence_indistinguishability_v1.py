import unittest
from canonical.runtime import h100_lexical_no_evidence_indistinguishability_v1 as x

class H100LexicalNoEvidenceIndistinguishabilityTests(unittest.TestCase):
    def test_forced_input_fails_one_identical_world(self):
        out=x.deterministic_two_world_outcome("INPUT")
        self.assertEqual(out["correct_world_count"],1)
        self.assertFalse(out["worst_case_correct"])

    def test_forced_target_fails_one_identical_world(self):
        out=x.deterministic_two_world_outcome("TARGET")
        self.assertEqual(out["correct_world_count"],1)
        self.assertFalse(out["worst_case_correct"])

    def test_randomized_minimax_is_one_half(self):
        m=x.minimax_randomized_accuracy()
        self.assertEqual(m["minimax_probability_input"],0.5)
        self.assertEqual(m["minimax_worst_case_accuracy"],0.5)
        for p in (0.0,0.1,0.25,0.5,0.75,0.9,1.0):
            self.assertLessEqual(x.randomized_two_world_worst_case(p)["worst_case_accuracy"],0.5)

    def test_no_evidence_fails_closed(self):
        out=x.fail_closed_decision(distinguishing_evidence_present=False)
        self.assertEqual(out["status"],"ABSTAIN_NO_DISTINGUISHING_EVIDENCE")
        self.assertIsNone(out["role"])

    def test_evidence_routes_to_verified_resolver(self):
        out=x.fail_closed_decision(distinguishing_evidence_present=True)
        self.assertEqual(out["status"],"EVIDENCE_REQUIRED__DELEGATE_TO_VERIFIED_SOURCE_RESOLVER")

    def test_certificate_is_zero_learned_and_nonterminal(self):
        c=x.certificate()
        self.assertEqual(c["randomized_minimax_worst_case_accuracy"],0.5)
        self.assertEqual(c["sound_no_evidence_action"],"ABSTAIN")
        self.assertEqual(c["persistent_learned_bytes_required_by_theorem"],0)
        self.assertEqual(c["h100_terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
