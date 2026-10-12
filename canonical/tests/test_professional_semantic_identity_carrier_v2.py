from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_semantic_identity_carrier_v2 as c

ROOT=Path(__file__).resolve().parents[2]

def pack():
 return json.loads((ROOT/c.PACK_PATH).read_text(encoding="utf-8"))

def r12_row():
 return next(x for x in pack()["claims"] if x["leaf_id"]=="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC")

class CurrentIdentityCarrierV2Tests(unittest.TestCase):
 def test_current_v2_twelve_semantic_claims_factor_losslessly(self):
  out=c.verify(repo_root=ROOT)
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["semantic_leaf_count"],12)
  self.assertEqual(out["factorization_pass_count"],12)
  self.assertEqual(out["mission_sufficient_carrier_factorization_proved_count"],12)
  self.assertEqual(out["unique_claim_id_count"],12)
  self.assertEqual(out["r12_claim_id"],c.EXPECTED_R12_CLAIM_ID)
  self.assertFalse(out["semantic_truth_authority"])
  self.assertFalse(out["terminal_authority"])

 def test_exact_current_r12_identity_carrier_passes_without_sampling(self):
  row=r12_row(); cert=c.build_certificate(row)
  mission=pack()["mission_blob_sha"]
  out=c.evaluate_claim(row,cert,current_mission_blob_sha=mission)
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["universal_factorization_proved"])
  self.assertTrue(out["projection_total"])
  self.assertTrue(out["projection_injective"])
  self.assertFalse(out["semantic_information_loss"])
  self.assertEqual(out["claim_id"],c.EXPECTED_R12_CLAIM_ID)

 def test_nonidentity_projection_fails_closed(self):
  row=r12_row(); cert=c.build_certificate(row); cert["projection"]="HASHED_SUMMARY"
  out=c.evaluate_claim(row,cert,current_mission_blob_sha=pack()["mission_blob_sha"])
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"IDENTITY_CARRIER_BINDING_DRIFT:projection")

 def test_current_claim_semantics_mutation_fails_closed(self):
  row=deepcopy(r12_row())
  row["semantics"]["true_when"]+="__MUTATED"
  cert=c.build_certificate(row)
  out=c.evaluate_claim(row,cert,current_mission_blob_sha=pack()["mission_blob_sha"])
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"SEMANTICS_HASH_MISMATCH")

 def test_duplicate_claim_identity_fails_closed(self):
  d=pack()
  d["claims"][1]["frozen_claim"]["claim_id"]=d["claims"][0]["frozen_claim"]["claim_id"]
  out=c.evaluate_pack(d,current_mission_blob_sha=d["mission_blob_sha"])
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"SEMANTIC_CLAIM_IDENTITIES_NOT_UNIQUE")

 def test_stale_mission_binding_fails_closed(self):
  d=pack()
  out=c.evaluate_pack(d,current_mission_blob_sha="0"*40)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"PACK_MISSION_BINDING_STALE")

 def test_scope_hash_drift_fails_closed(self):
  row=deepcopy(r12_row())
  row["scope_definition_sha256"]="0"*64
  cert=c.build_certificate(row)
  out=c.evaluate_claim(row,cert,current_mission_blob_sha=c._blob(ROOT/c.MISSION_PATH))
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"ROW_SCOPE_CLAIM_SCOPE_MISMATCH")

if __name__=="__main__":
 unittest.main(verbosity=2)
