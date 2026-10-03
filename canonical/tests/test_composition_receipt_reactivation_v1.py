import copy, json, unittest
from pathlib import Path
from canonical.runtime.composition_receipt_reactivation_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
def j(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class T(unittest.TestCase):
    def setUp(self):
        self.manifest=j("governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
        self.protocols=j("governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        self.bridge=j("governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json")
        self.bridgev=j("verification/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        self.memory=j("governance/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V1.json")
        self.package=j("capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json")
    def runv(self,*xs):
        return evaluate(*(xs or [self.manifest,self.protocols,self.bridge,self.bridgev,self.memory,self.package]))
    def test_current_truth_restores_exactly_delegation_and_memory(self):
        v=self.runv()
        self.assertEqual(v["status"],"PASS")
        self.assertEqual(v["scoped_proved_interface_count"],2)
        self.assertEqual(v["open_interface_count"],10)
        self.assertEqual({x["component_id"] for x in v["admitted_receipts"]},{"delegation","memory"})
        self.assertIn("tool discovery",{x.get("component_id") for x in v["quarantined_bindings"]})
        self.assertFalse(v["parent_composition_predicate_closed"])
        self.assertEqual(v["atomic_acceptance_credit_delta"],0)
    def test_delegation_recloses_only_while_source_family_passes(self):
        p=copy.deepcopy(self.protocols)
        next(x for x in p["protocols"] if x["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")["status"]="DEFINED_RESULT_OPEN"
        v=evaluate(self.manifest,p,self.bridge,self.bridgev,self.memory,self.package)
        self.assertEqual({x["component_id"] for x in v["admitted_receipts"]},{"memory"})
    def test_memory_fails_closed_if_owned_scope_not_closed(self):
        pkg=copy.deepcopy(self.package); pkg["decision"]["parent_family_closed_for_claim_scope"]=False
        v=evaluate(self.manifest,self.protocols,self.bridge,self.bridgev,self.memory,pkg)
        self.assertEqual({x["component_id"] for x in v["admitted_receipts"]},{"delegation"})
    def test_invented_binding_fails_closed(self):
        b=copy.deepcopy(self.bridge)
        b["bindings"].append({"component_id":"invented","interface_id":"x","source_family":"EXACT_SYMBOLIC_COMPUTATION","proved_properties":["SCOPED_ACCEPTANCE_PROOF"]})
        v=evaluate(self.manifest,self.protocols,b,self.bridgev,self.memory,self.package)
        self.assertEqual(v["status"],"FAIL_CLOSED")
        self.assertEqual(v["scoped_proved_interface_count"],0)

if __name__=="__main__":
    unittest.main()
