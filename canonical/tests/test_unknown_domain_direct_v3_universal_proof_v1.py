import unittest

from canonical.runtime import unknown_domain_direct_candidate_v2 as candidate
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as proof


class UnknownDomainV3UniversalProofTests(unittest.TestCase):

    def test_universal_proof_is_content_bound_zero_reality(self):
        out=proof.prove()
        self.assertEqual(out["status"],"PASS__UNIVERSAL_OVER_EXACT_COLLISION_TOTALIZED_V3_GENERATOR_DOMAIN")
        self.assertEqual(out["scope"]["production_population_cases"],27)
        self.assertEqual(out["scope"]["terminal_or_production_cases_generated"],0)
        self.assertIs(out["fresh_reality_required_for_this_exact_v3_generator_claim"],False)
        self.assertEqual(out["production_execution_information_gain_for_this_exact_v3_generator_claim"],0)
        self.assertEqual(out["exact_subject_blobs"],proof.EXPECTED_BLOBS)

    def test_identifier_construction_is_bijection_not_hash_uniqueness(self):
        out=proof.prove()["identifier_totality_proof"]
        self.assertEqual(out["status"],"PROVED_BY_BIJECTION_CONSTRUCTION")
        self.assertIs(out["uniqueness_depends_on_hash_collision_resistance"],False)
        self.assertIs(out["uniform_randomness_required"],False)
        for n in out["permutation_sizes"]:
            for secret in (b"A"*32,b"B"*32,b"\x00"*32,b"\xff"*32):
                p=g3._perm(secret,"BEACON-VALID-0123456789",f"n={n}",n)
                self.assertEqual(len(p),n)
                self.assertEqual(len(set(p)),n)
                self.assertEqual(set(p),set(range(n)))

    def test_transfer_structural_margins_are_strict(self):
        out=proof.prove()["transfer_proof"]
        self.assertIs(out["all_six_families_universal"],True)
        self.assertEqual(out["max_transfer_probes"],2)
        self.assertEqual(out["full_rediscovery_probe_floor"],3)
        self.assertGreater(out["affine_min_wrong_support_output_gap"],2.84)
        self.assertGreaterEqual(out["complement_min_wrong_support_output_gap"],4.75)
        self.assertGreater(out["sat_mono_conservative_min_wrong_support_output_gap"],out["sat_mono_max_candidate_close_tolerance"])
        self.assertGreater(out["sign_negative_probe_min_shifted_distractor_value"],0)
        self.assertGreater(out["step_min_wrong_side_margin"],2.54)
        self.assertGreaterEqual(out["add2_min_wrong_support_first_probe_gap"],1.5)
        self.assertIs(out["add2_true_support_role_swap_safe"],True)

    def test_abstention_classes_are_collision_totalized(self):
        out=proof.prove()["abstention_proof"]
        self.assertIs(out["all_three_classes_universal"],True)
        self.assertIs(out["identifier_collision_can_change_class_semantics"],False)
        self.assertIn("INTENTIONALLY_SHARE",out["identifiable"])
        self.assertIn("STRUCTURALLY_DISTINCT",out["nonidentifiable"])
        self.assertIn("UNIQUE_MINIMUM_COST",out["underspecified"])

    def test_nonproduction_fixture_regression_multiple_beacons(self):
        # Regression evidence only; universality comes from the structural proof.
        for beacon in (
            "V3-QUALIFICATION-ALPHA-0001",
            "V3-QUALIFICATION-BETA-0002",
            "V3-QUALIFICATION-GAMMA-0003",
        ):
            packet=g3.generate_qualification_fixture_population(beacon=beacon)
            self.assertIs(packet["production"],False)
            self.assertEqual(packet["case_count"],27)
            self.assertEqual(packet["identifier_totality"],g3.IDENTIFIER_TOTALITY)
            rows=[]
            for visible,hidden in zip(packet["visible_cases"],packet["hidden_records"]):
                out=harness.execute_case(
                    candidate_step=candidate.step,
                    case_visible=visible,
                    hidden_record=hidden,
                )
                rows.append(out["scorer_result"])
            agg=scorer.aggregate(rows)
            self.assertIs(agg["all_27_cases_pass"],True)

    def test_no_credit_and_no_open_world_overclaim(self):
        out=proof.prove()
        self.assertEqual(out["accounting"]["acceptance_credit_delta"],0)
        self.assertEqual(out["accounting"]["capability_credit_delta"],0)
        self.assertEqual(out["accounting"]["ownership_credit_delta"],0)
        self.assertTrue(any("OPEN_WORLD" in x for x in out["hard_nonclaims"]))
        self.assertTrue(any("FALSE_V2" in x for x in out["hard_nonclaims"]))
        self.assertTrue(any("INDEPENDENT_CONTENT_BOUND_VERIFICATION" in x for x in out["hard_nonclaims"]))


if __name__=="__main__":
    unittest.main()
