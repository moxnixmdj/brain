from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_semantic_identity_carrier_v1 as c

ROOT=Path(__file__).resolve().parents[2]

def manifest():
 return json.loads((ROOT/c.PINS["manifest"][0]).read_text(encoding="utf-8"))

def r12_scope():
 return c.domain.build_claim_scope(
  manifest(),
  "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC",
  epoch=c.EPOCH,
 )

class IdentityCarrierTests(unittest.TestCase):
 def test_current_twelve_semantic_claims_factor_losslessly(self):
  out=c.verify()
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["semantic_leaf_count"],12)
  self.assertEqual(out["factorization_pass_count"],12)
  self.assertEqual(out["unique_claim_id_count"],12)
  self.assertEqual(out["r12_claim_id"],c.EXPECTED_R12_CLAIM_ID)
  self.assertFalse(out["leaf_property_truth_authority"])
  self.assertFalse(out["terminal_authority"])

 def test_exact_r12_identity_carrier_passes_universally_without_sampling(self):
  m=manifest();cs=r12_scope();cert=c.build_certificate(cs)
  out=c.evaluate(m,cs,cert)
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["universal_factorization_proved"])
  self.assertTrue(out["projection_total"])
  self.assertTrue(out["projection_injective"])
  self.assertFalse(out["semantic_information_loss"])
  self.assertEqual(out["claim_id"],c.EXPECTED_R12_CLAIM_ID)

 def test_nonidentity_projection_fails_closed(self):
  m=manifest();cs=r12_scope();cert=c.build_certificate(cs)
  cert["projection"]="HASHED_SUMMARY"
  out=c.evaluate(m,cs,cert)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"IDENTITY_CARRIER_BINDING_DRIFT:projection")

 def test_compressed_or_lossy_carrier_fails_closed(self):
  m=manifest();cs=r12_scope();cert=c.build_certificate(cs)
  cert["semantic_information_loss"]=True
  out=c.evaluate(m,cs,cert)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"IDENTITY_CARRIER_BINDING_DRIFT:semantic_information_loss")

 def test_scope_drift_fails_before_carrier_proof(self):
  m=manifest();cs=r12_scope()
  cs=deepcopy(cs)
  cs["scope_definition"]["domain_definition"]["filters"]=["ONLY_EASY_CASES"]
  cert=c.build_certificate(cs)
  out=c.evaluate(m,cs,cert)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")

 def test_claim_id_substitution_fails_before_carrier_proof(self):
  m=manifest();cs=r12_scope()
  cs=deepcopy(cs);cs["claim"]["claim_id"]="0"*64
  cert=c.build_certificate(cs)
  out=c.evaluate(m,cs,cert)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")

 def test_stale_mission_binding_fails_closed(self):
  m=manifest();cs=r12_scope()
  cs=deepcopy(cs);cs["claim"]["mission_blob_sha"]="0"*40
  # Recompute claim id so the claim is internally self-consistent but stale.
  from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id
  cs["claim"]["claim_id"]=compute_claim_id(cs["claim"])
  cert=c.build_certificate(cs)
  out=c.evaluate(m,cs,cert)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")

 def test_factorization_proof_cannot_be_downgraded_to_sample(self):
  m=manifest();cs=r12_scope();cert=c.build_certificate(cs)
  cert["factorization"]["universal_not_sampled"]=False
  out=c.evaluate(m,cs,cert)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"FACTORIZATION_PROOF_DRIFT:universal_not_sampled")

if __name__=="__main__":
 unittest.main(verbosity=2)
