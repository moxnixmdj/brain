from __future__ import annotations

import copy
import unittest

from canonical.runtime import contract_native_proof_suites as source
from canonical.runtime import p1_shared_failure_semantics_batch_v1 as batch

CONTRACT = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"


class P1SharedFailureSemanticsBatchV2Tests(unittest.TestCase):
    def test_binder_accepts_public_source_only(self):
        full = source.generate_case(CONTRACT, 1234567, 4)
        public = source.public_task(full)
        out = batch.bind_public_source_case(
            public, surface_id=batch.SURFACES[0], case_index=0
        )
        self.assertEqual(out["status"], "PASS", out)
        self.assertNotIn("_oracle", out["candidate_case"])
        self.assertEqual(out["semantics_counts"]["DIRECT_CONTRACT"], 1)
        self.assertGreaterEqual(out["semantics_counts"]["DERIVED_UPSTREAM"], 1)

    def test_hidden_oracle_input_is_explicitly_forbidden(self):
        full = source.generate_case(CONTRACT, 7, 4)
        out = batch.bind_public_source_case(
            full, surface_id=batch.SURFACES[0], case_index=0
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "HIDDEN_ORACLE_INPUT_FORBIDDEN")

    def test_semantics_binding_is_invariant_to_hidden_oracle_mutation(self):
        full = source.generate_case(CONTRACT, 99117, 5)
        public = source.public_task(full)
        baseline = batch.bind_public_source_case(
            public, surface_id=batch.SURFACES[1], case_index=2
        )
        mutant = copy.deepcopy(full)
        mutant["_oracle"]["cause_step"] = 0
        mutant_public = source.public_task(mutant)
        changed_hidden = batch.bind_public_source_case(
            mutant_public, surface_id=batch.SURFACES[1], case_index=2
        )
        self.assertEqual(baseline, changed_hidden)

    def test_public_failed_state_is_load_bearing(self):
        full = source.generate_case(CONTRACT, 1234, 3)
        public = source.public_task(full)
        for row in public["task"]["trajectory"]:
            if row.get("invariant_pass") is False:
                row["state"] = "UNBOUND_FAILED_STATE"
                break
        out = batch.bind_public_source_case(
            public, surface_id=batch.SURFACES[0], case_index=0
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("FAILED_CHECK_PUBLIC_SEMANTICS_UNBOUND", out["reason"])

    def test_all_three_surfaces_dual_score_on_spent_cases(self):
        beacon = "spent-preflight-beacon-v2"
        for surface in batch.SURFACES:
            for i in (0, 7, 31, 63):
                out = batch.evaluate_one(
                    beacon=beacon, surface_id=surface, case_index=i
                )
                self.assertTrue(out["pass"], out)
                self.assertTrue(out["v7_intervention_scorer_pass"])
                self.assertTrue(out["source_native_rescue_scorer_pass"])
                self.assertTrue(out["source_native_rescue_pass"])
                self.assertEqual(
                    out["semantic_binding_basis"],
                    "FROZEN_PUBLIC_SOURCE_STATE_AND_INVARIANT_RESULT_ONLY__HIDDEN_ORACLE_INPUT_FORBIDDEN",
                )

    def test_seed_is_post_freeze_beacon_sensitive_and_deterministic(self):
        a = batch.derive_seed("beacon-A", batch.SURFACES[0], 0)
        b = batch.derive_seed("beacon-A", batch.SURFACES[0], 0)
        c = batch.derive_seed("beacon-B", batch.SURFACES[0], 0)
        d = batch.derive_seed("beacon-A", batch.SURFACES[1], 0)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(a, d)

    def test_wrong_candidate_fails_independent_source_scorer(self):
        full = source.generate_case(CONTRACT, 442211, 4)
        wrong_step = full["_oracle"]["cause_step"] + 1
        wrong = {
            "status": "IDENTIFIED",
            "cause_action_id": f"A{wrong_step}",
            "supporting_receipts": ["tampered"],
        }
        adapted = batch._adapt_v7_to_source_candidate(wrong)
        verdict = source.score_case(full, adapted)
        self.assertFalse(verdict["pass"], verdict)

    def test_mutation_preflight_enforces_public_only_firewall(self):
        out = batch.mutation_preflight()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["fresh_reality_units_consumed"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_spent_full_batch_cannot_self_claim_reality(self):
        out = batch.run_batch("spent-unit-test-beacon-v2")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["cases"], batch.TOTAL_CASES)
        self.assertEqual(out["passes"], batch.TOTAL_CASES)
        self.assertEqual(out["failures"], 0)
        self.assertEqual(set(out["by_surface"]), set(batch.SURFACES))
        self.assertEqual(out["terminal_v3_replayed"], 0)
        self.assertEqual(out["fresh_reality_units_consumed"], 0)
        self.assertEqual(
            out["reality_unit_candidate_if_separately_authorized_and_independently_adjudicated"],
            1,
        )
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
