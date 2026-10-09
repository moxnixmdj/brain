import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    def test_activation_v2_truth(self):
        a=json.loads((ROOT/"canonical/governance/R2_REGCAP_CANDIDATE_AMBIGUITY_CONTROL_ACTIVATION_20261009_V2.json").read_text())
        self.assertEqual(a["bounded_policy"]["authenticated_one_step_discriminator"],"RELEASABILITY_CLASS")
        self.assertEqual(a["bounded_policy"]["minimum_observation_count"],1)
        self.assertFalse(a["bounded_policy"]["concept_identity_before_observation"])
        self.assertFalse(a["bounded_policy"]["open_world_candidate_completeness"])
        self.assertEqual(a["r2_truth_delta"]["primary_internal_unsolved_count_delta"],0)
        self.assertFalse(a["r2_truth_delta"]["finance_semantic_tail_closed"])
        self.assertEqual(a["strict_externality"]["missing_discriminator_observation_classification"],"INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT")
        self.assertFalse(a["strict_externality"]["information_theoretic_externality_proved"])
        self.assertFalse(a["semantic_truth_authority"])
        self.assertFalse(a["policy_adequacy_authority"])
        self.assertFalse(a["terminal_authority"])
        self.assertEqual(a["accounting"]["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
