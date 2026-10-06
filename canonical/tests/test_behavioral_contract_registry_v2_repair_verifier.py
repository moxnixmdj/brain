from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.behavioral_contract_registry_v2_repair_verifier import RegistryRepairError,verify,BEHAVIOR
ROOT=Path(__file__).resolve().parents[2]
V1=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
V2=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"
SHA="ee187f611a0e82b2de495ee377682f39bc31dd31"
def docs(): return json.loads(V1.read_text()),json.loads(V2.read_text())
class Tests(unittest.TestCase):
 def test_current(self):
  a,b=docs(); o=verify(a,b,v1_sha=SHA); self.assertFalse(o["implementation_proved"])
 def test_extra_contract_fails(self):
  a,b=docs(); x=copy.deepcopy(b); x["active_contracted_residuals"].append(dict(x["active_contracted_residuals"][-1]))
  with self.assertRaises(RegistryRepairError): verify(a,x,v1_sha=SHA)
 def test_wrong_family_drift_fails(self):
  a,b=docs(); x=copy.deepcopy(b); x["family_to_residual_contracts"]["COMPUTER_AND_BROWSER_USE"].append(BEHAVIOR)
  with self.assertRaises(RegistryRepairError): verify(a,x,v1_sha=SHA)
 def test_missing_target_binding_fails(self):
  a,b=docs(); x=copy.deepcopy(b); x["family_to_residual_contracts"]["AGENTIC_SCIENTIFIC_RESEARCH"].pop()
  with self.assertRaises(RegistryRepairError): verify(a,x,v1_sha=SHA)
if __name__=="__main__": unittest.main(verbosity=2)
