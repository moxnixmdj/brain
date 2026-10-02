import unittest

from canonical.runtime.trajectory_failure_localization_proof import (
    make_synthetic_case,
    public_case,
    verify_localization,
    verify_batch,
)


class TrajectoryFailureLocalizationProofTests(unittest.TestCase):
    def setUp(self):
        self.case=make_synthetic_case(
            case_id="synthetic-1",
            step_count=8,
            causal_step=2,
            symptom_step=4,
            terminal_failure_step=6,
        )

    def test_public_view_hides_causal_and_symptom_identity(self):
        p=public_case(self.case)
        self.assertNotIn("causal_step",p)
        self.assertNotIn("symptom_step",p)
        self.assertEqual(p["terminal_failure_step"],6)

    def test_true_causal_target_passes_intervention_rescue(self):
        out=verify_localization(self.case,2)
        self.assertTrue(out["pass"])
        self.assertTrue(out["nominated_repair_rescues_terminal_outcome"])
        self.assertFalse(out["symptom_only_repair_rescues_terminal_outcome"])

    def test_downstream_symptom_nomination_fails(self):
        out=verify_localization(self.case,4)
        self.assertFalse(out["pass"])
        self.assertFalse(out["nominated_repair_rescues_terminal_outcome"])

    def test_wrong_earlier_step_fails(self):
        self.assertFalse(verify_localization(self.case,1)["pass"])

    def test_invalid_nomination_fails_closed(self):
        self.assertEqual(verify_localization(self.case,7)["status"],"FAIL_CLOSED")
        self.assertEqual(verify_localization(self.case,"2")["status"],"FAIL_CLOSED")

    def test_batch_requires_every_case(self):
        c2=make_synthetic_case(
            case_id="synthetic-2",step_count=7,causal_step=1,symptom_step=3,terminal_failure_step=5
        )
        self.assertTrue(verify_batch([(self.case,2),(c2,1)])["pass"])
        self.assertFalse(verify_batch([(self.case,2),(c2,3)])["pass"])


if __name__=="__main__":
    unittest.main()
