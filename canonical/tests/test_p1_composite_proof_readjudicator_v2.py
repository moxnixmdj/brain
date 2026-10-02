from __future__ import annotations

import unittest

from canonical.runtime.p1_composite_proof_readjudicator_v2 import (
    evaluate,
    mutation_trials,
)


class P1CompositeProofReadjudicatorV2Tests(unittest.TestCase):
    def test_exact_partition_and_all_nine_mutations_killed(self):
        out = evaluate()
        self.assertTrue(out["partition_exact"], out)
        self.assertEqual(out["required_mutation_count"], 9, out)
        self.assertEqual(out["mutation_trial_count"], 9, out)
        self.assertEqual(out["killed_mutation_count"], 9, out)
        self.assertEqual(out["surviving_required_mutations"], [], out)
        self.assertEqual(out["strict_v4_baseline_failures"], [], out)
        self.assertTrue(out["semantic_repair_complete"], out)

    def test_known_old_counterexamples_are_now_killed(self):
        trials = mutation_trials()
        drop = trials["DROP_PROVENANCE_OR_DEPENDENCY_EDGE"]
        diag = trials["UNFALSIFIABLE_DIAGNOSIS"]
        self.assertTrue(drop["old_scorer_passed"], drop)
        self.assertTrue(drop["killed"], drop)
        self.assertTrue(diag["baseline_pass"], diag)
        self.assertTrue(diag["killed"], diag)

    def test_terminal_mutation_roles_are_load_bearing(self):
        trials = mutation_trials()
        for mid in [
            "SELECT_DOWNSTREAM_SYMPTOM",
            "SELECT_LATER_CORRELATED_STEP",
            "REPAIR_TARGET_WITH_NO_RESCUE",
        ]:
            self.assertTrue(trials[mid]["baseline_pass"], trials[mid])
            self.assertTrue(trials[mid]["killed"], trials[mid])

    def test_zero_credit_until_independent_verification(self):
        out = evaluate()
        self.assertFalse(out["whole_p1_contract_restored"], out)
        self.assertTrue(out["independent_verification_required"], out)
        self.assertEqual(out["terminal_results_replayed"], 0, out)
        self.assertEqual(out["fresh_terminal_evidence_consumed"], 0, out)
        self.assertEqual(out["capability_credit_delta"], 0, out)
        self.assertEqual(out["family_credit_delta"], 0, out)
        self.assertFalse(out["execution_authority"], out)
        self.assertFalse(out["promotion_authority"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
