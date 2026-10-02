from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.composition_behavioral_bridge_verifier_v1 import evaluate, git_blob_sha

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
TRANS=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"
MAN=ROOT/"canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
BRIDGE=ROOT/"canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json"

class BridgeTests(unittest.TestCase):
    def docs(self):
        reg=json.loads(REG.read_text()); trans=json.loads(TRANS.read_text()); man=json.loads(MAN.read_text()); bridge=json.loads(BRIDGE.read_text())
        shas={"registry":git_blob_sha(REG),"transmutation":git_blob_sha(TRANS),"manifest":git_blob_sha(MAN)}
        return reg,trans,man,bridge,shas
    def test_live_exact_two(self):
        reg,trans,man,bridge,shas=self.docs()
        out=evaluate(reg,trans,man,bridge,shas)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["derived_binding_count"],2)
        self.assertEqual({x["component_id"] for x in out["derived_bindings"]},{"delegation","tool discovery"})
        self.assertFalse(out["slicer_receipt_authorized"])
    def test_invented_binding_fails(self):
        reg,trans,man,bridge,shas=self.docs()
        bridge=copy.deepcopy(bridge)
        bridge["bindings"].append({
            "component_id":"memory","interface_id":"browser/computer action+memory+recovery","behavior_id":"INVENTED",
            "source_family":"LONG_HORIZON_MEMORY_AND_CONTINUITY","closure_evidence_id":"INVENTED",
            "source_witness_path":"x","independent_verification":"x","proved_properties":["SCOPED_ACCEPTANCE_PROOF"]
        })
        out=evaluate(reg,trans,man,bridge,shas)
        self.assertFalse(out["pass"])
        self.assertIn("BINDINGS_NOT_EXACT_RECOMPUTATION",out["errors"])
    def test_self_authorization_fails(self):
        reg,trans,man,bridge,shas=self.docs()
        bridge=copy.deepcopy(bridge)
        bridge["verification_state"]["independent_verification"]=True
        out=evaluate(reg,trans,man,bridge,shas)
        self.assertFalse(out["pass"])
        self.assertIn("CANDIDATE_MUST_NOT_SELF_AUTHORIZE",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
