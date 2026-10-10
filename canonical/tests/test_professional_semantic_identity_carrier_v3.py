from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_semantic_identity_carrier_v3 as c
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3

ROOT=Path(__file__).resolve().parents[2]

def docs():
    pointer=json.loads((ROOT/c.MISSION_POINTER).read_text())
    authority=json.loads((ROOT/c.MISSION_AUTHORITY).read_text())
    pack=pack_v3.verify(repo_root=ROOT)
    return pointer,authority,pack

class StableIdentityCarrierV3Tests(unittest.TestCase):
    def test_current_v3_twelve_claims_factor_losslessly(self):
        out=c.verify(repo_root=ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_leaf_count"],12)
        self.assertEqual(out["factorization_pass_count"],12)
        self.assertEqual(out["mission_sufficient_carrier_factorization_proved_count"],12)
        self.assertEqual(out["r12_claim_id"],c.EXPECTED_R12_CLAIM_ID)
        self.assertFalse(out["cross_claim_root_transport_authorized"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_pointer_bookkeeping_drift_does_not_change_stable_claim_factorization(self):
        p,a,pack=docs()
        p=deepcopy(p); p["synthetic_currentness_only"]={"n":1}
        out=c.evaluate_pack(
            pack,current_pointer=p,mission_authority=a,
            mission_authority_blob_sha=c.MISSION_AUTHORITY_BLOB,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["r12_claim_id"],c.EXPECTED_R12_CLAIM_ID)

    def test_pointer_objective_drift_fails_closed(self):
        p,a,pack=docs()
        p=deepcopy(p); p["real_objective"]+="__DRIFT"
        out=c.evaluate_pack(
            pack,current_pointer=p,mission_authority=a,
            mission_authority_blob_sha=c.MISSION_AUTHORITY_BLOB,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"V3_STABLE_CLAIM_GUARD_REJECTED")

    def test_semantics_mutation_fails_closed(self):
        p,a,pack=docs()
        pack=deepcopy(pack)
        row=next(x for x in pack["claims"] if x["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC")
        row["semantics"]["true_when"]+="__MUTATED"
        out=c.evaluate_pack(
            pack,current_pointer=p,mission_authority=a,
            mission_authority_blob_sha=c.MISSION_AUTHORITY_BLOB,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"V3_IDENTITY_FACTORIZATION_MEMBER_FAILED")

    def test_duplicate_claim_id_fails_closed(self):
        p,a,pack=docs()
        pack=deepcopy(pack)
        pack["claims"][1]["frozen_claim"]["claim_id"]=pack["claims"][0]["frozen_claim"]["claim_id"]
        out=c.evaluate_pack(
            pack,current_pointer=p,mission_authority=a,
            mission_authority_blob_sha=c.MISSION_AUTHORITY_BLOB,
        )
        self.assertFalse(out["pass"])

    def test_wrong_mission_authority_blob_fails_closed(self):
        p,a,pack=docs()
        out=c.evaluate_pack(
            pack,current_pointer=p,mission_authority=a,
            mission_authority_blob_sha="0"*40,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"V3_PACK_MISSION_AUTHORITY_DRIFT")

if __name__=="__main__":
    unittest.main(verbosity=2)
