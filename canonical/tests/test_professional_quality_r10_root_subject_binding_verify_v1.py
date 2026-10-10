import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_r10_root_subject_binding_verify_v1 as v
ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text())
class T(unittest.TestCase):
 def docs(self):return load(v.BIND),load(v.SUB),{k:load(p) for k,(p,_h) in v.REFS.items()}
 def patch(self,b,s,d):
  old=v.read;v.read=lambda root,p,h:b if p==v.BIND else s if p==v.SUB else d[next(k for k,(rp,_x) in v.REFS.items() if rp==p)];return old
 def test_positive(self):self.assertTrue(v.verify()["pass"])
 def test_wrong_subject(self):
  b,s,d=self.docs();b["subject_sha256"]="bad";old=self.patch(b,s,d)
  try:self.assertEqual(v.verify()["reason"],"SUBJECT_TUPLE_MISMATCH")
  finally:v.read=old
 def test_missing_escalation(self):
  b,s,d=self.docs();d["execution_profile"]["escalation_triggers"]=[];old=self.patch(b,s,d)
  try:self.assertEqual(v.verify()["reason"],"DECISION_ESCALATION_MISSING")
  finally:v.read=old
 def test_missing_step(self):
  b,s,d=self.docs();d["execution_profile"]["steps"]=[];old=self.patch(b,s,d)
  try:self.assertEqual(v.verify()["reason"],"MINIMUM_BLOCKING_CUT_STEP_MISSING")
  finally:v.read=old
 def test_overclaim(self):
  b,s,d=self.docs();b["normative_aggregation_closure_proved"]=True;old=self.patch(b,s,d)
  try:self.assertEqual(v.verify()["reason"],"R10_SCOPE_OVERCLAIM")
  finally:v.read=old
if __name__=="__main__":unittest.main(verbosity=2)
