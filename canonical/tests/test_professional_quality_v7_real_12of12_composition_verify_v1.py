from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_v7_real_12of12_composition_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
 def run_patch(self,patches):
  old=v._read
  def fake(root,p,h):
   if p in patches:return deepcopy(patches[p])
   return old(root,p,h)
  try:v._read=fake;return v.verify()
  finally:v._read=old
 def test_positive_real_repository_bytes(self):
  o=v.verify();self.assertTrue(o["pass"],o);self.assertTrue(o["composition_admissible"]);self.assertEqual(o["verified_root_subject_binding_count"],12);self.assertFalse(o["professional_quality_closed"]);self.assertFalse(o["quality_authority"]);self.assertFalse(o["terminal_authority"])
 def test_missing_r12_row_fails_closed(self):
  wl=load(v.WORKLIST);wl["roots"]=[x for x in wl["roots"] if x["root_id"]!="R12_META_COMPOSITION_CLOSURE"]
  self.assertEqual(self.run_patch({v.WORKLIST:wl})["reason"],"WORKLIST_ROOT_SET_INVALID")
 def test_r12_subject_drift_fails_closed(self):
  wl=load(v.WORKLIST);row=next(x for x in wl["roots"] if x["root_id"]=="R12_META_COMPOSITION_CLOSURE");p=row["binding"]["path"];d=load(p);d["subject_sha256"]="0"*64
  self.assertEqual(self.run_patch({p:d})["reason"],"SUBJECT_BINDING_VERIFY_IDENTITY_MISMATCH")
 def test_r12_receipt_authority_missing_fails_closed(self):
  wl=load(v.WORKLIST);row=next(x for x in wl["roots"] if x["root_id"]=="R12_META_COMPOSITION_CLOSURE");p=row["verification"]["path"];d=load(p);d["root_subject_binding_authority"]=False
  self.assertEqual(self.run_patch({p:d})["reason"],"ROOT_SUBJECT_BINDING_AUTHORITY_REQUIRED")
 def test_scoped_root_cover_must_be_complete(self):
  d=load(v.REGISTRY);d["entries"]=[x for x in d["entries"] if x.get("root_id")!="R12_META_COMPOSITION_CLOSURE"]
  self.assertEqual(self.run_patch({v.REGISTRY:d})["reason"],"SCOPED_ROOT_COVER_INCOMPLETE")
 def test_adapter_public_success_required(self):
  d=load(v.GATE_ADAPTER_VERIFY);d["public_runner"]["conclusion"]="failure"
  self.assertEqual(self.run_patch({v.GATE_ADAPTER_VERIFY:d})["reason"],"GATE_ADAPTER_NOT_INDEPENDENTLY_VERIFIED")
 def test_root_terminal_self_authority_fails_closed(self):
  wl=load(v.WORKLIST);row=next(x for x in wl["roots"] if x["root_id"]=="R10_ANALYSIS_DECISION");p=row["binding"]["path"];d=load(p);d["terminal_authority"]=True
  self.assertEqual(self.run_patch({p:d})["reason"],"ROOT_BINDING_SELF_AUTHORITY_FORBIDDEN")

if __name__=="__main__":unittest.main(verbosity=2)
