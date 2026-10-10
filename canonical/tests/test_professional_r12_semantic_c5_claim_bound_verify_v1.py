from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r12_semantic_c5_claim_bound_verify_v1 as v
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]

def docs():
 claim=json.loads((ROOT/v.CLAIM_PATH).read_text())
 cert=json.loads((ROOT/v.CERT_PATH).read_text())
 bout=batch.verify(repo_root=ROOT)
 return claim,cert,bout

class R12SemanticC5ClaimBoundVerifyV1Tests(unittest.TestCase):
 def test_current_exact_claim_c5_passes_only_coverage_accounting(self):
  out=v.verify(repo_root=ROOT)
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["c5_coverage_accounting_proved"])
  self.assertTrue(out["whole_leaf_domain_equivalence_proved"])
  self.assertTrue(out["whole_leaf_scope_complete"])
  self.assertFalse(out["material_defeater_totality_proved"])
  self.assertFalse(out["cc_r3_terminal_closure"])
  self.assertFalse(out["semantic_property_truth_authority"])
  self.assertEqual(out["terminal_credit_delta"],0)

 def test_scope_filter_narrowing_fails_closed(self):
  claim,cert,bout=docs()
  claim=deepcopy(claim)
  claim["claim_scope"]["scope_definition"]["domain_definition"]["filters"]=["ONLY_EASY_CASES"]
  out=v.evaluate(claim,cert,bout,repo_root=ROOT)
  self.assertFalse(out["pass"])
  self.assertIn(out["reason"],{"WHOLE_DOMAIN_EQUIVALENCE_NOT_PROVED","WHOLE_DOMAIN_ACCOUNTING_DRIFT"})

 def test_claim_identity_mismatch_fails_closed(self):
  claim,cert,bout=docs()
  claim=deepcopy(claim);claim["claim_id"]="0"*64
  out=v.evaluate(claim,cert,bout,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"FROZEN_CLAIM_IDENTITY_DRIFT")

 def test_scope_batch_incompleteness_fails_closed(self):
  claim,cert,bout=docs()
  bout=deepcopy(bout)
  row=next(x for x in bout["rows"] if x["leaf_id"]==v.LEAF_ID)
  row["whole_leaf_scope_complete"]=False
  out=v.evaluate(claim,cert,bout,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"R12_SCOPE_BATCH_BINDING_INVALID")

 def test_stronger_totality_cannot_be_smuggled_into_c5(self):
  claim,cert,bout=docs()
  cert=deepcopy(cert);cert["resulting_cut"]["stronger_material_defeater_totality_open"]=False
  out=v.evaluate(claim,cert,bout,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"STRONGER_TOTALITY_MUST_REMAIN_OPEN")

 def test_credit_self_grant_fails_closed(self):
  claim,cert,bout=docs()
  cert=deepcopy(cert);cert["accounting"]["property_truth_credit_delta"]=1
  out=v.evaluate(claim,cert,bout,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"NONZERO_CREDIT_FORBIDDEN")

if __name__=="__main__":
 unittest.main(verbosity=2)
