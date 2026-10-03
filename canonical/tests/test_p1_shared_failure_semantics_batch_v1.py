from __future__ import annotations

import copy
import unittest

from canonical.runtime import contract_native_proof_suites as source
from canonical.runtime import p1_shared_failure_semantics_batch_v1 as batch

CONTRACT = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"


class P1SharedFailureSemanticsBatchV1Tests(unittest.TestCase):
    def test_source_native_case_is_bound_without_oracle_leak(self):
        case = source.generate_case(CONTRACT, 1234567, 4)
        out = batch.instrument_source_case(
            case, surface_id=batch.SURFACES[0], case_index=0
        )
        self.assertEqual(out["status"], "PASS", out)
        self.assertNotIn("_oracle", out["candidate_case"])
        self.assertNotIn("source_case", out["candidate_case"])
        self.assertEqual(out["semantics_counts"]["DIRECT_CONTRACT"], 1)
        self.assertGreaterEqual(out["semantics_counts"]["DERIVED_UPSTREAM"], 1)

    def test_direct_semantics_matches_hidden_injected_cause(self):
        for seed in (11, 101, 1009, 90001):
            case = source.generate_case(CONTRACT, seed, 5)
            out = batch.instrument_source_case(
                case, surface_id=batch.SURFACES[1], case_index=1
            )
            self.assertEqual(out["status"], "PASS", out)
            self.assertEqual(out["cause_step"], case["_oracle"]["cause_step"])
            failed = [
                (row["action_id"], check["failure_semantics"])
                for row in out["candidate_case"]["task"]["trajectory"]
                for check in row["checks"]
                if check["pass"] is False
            ]
            direct = [aid for aid, sem in failed if sem == "DIRECT_CONTRACT"]
            self.assertEqual(direct, [f"A{case['_oracle']['cause_step']}"])

    def test_all_three_frozen_surfaces_execute_through_both_scorers(self):
        beacon = "spent-test-beacon-v1"
        for surface in batch.SURFACES:
            for i in (0, 7, 31, 63):
                out = batch.evaluate_one(
                    beacon=beacon, surface_id=surface, case_index=i
                )
                self.assertTrue(out["pass"], out)
                self.assertTrue(out["v7_intervention_scorer_pass"])
                self.assertTrue(out["source_native_rescue_scorer_pass"])
                self.assertTrue(out["source_native_rescue_pass"])

    def test_seed_is_post_freeze_beacon_sensitive_and_deterministic(self):
        a = batch.derive_seed("beacon-A", batch.SURFACES[0], 0)
        b = batch.derive_seed("beacon-A", batch.SURFACES[0], 0)
        c = batch.derive_seed("beacon-B", batch.SURFACES[0], 0)
        d = batch.derive_seed("beacon-A", batch.SURFACES[1], 0)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(a, d)

    def test_missing_failure_semantics_fails_closed(self):
        case = source.generate_case(CONTRACT, 80001, 3)
        good = batch.instrument_source_case(
            case, surface_id=batch.SURFACES[0], case_index=0
        )
        self.assertEqual(good["status"], "PASS")
        raw = {
            "surface_id": batch.SURFACES[0],
            "case_id": "mutant",
            "source_observation_receipt": "receipt",
            "trajectory": copy.deepcopy(good["candidate_case"]["task"]["trajectory"]),
            "terminal_failed_resources": copy.deepcopy(
                good["candidate_case"]["task"]["terminal_failed_resources"]
            ),
        }
        for row in raw["trajectory"]:
            for check in row["checks"]:
                if check.get("pass") is False:
                    check.pop("failure_semantics", None)
                    from canonical.runtime.p1_shared_failure_semantics_normalizer_v1 import normalize_case
                    out = normalize_case(raw)
                    self.assertEqual(out["status"], "FAIL_CLOSED", out)
                    self.assertIn("FAILURE_SEMANTICS_UNBOUND", out["reason"])
                    return
        self.fail("fixture had no failed check")

    def test_source_cause_tamper_fails_independent_source_scorer(self):
        out = batch.evaluate_one(
            beacon="spent-tamper-beacon",
            surface_id=batch.SURFACES[2],
            case_index=5,
        )
        self.assertTrue(out["pass"], out)
        # The dual-scorer property is checked more directly by adapting an
        # intentionally wrong V7-like output to the original source scorer.
        case = source.generate_case(CONTRACT, 442211, 4)
        wrong_step = case["_oracle"]["cause_step"] + 1
        wrong = {
            "status": "IDENTIFIED",
            "cause_action_id": f"A{wrong_step}",
            "supporting_receipts": ["tampered"],
        }
        adapted = batch._adapt_v7_to_source_candidate(wrong)
        verdict = source.score_case(case, adapted)
        self.assertFalse(verdict["pass"], verdict)

    def test_mutation_preflight_is_fail_closed_and_zero_reality(self):
        out = batch.mutation_preflight()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["fresh_reality_units_consumed"], 0)
        for verdict in out["verdicts"].values():
            self.assertEqual(verdict["status"], "FAIL_CLOSED")

    def test_full_spent_batch_shape_passes(self):
        out = batch.run_batch("spent-unit-test-beacon-v1")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["cases"], batch.TOTAL_CASES)
        self.assertEqual(out["passes"], batch.TOTAL_CASES)
        self.assertEqual(out["failures"], 0)
        self.assertEqual(set(out["by_surface"]), set(batch.SURFACES))
        self.assertEqual(out["terminal_v3_replayed"], 0)
        # This function models the terminal observation and therefore reports
        # one reality unit. This unit-test invocation is explicitly spent and
        # cannot be promoted as terminal evidence.
        self.assertEqual(out["fresh_reality_units_consumed"], 1)
        for row in out["by_surface"].values():
            self.assertTrue(row["all_pass"])
            self.assertTrue(row["both_semantics_classes_present_every_case"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
