from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_r8_root_subject_binding_verify_v1 as v
ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text())
class T(unittest.TestCase):
 def docs(self):
  b=load(v.BIND); s=load(v.SUB); d={k:load(p) for k,(p,_h) in v.REFS.items()}; return b,s,d
 def test_positive(self):
  self.assertTrue(v.verify()["pass"])
 def test_wrong_subject(self):
  b,s,d=self.docs(); b=deepcopy(b); b["subject_sha256"]="bad"
  td=ROOT/"_tmp_r8_test.json"
  # exercise structural evaluator indirectly by monkeypatching read
  old=v.read
  try:
   v.read=lambda root,p,h: b if p==v.BIND else s if p==v.SUB else d[next(k for k,(rp,_x) in v.REFS.items() if rp==p)]
   self.assertFalse(v.verify()["pass"])
  finally:v.read=old
 def test_trigger_missing(self):
  b,s,d=self.docs(); d=deepcopy(d); d["execution_profile"]["escalation_triggers"]=[]
  old=v.read
  try:
   v.read=lambda root,p,h: b if p==v.BIND else s if p==v.SUB else d[next(k for k,(rp,_x) in v.REFS.items() if rp==p)]
   self.assertEqual(v.verify()["reason"],"TRIGGER_MISSING")
  finally:v.read=old
 def test_scope_widening(self):
  b,s,d=self.docs(); d=deepcopy(d); d["r8_semantic_scope"]["global_root_closure"]=True
  old=v.read
  try:
   v.read=lambda root,p,h: b if p==v.BIND else s if p==v.SUB else d[next(k for k,(rp,_x) in v.REFS.items() if rp==p)]
   self.assertEqual(v.verify()["reason"],"SEMANTIC_SCOPE_INVALID")
  finally:v.read=old
 def test_self_authority(self):
  b,s,d=self.docs(); b=deepcopy(b); b["root_subject_binding_authority"]=True
  old=v.read
  try:
   v.read=lambda root,p,h: b if p==v.BIND else s if p==v.SUB else d[next(k for k,(rp,_x) in v.REFS.items() if rp==p)]
   self.assertEqual(v.verify()["reason"],"SELF_AUTHORITY_FORBIDDEN")
  finally:v.read=old
if __name__=="__main__":unittest.main(verbosity=2)
