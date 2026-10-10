from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_r9_root_subject_binding_verify_v1 as v
ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text())
class T(unittest.TestCase):
 def docs(self):
  b=load(v.BIND);s=load(v.SUB);d={k:load(p) for k,(p,_h) in v.REFS.items()};return b,s,d
 def patch(self,b,s,d):
  old=v.read
  v.read=lambda root,p,h:b if p==v.BIND else s if p==v.SUB else d[next(k for k,(rp,_x) in v.REFS.items() if rp==p)]
  return old
 def test_positive(self):self.assertTrue(v.verify()["pass"])
 def test_wrong_subject(self):
  b,s,d=self.docs();b["subject_sha256"]="bad";old=self.patch(b,s,d)
  try:self.assertEqual(v.verify()["reason"],"SUBJECT_TUPLE_MISMATCH")
  finally:v.read=old
 def test_trigger_missing(self):
  b,s,d=self.docs();d["execution_profile"]["escalation_triggers"]=[];old=self.patch(b,s,d)
  try:self.assertEqual(v.verify()["reason"],"TRIGGER_MISSING")
  finally:v.read=old
 def test_temporal_overclaim(self):
  b,s,d=self.docs();b["distribution_shift_transport_proved"]=True;old=self.patch(b,s,d)
  try:self.assertEqual(v.verify()["reason"],"TEMPORAL_OVERCLAIM")
  finally:v.read=old
 def test_scope_widening(self):
  b,s,d=self.docs();d["temporal_scope"]["global_root_closure"]=True;old=self.patch(b,s,d)
  try:self.assertEqual(v.verify()["reason"],"TEMPORAL_SCOPE_INVALID")
  finally:v.read=old
if __name__=="__main__":unittest.main(verbosity=2)
