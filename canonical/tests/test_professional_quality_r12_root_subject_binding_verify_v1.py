from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_r12_root_subject_binding_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text())

class Tests(unittest.TestCase):
 def run_patch(self,patches):
  old=v.read
  def fake(root,p,h):
   if p in patches:return deepcopy(patches[p])
   return old(root,p,h)
  try:
   v.read=fake
   return v.verify()
  finally:v.read=old
 def test_positive_real_repository_bytes(self):
  o=v.verify();self.assertTrue(o["pass"],o);self.assertTrue(o["root_subject_binding_authority"]);self.assertFalse(o["same_subject_composition_pass"]);self.assertFalse(o["terminal_authority"])
 def test_self_authority_fails_closed(self):
  b=load(v.BIND);b["quality_authority"]=True
  self.assertEqual(self.run_patch({v.BIND:b})["reason"],"SELF_AUTHORITY_FORBIDDEN:quality_authority")
 def test_unknown_defeater_overclaim_fails_closed(self):
  b=load(v.BIND);b["unknown_defeater_completeness_proved"]=True
  self.assertEqual(self.run_patch({v.BIND:b})["reason"],"UNKNOWN_DEFEATER_OVERCLAIM")
 def test_prior_subject_drift_fails_closed(self):
  wl=load(v.REFS["prior_root_binding_worklist"][0]);row=next(x for x in wl["roots"] if x["root_id"]=="R10_ANALYSIS_DECISION")
  bd=load(row["binding"]["path"]);bd["subject_sha256"]="0"*64
  self.assertEqual(self.run_patch({row["binding"]["path"]:bd})["reason"],"PRIOR_ROOT_SUBJECT_DRIFT:R10_ANALYSIS_DECISION")
 def test_missing_prior_independent_authority_fails_closed(self):
  wl=load(v.REFS["prior_root_binding_worklist"][0]);row=next(x for x in wl["roots"] if x["root_id"]=="R11_ADAPTIVE_INTEGRITY_SECURITY")
  vd=load(row["verification"]["path"]);vd["root_subject_binding_authority"]=False
  self.assertEqual(self.run_patch({row["verification"]["path"]:vd})["reason"],"PRIOR_ROOT_AUTHORITY_MISSING:R11_ADAPTIVE_INTEGRITY_SECURITY")
 def test_known_defeater_scope_widening_fails_closed(self):
  p=v.REFS["known_defeater_binding"][0];d=load(p);d["hard_nonclaims"]=[]
  self.assertEqual(self.run_patch({p:d})["reason"],"KNOWN_DEFEATER_SCOPE_OVERCLAIM")
 def test_composition_gate_self_closure_forbidden(self):
  p=v.REFS["composition_gate"][0];d=load(p);d["authority_boundary"]["quality_authority"]=True
  self.assertEqual(self.run_patch({p:d})["reason"],"COMPOSITION_GATE_BOUNDARY_INVALID")

if __name__=="__main__":unittest.main(verbosity=2)
