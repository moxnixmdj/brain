from __future__ import annotations
import copy,unittest
from canonical.runtime.tool_discovery_common_frozen_authority_scope_theorem_v1 import prove,_sha

def tool(tid,cost):
    return {"tool_id":tid,"cost":cost,"available":True,"authorized":True,"epoch":0,"meta":{"x":tid}}

def instance():
    manifest=[tool("A",1),tool("B",2)]
    rows=sorted(manifest,key=lambda r:r["tool_id"])
    result_digest=_sha(rows)
    sources=[{"source_id":"S","authoritative":True,"available":True,"authorized":True,"source_epoch":0,"result_sha256":result_digest}]
    md=_sha(rows)
    return {
      "decision_epoch":7,"authority_manifest":manifest,
      "brain":{"decision_epoch":7,"authority_manifest_sha256":md},
      "opus":{"decision_epoch":7,"authority_manifest_sha256":md},
      "discovery_sources":sources,
      "discovery_results":[{"source_id":"S","complete":True,"decision_epoch":7,"source_epoch":0,"tools":manifest}],
    }

class Tests(unittest.TestCase):
    def test_exact_scope_passes(self):
        out=prove(instance()); self.assertTrue(out["identity_scope_complete"],out)
        self.assertTrue(out["brain_opus_same_frozen_authority"])
        self.assertFalse(out["capability_truth_proved"])
    def test_missing_tool_fails(self):
        x=instance(); x["discovery_results"][0]["tools"]=x["discovery_results"][0]["tools"][:-1]
        out=prove(x); self.assertFalse(out["identity_scope_complete"])
    def test_extra_tool_fails(self):
        x=instance(); x["discovery_results"][0]["tools"].append(tool("C",3))
        out=prove(x); self.assertFalse(out["identity_scope_complete"])
    def test_route_digest_mismatch_fails(self):
        x=instance(); x["opus"]["authority_manifest_sha256"]="sha256:"+"0"*64
        out=prove(x); self.assertFalse(out["identity_scope_complete"])
    def test_hidden_capability_leak_fails(self):
        x=instance(); x["authority_manifest"][0]["capabilities"]=["SECRET"]
        out=prove(x); self.assertFalse(out["identity_scope_complete"])
if __name__=="__main__": unittest.main(verbosity=2)
