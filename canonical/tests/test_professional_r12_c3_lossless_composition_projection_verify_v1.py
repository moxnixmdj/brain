from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_r12_c3_lossless_composition_projection_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
 inp=json.loads((ROOT/v.INPUT_PATH).read_text())
 cv=json.loads((ROOT/v.PINS["composition_verify"][0]).read_text())
 gate_source=(ROOT/v.PINS["gate"][0]).read_text()
 bindings={};verifications={};actual={}
 for row in inp["root_subject_bindings"]:
  rid=row["root_id"];br=row["binding"];vr=row["verification"]
  bp=ROOT/br["path"];vp=ROOT/vr["path"]
  bindings[rid]=json.loads(bp.read_text())
  verifications[rid]=json.loads(vp.read_text())
  actual[rid]=v._blob(bp)
 return inp,bindings,verifications,cv,actual,gate_source

class R12C3LosslessCompositionProjectionVerifyV1Tests(unittest.TestCase):
 def test_current_projection_is_lossless_scope_preserving_only(self):
  out=v.verify(repo_root=ROOT)
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["root_binding_count"],12)
  self.assertEqual(out["reconstructible_binding_count"],12)
  self.assertTrue(out["projection_injective_on_frozen_root_set"])
  self.assertTrue(out["projection_reconstructible_from_content_address"])
  self.assertFalse(out["scope_widening_introduced_by_composition"])
  self.assertFalse(out["authority_widening_introduced_by_composition"])
  self.assertTrue(out["c3_composition_abstraction_soundness_proved"])
  self.assertFalse(out["semantic_property_truth_authority"])

 def test_lost_content_address_semantics_fails_closed(self):
  inp,b,vv,cv,actual,source=docs()
  source=source.replace('"subject_binding_git_blob_sha":bblob','"binding_omitted":True')
  out=v.analyze(inp,b,vv,cv,actual_binding_blobs=actual,gate_source=source)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"GATE_PROJECTION_SEMANTICS_FRAGMENT_MISSING")

 def test_missing_scope_limitations_fails_closed(self):
  inp,b,vv,cv,actual,source=docs()
  b=deepcopy(b);rid=next(iter(b));b[rid]["binding_scope"]["limitations"]=[]
  out=v.analyze(inp,b,vv,cv,actual_binding_blobs=actual,gate_source=source)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"BINDING_SCOPE_LIMITATIONS_MISSING")

 def test_subject_drift_fails_closed(self):
  inp,b,vv,cv,actual,source=docs()
  b=deepcopy(b);rid=next(iter(b));b[rid]["subject_sha256"]="0"*64
  out=v.analyze(inp,b,vv,cv,actual_binding_blobs=actual,gate_source=source)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"BINDING_SUBJECT_DRIFT")

 def test_failed_root_verification_fails_closed(self):
  inp,b,vv,cv,actual,source=docs()
  vv=deepcopy(vv);rid=next(iter(vv));vv[rid]["status"]="FAIL_CLOSED"
  out=v.analyze(inp,b,vv,cv,actual_binding_blobs=actual,gate_source=source)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"INDEPENDENT_ROOT_VERIFICATION_NOT_PASS")

 def test_composition_receipt_authority_widening_fails_closed(self):
  inp,b,vv,cv,actual,source=docs()
  cv=deepcopy(cv);cv["semantic_truth_authority"]=True
  out=v.analyze(inp,b,vv,cv,actual_binding_blobs=actual,gate_source=source)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"COMPOSITION_RECEIPT_AUTHORITY_WIDENING")

if __name__=="__main__":
 unittest.main(verbosity=2)
