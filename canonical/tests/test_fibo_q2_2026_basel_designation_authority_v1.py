import unittest
from pathlib import Path

from canonical.runtime import fibo_q2_2026_basel_designation_authority_v1 as basel


ROOT = Path(__file__).resolve().parents[2]
BASEL = (
    "https://spec.edmcouncil.org/fibo/ontology/"
    "SEC/Securities/EuropeanSecurities/EUSecuritiesRestrictions/BaselIIIDesignation"
)
CET1 = (
    "https://spec.edmcouncil.org/fibo/ontology/"
    "SEC/Securities/EuropeanSecurities/EUSecuritiesRestrictions/CommonEquityTier1"
)
AT1 = (
    "https://spec.edmcouncil.org/fibo/ontology/"
    "SEC/Securities/EuropeanSecurities/EUSecuritiesRestrictions/AdditionalTier1Capital"
)
TIER1 = (
    "https://spec.edmcouncil.org/fibo/ontology/"
    "SEC/Securities/EuropeanSecurities/EUSecuritiesRestrictions/Tier1Capital"
)
TIER2 = (
    "https://spec.edmcouncil.org/fibo/ontology/"
    "SEC/Securities/EuropeanSecurities/EUSecuritiesRestrictions/Tier2Capital"
)


class Tests(unittest.TestCase):
    def test_pack_authenticates_complete_basel_designation_fragment(self):
        out = basel.load_pack(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["designation_class_id"], BASEL)
        self.assertEqual(
            set(out["member_ids"]),
            {CET1, AT1, TIER1, TIER2},
        )
        self.assertTrue(out["member_set_complete_relative_to_bound_source"])
        self.assertFalse(out["open_world_finance_ontology_complete"])
        self.assertFalse(out["imported_ontology_closure_complete"])

    def test_abbreviations_and_labels_retrieve_candidates_without_proving_identity(self):
        cet1 = basel.exact_surface_candidates("CET1", repo_root=ROOT)
        self.assertTrue(cet1["pass"], cet1)
        self.assertEqual(cet1["candidate_concept_ids"], [CET1])
        self.assertFalse(cet1["contextual_semantic_identity_proved"])
        self.assertFalse(cet1["semantic_truth_authority"])

        at1 = basel.exact_surface_candidates("additional tier 1 capital", repo_root=ROOT)
        self.assertEqual(at1["candidate_concept_ids"], [AT1])

    def test_type_membership_receipt_is_semantic_truth_but_not_terminal_authority(self):
        req = basel.make_type_membership_request(CET1, BASEL, repo_root=ROOT)
        out = basel.verify_type_membership_receipt(req, repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relation"], "INSTANCE_OF")
        self.assertEqual(out["source_id"], CET1)
        self.assertEqual(out["target_id"], BASEL)
        self.assertTrue(out["source_semantics_authenticated"])
        self.assertTrue(out["target_semantics_authenticated"])
        self.assertTrue(out["relation_semantics_authenticated"])
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["acceptance_authority"])

    def test_all_four_members_have_verified_type_membership(self):
        pack = basel.load_pack(repo_root=ROOT)
        for member_id in pack["member_ids"]:
            req = basel.make_type_membership_request(member_id, BASEL, repo_root=ROOT)
            out = basel.verify_type_membership_receipt(req, repo_root=ROOT)
            self.assertTrue(out["pass"], (member_id, out))

    def test_unknown_surface_never_coerces_to_nearest_basel_designation(self):
        out = basel.exact_surface_candidates("loss-absorbing cushion", repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["candidate_concept_ids"], [])
        self.assertFalse(out["contextual_semantic_identity_proved"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_unknown_member_cannot_receive_type_membership_receipt(self):
        bogus = CET1 + "Bogus"
        try:
            req = basel.make_type_membership_request(bogus, BASEL, repo_root=ROOT)
        except Exception:
            return
        out = basel.verify_type_membership_receipt(req, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_wrong_target_cannot_receive_type_membership_receipt(self):
        bogus_target = BASEL + "Other"
        try:
            req = basel.make_type_membership_request(CET1, bogus_target, repo_root=ROOT)
        except Exception:
            return
        out = basel.verify_type_membership_receipt(req, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertFalse(out["semantic_truth_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
