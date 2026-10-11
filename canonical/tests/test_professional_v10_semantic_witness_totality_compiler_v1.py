from __future__ import annotations
import unittest
from unittest.mock import patch

from canonical.runtime import professional_v10_semantic_witness_totality_compiler_v1 as v
from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as claims

class Tests(unittest.TestCase):
 def test_current_compiles_all_twelve(self):
  o=v.compile_candidates()
  self.assertTrue(o["pass"],o)
  self.assertEqual(o["compiled_root_count"],12)
  self.assertEqual(o["claim_scoped_totality_candidate_count"],12)
  self.assertEqual(o["bounded_positive_witness_count"],12)
  self.assertEqual(o["fail_closed_complement_count"],12)
  self.assertEqual(len({x["root_id"] for x in o["roots"]}),12)

 def test_claim_binding_matches_exact_v10_batch(self):
  o=v.compile_candidates();self.assertTrue(o["pass"],o)
  cb=claims.verify()
  expected={(x["root_id"],x["leaf_id"],x["claim_id"]) for x in cb["rows"]}
  observed={(x["root_id"],x["leaf_id"],x["semantic_claim_id"]) for x in o["roots"]}
  self.assertEqual(observed,expected)

 def test_every_root_is_positive_bounded_plus_fail_closed_complement(self):
  o=v.compile_candidates();self.assertTrue(o["pass"],o)
  for row in o["roots"]:
   self.assertTrue(row["bounded_positive_witness_proved"],row)
   self.assertTrue(row["positive_route_nonvacuous"],row)
   self.assertTrue(row["fail_closed_complement_proved"],row)
   self.assertEqual(row["outside_bounded_positive_domain_disposition"],"FAIL_CLOSED_NONPOSITIVE")
   self.assertTrue(row["claim_scoped_totality_proved"],row)
   self.assertTrue(row["cc_r1_reality_containment_proved"],row)
   self.assertTrue(row["cc_r2_mission_soundness_proved"],row)
   self.assertTrue(row["cc_r3_terminal_closure_proved"],row)

 def test_candidate_never_self_authorizes_r4_or_property_truth(self):
  o=v.compile_candidates();self.assertTrue(o["pass"],o)
  self.assertFalse(o["independent_verified"])
  self.assertFalse(o["r4_proof_realization_authority"])
  self.assertFalse(o["semantic_property_truth_authority"])
  self.assertFalse(o["terminal_authority"])
  for row in o["roots"]:
   self.assertFalse(row["independent_verified"],row)
   self.assertFalse(row["r4_proof_realization_authority"],row)
   self.assertFalse(row["semantic_property_truth_authority"],row)

 def test_missing_or_stale_witness_ref_fails_closed(self):
  original=v._safe_ref
  calls={"n":0}
  def bad(root,ref):
   calls["n"]+=1
   if calls["n"]==1:return False
   return original(root,ref)
  with patch.object(v,"_safe_ref",side_effect=bad):
   o=v.compile_candidates()
  self.assertFalse(o["pass"])
  self.assertTrue(str(o["reason"]).startswith("WITNESS_REF_NOT_CURRENT:"))

 def test_binder_shape_drift_fails_closed(self):
  fake={"pass":True,"unknown_or_mismatch_authorized":True,
        "required_totality_fields":list(v.binder.REQUIRED_TOTALITY_FIELDS)}
  with patch.object(v.binder,"prove_fail_closed_shape",return_value=fake):
   o=v.compile_candidates()
  self.assertFalse(o["pass"])
  self.assertEqual(o["reason"],"BINDER_FAIL_CLOSED_SHAPE_NOT_PROVED")

if __name__=="__main__":unittest.main(verbosity=2)
