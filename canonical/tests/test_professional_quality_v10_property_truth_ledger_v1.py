from __future__ import annotations

from copy import deepcopy
import json
from unittest.mock import patch
import unittest

from canonical.runtime import professional_quality_v10_property_truth_ledger_v1 as v


R1="PQ::R1_TARGET_SPECIFICATION::SEMANTIC"


class Tests(unittest.TestCase):
    def test_current_r1_registry_yields_thirteen_of_twenty_four(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["verified_execution_leaf_count"],12)
        self.assertEqual(out["verified_semantic_leaf_count"],1)
        self.assertEqual(out["verified_semantic_leaf_ids"],[R1])
        self.assertEqual(out["verified_leaf_count"],13)
        self.assertEqual(out["open_leaf_count"],11)
        self.assertEqual(out["open_execution_leaf_ids"],[])
        self.assertEqual(out["rejected_semantic_receipt_count"],0)
        self.assertTrue(out["execution_identity_transport_proved"])
        self.assertFalse(out["promotion_ready"])
        self.assertFalse(out["terminal_authority"])

    def test_execution_identity_drift_fails_closed(self):
        real=v._load
        def altered(root,rel,expected=None):
            doc=deepcopy(dict(real(root,rel,expected)))
            if rel==v.NEW_MANIFEST_PATH:
                doc["roots"][0]["execution_leaf"]["acceptance"]="DRIFT"
            return doc
        with patch.object(v,"_load",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"EXECUTION_IDENTITY_DRIFT:R1_TARGET_SPECIFICATION")

    def test_stale_r1_semantic_basis_reopens_only_r1(self):
        real=v._safe_entry
        def altered(root,entry):
            doc,err=real(root,entry)
            if doc is not None and doc.get("leaf_id")==R1:
                doc=deepcopy(dict(doc))
                doc["verification_basis"][0]["git_blob_sha"]="0"*40
            return doc,err
        with patch.object(v,"_safe_entry",side_effect=altered):
            out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["verified_semantic_leaf_count"],0)
        self.assertIn(R1,out["open_semantic_leaf_ids"])
        self.assertEqual(out["verified_leaf_count"],12)
        self.assertEqual(out["rejected_semantic_receipt_count"],1)

    def test_unknown_semantic_leaf_in_registry_fails_closed(self):
        real=v._load
        def altered(root,rel,expected=None):
            doc=deepcopy(dict(real(root,rel,expected)))
            if rel==v.SEMANTIC_REGISTRY_PATH:
                doc["semantic_receipts"]["PQ::UNKNOWN::SEMANTIC"]=[]
            return doc
        with patch.object(v,"_load",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"UNKNOWN_SEMANTIC_LEAF_IDS")

    def test_execution_independent_replay_is_load_bearing(self):
        real=v._load
        def altered(root,rel,expected=None):
            doc=deepcopy(dict(real(root,rel,expected)))
            if rel==v.EXEC_VERIFY_PATH:
                doc["independent_replay"]["direct_registry_v2_eval"]["rejected_receipt_count"]=1
            return doc
        with patch.object(v,"_load",side_effect=altered):
            out=v.verify()
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"EXECUTION_INDEPENDENT_REPLAY_NOT_EXACT_12_OF_12")

    def test_partial_property_truth_never_promotes_global_authority(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["verified_leaf_count"],13)
        for key in ("quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
            self.assertFalse(out[key],key)
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
