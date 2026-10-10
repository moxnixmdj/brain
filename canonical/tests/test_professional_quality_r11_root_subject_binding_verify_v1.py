from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_r11_root_subject_binding_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text())

class R11BindingTests(unittest.TestCase):
    def docs(self):
        b=load(v.BIND); s=load(v.SUB)
        d={k:load(p) for k,(p,_h) in v.REFS.items()}
        return b,s,d
    def run_with(self,b,s,d):
        old=v.read
        try:
            v.read=lambda root,p,h: b if p==v.BIND else s if p==v.SUB else d[next(k for k,(rp,_x) in v.REFS.items() if rp==p)]
            return v.verify()
        finally:
            v.read=old
    def test_positive(self):
        self.assertTrue(v.verify()["pass"])
    def test_wrong_subject(self):
        b,s,d=self.docs(); b=deepcopy(b); b["subject_sha256"]="bad"
        self.assertEqual(self.run_with(b,s,d)["reason"],"SUBJECT_TUPLE_MISMATCH")
    def test_missing_holdout_trigger(self):
        b,s,d=self.docs(); d=deepcopy(d); d["execution_profile"]["escalation_triggers"]=[]
        self.assertEqual(self.run_with(b,s,d)["reason"],"HOLDOUT_ESCALATION_MISSING")
    def test_scope_widening(self):
        b,s,d=self.docs(); d=deepcopy(d); d["firewall_scope"]["global_root_closure"]=True
        self.assertEqual(self.run_with(b,s,d)["reason"],"FIREWALL_SCOPE_INVALID")
    def test_self_authority(self):
        b,s,d=self.docs(); b=deepcopy(b); b["root_subject_binding_authority"]=True
        self.assertEqual(self.run_with(b,s,d)["reason"],"SELF_AUTHORITY_FORBIDDEN")

if __name__=="__main__": unittest.main(verbosity=2)
