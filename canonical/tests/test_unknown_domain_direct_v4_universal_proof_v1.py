import hashlib
import unittest

from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v4_universal_proof_v1 as proof


class UnknownDomainV4UniversalProofTests(unittest.TestCase):
    def test_content_bound_total_exact_theorem(self):
        out=proof.prove()
        self.assertEqual(out["status"],"PASS__UNIVERSAL_OVER_ALL_VALID_TOTALIZED_V3_INPUTS_WITH_EXACT_FLOAT_V3_CANDIDATE")
        self.assertFalse(out["identifier_totality_proof"]["hash_collision_resistance_required"])
        self.assertTrue(out["transfer_proof"]["add2_exact_float_order_repaired"])
        self.assertEqual(out["scope"]["terminal_or_production_cases_generated"],0)
        self.assertEqual(out["accounting"]["acceptance_credit_delta"],0)

    def test_totalized_generator_is_injective_for_adversarial_digest_inputs(self):
        for n in (2,3,4,12,15):
            for secret in (b"\x00"*32,b"\xff"*32,b"A"*32,b"B"*32):
                p=g3._perm(secret,"TOTALITY-BEACON-0123456789",f"T={n}",n)
                self.assertEqual(len(p),n)
                self.assertEqual(set(p),set(range(n)))

    def test_float_safe_candidate_passes_totalized_generator_regressions(self):
        for beacon in (
            "V4-TOTAL-EXACT-ALPHA-0001",
            "V4-TOTAL-EXACT-BETA-0002",
            "V4-TOTAL-EXACT-GAMMA-0003",
        ):
            packet=g3.generate_qualification_fixture_population(beacon=beacon)
            results=[]
            for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
                out=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
                results.append(out["scorer_result"])
            self.assertTrue(scorer.aggregate(results)["all_27_cases_pass"])

    def test_v2_float_counterexample_stays_falsified_and_v3_repairs_it(self):
        secret=hashlib.sha256(b"secret-full-6").digest()
        beacon="CEFULL-00000006-20261005-LONG"
        visible,hidden=g3._transfer_case(secret,beacon,4,namespace="V4REG")
        bad=harness.execute_case(candidate_step=c2.step,case_visible=visible,hidden_record=hidden)
        good=harness.execute_case(candidate_step=c3.step,case_visible=visible,hidden_record=hidden)
        self.assertFalse(bad["scorer_result"]["pass"])
        self.assertIn("DOMAIN_B_TERMINAL_CONSEQUENCE_WRONG",bad["scorer_result"]["errors"])
        self.assertTrue(good["scorer_result"]["pass"],good["scorer_result"])
        self.assertEqual(good["candidate_terminal_action"]["terminal_consequence"],hidden["gold_terminal_consequence"])
        self.assertEqual(good["probe_count"],1)

    def test_original_quantifier_is_not_weakened(self):
        out=proof.prove()
        self.assertEqual(out["scope"]["beacon"],"ALL_VALID_STRINGS_LENGTH_GE_16")
        self.assertIn("ALL_VALUES_ACCEPTED",out["scope"]["evaluator_secret"])
        self.assertFalse(out["identifier_totality_proof"]["accepted_secret_or_beacon_rejected_due_identifier_collision"])


if __name__=="__main__":
    unittest.main()
