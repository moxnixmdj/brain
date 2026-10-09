import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


class Tests(unittest.TestCase):
    def test_regcap_candidate_ambiguity_activation_truth(self):
        a=json.loads((ROOT/"canonical/governance/R2_REGCAP_CANDIDATE_AMBIGUITY_CONTROL_ACTIVATION_20261009_V1.json").read_text())
        v=json.loads((ROOT/"canonical/verification/R2_REGCAP_CANDIDATE_AMBIGUITY_CONTROL_VERIFY_20261009_V1.json").read_text())
        self.assertEqual(a["verification"]["status"],v["status"])
        self.assertTrue(a["new_closed_subproblem"]["new_state"].startswith("CLOSED_FOR_VERIFIED_BOUNDED"))
        self.assertEqual(a["r2_truth_delta"]["primary_internal_unsolved_count_delta"],0)
        self.assertEqual(a["r2_truth_delta"]["primary_internal_unsolved_cell_remains"],"FINANCE_SEMANTIC_ADEQUACY_TAIL")
        self.assertFalse(a["strict_externality"]["missing_context_or_observation_is_external_impossibility"])
        self.assertEqual(a["strict_externality"]["pending_clarification_or_acquisition_classification"],"INTERNAL_UNSOLVED")
        self.assertFalse(a["semantic_truth_authority"])
        self.assertFalse(a["policy_adequacy_authority"])
        self.assertFalse(a["terminal_authority"])
        self.assertEqual(a["accounting"]["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
