from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime import professional_semantic_identity_carrier_v3 as c
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as p


class ProfessionalSemanticIdentityCarrierV3Tests(unittest.TestCase):
    def test_current_v3_claims_factor_12_of_12(self):
        out=c.verify()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_leaf_count"],12)
        self.assertEqual(out["factorization_pass_count"],12)
        self.assertEqual(out["mission_sufficient_carrier_factorization_proved_count"],12)
        self.assertEqual(out["unique_claim_id_count"],12)
        self.assertEqual(out["r12_claim_id"],c.EXPECTED_R12_CLAIM_ID)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_mission_authority_binding_drift_fails(self):
        pack=p.verify()
        self.assertTrue(pack["pass"],pack)
        pack=deepcopy(pack)
        pack["mission_blob_sha"]="0"*40
        out=c.evaluate_pack(pack)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"MISSION_AUTHORITY_BINDING_DRIFT")

    def test_duplicate_claim_identity_fails(self):
        pack=p.verify()
        self.assertTrue(pack["pass"],pack)
        pack=deepcopy(pack)
        pack["claims"][1]["frozen_claim"]["claim_id"]=pack["claims"][0]["frozen_claim"]["claim_id"]
        out=c.evaluate_pack(pack)
        self.assertFalse(out["pass"])

    def test_r12_claim_identity_is_current_v3(self):
        pack=p.verify()
        self.assertTrue(pack["pass"],pack)
        row=next(x for x in pack["claims"] if x["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC")
        self.assertEqual(row["frozen_claim"]["claim_id"],c.EXPECTED_R12_CLAIM_ID)


if __name__=="__main__":
    unittest.main(verbosity=2)
