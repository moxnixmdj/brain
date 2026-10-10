from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from canonical.runtime import professional_r12_semantic_leaf_property_truth_v1 as v


class Tests(unittest.TestCase):
    def test_exact_current_claim_proves_r12_semantic_leaf_only(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["semantic_leaf_property_truth_proved"])
        self.assertTrue(out["leaf_semantic_satisfied"])
        self.assertTrue(out["claim_scoped_totality_proved"])
        self.assertTrue(out["cc_r1_reality_containment_proved"])
        self.assertTrue(out["cc_r2_mission_soundness_proved"])
        self.assertTrue(out["cc_r3_terminal_closure_proved"])
        self.assertTrue(out["r4_proof_realization_authority"])
        self.assertFalse(out["cross_claim_transport"])
        self.assertFalse(out["finite_catalog_completeness_claim"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_root_runtime_rejection_blocks_property_truth(self):
        with patch.object(v.roots,"verify",return_value={"pass":False}):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ROOT_REGISTRY_RUNTIME_REJECTED")

    def test_independent_registry_receipt_is_load_bearing(self):
        original=v._load

        def altered(root,rel,expected):
            doc=deepcopy(dict(original(root,rel,expected)))
            if rel==v.ROOT_RECEIPT_PATH:
                doc["pass"]=False
            return doc

        with patch.object(v,"_load",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ROOT_REGISTRY_INDEPENDENT_RECEIPT_NOT_PASS")

    def test_registry_result_hash_drift_fails(self):
        original=v._load

        def altered(root,rel,expected):
            doc=deepcopy(dict(original(root,rel,expected)))
            if rel==v.ROOT_RECEIPT_PATH:
                doc["independent_replay"]["verifier_result_sha256"]="0"*64
            return doc

        with patch.object(v,"_load",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ROOT_REGISTRY_RERUN_RESULT_HASH_DRIFT")

    def test_root_inclusion_identity_drift_fails(self):
        original=v._load

        def altered(root,rel,expected):
            doc=deepcopy(dict(original(root,rel,expected)))
            if rel==v.REGISTRY_PATH:
                doc["root_identities"][2]["claim"]="B_plus SUBSETEQ SOMETHING_ELSE"
            return doc

        with patch.object(v,"_load",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ROOT_INCLUSION_IDENTITY_DRIFT")

    def test_target_quantification_drift_fails(self):
        original=v._load

        def altered(root,rel,expected):
            doc=deepcopy(dict(original(root,rel,expected)))
            if rel==v.CLAIM_PATH:
                doc["target_predicate"]["quantification"]="SOME_INPUTS"
            return doc

        with patch.object(v,"_load",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"TARGET_QUANTIFICATION_DRIFT")

    def test_r4_does_not_grant_global_authority(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        for key in (
            "quality_authority","acceptance_authority","promotion_authority","terminal_authority"
        ):
            self.assertFalse(out[key],key)


if __name__=="__main__":
    unittest.main(verbosity=2)
